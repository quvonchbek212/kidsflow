"""To'lov xizmati: allocation, idempotency, reversal (4.5, 11-bo'lim).

Moliyaviy yozuvlar o'chirilmaydi; noto'g'ri to'lov reversal bilan tuzatiladi.
Takroriy yozuvning oldini olish uchun idempotency_key ishlatiladi.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import PaymentStatus
from app.models.finance import PaymentAllocation, PaymentTransaction
from app.models.messaging import OutboxEvent
from app.repositories.child_repository import EnrollmentRepository
from app.repositories.finance_repository import (
    InvoiceRepository,
    PaymentRepository,
)
from app.repositories.messaging_repository import OutboxRepository
from app.schemas.finance import PaymentRecordRequest
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.invoice_recompute import recompute_invoice
from app.utils.money import ZERO, money

PAYMENT_RECORDED = "PAYMENT_RECORDED"


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._invoices = InvoiceRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._outbox = OutboxRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def record(
        self, data: PaymentRecordRequest, current_user: CurrentUser
    ) -> PaymentTransaction:
        # Idempotency — bir xil kalit bilan takroriy so'rov mavjud to'lovni qaytaradi.
        if data.idempotency_key:
            existing = await self._payments.get_by_idempotency_key(data.idempotency_key)
            if existing is not None:
                return existing

        enrollment = await self._enrollments.get_active_for_child(data.child_id)
        if enrollment is None:
            raise ConflictError(
                "Bolaning faol enrollmenti yo'q — to'lov kiritib bo'lmaydi."
            )
        branch_id = enrollment.branch_id
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filialda to'lov kiritish huquqi yo'q.")

        amount = money(data.amount)
        payment = PaymentTransaction(
            branch_id=branch_id,
            child_id=data.child_id,
            amount=amount,
            payment_method=data.payment_method.value,
            paid_at=data.paid_at,
            reference=data.reference,
            receipt_file_id=data.receipt_file_id,
            status=PaymentStatus.RECORDED.value,
            recorded_by=current_user.id,
            idempotency_key=data.idempotency_key,
        )
        self._payments.add(payment)
        await self._session.flush()

        # Eng eski qarzdorlikdan boshlab taqsimlaymiz (5-bo'lim: aniq formula).
        remaining = amount
        outstanding = await self._invoices.list_outstanding_for_child(data.child_id)
        for invoice in outstanding:
            if remaining <= ZERO:
                break
            due = money(Decimal(str(invoice.outstanding_amount)))
            alloc = min(remaining, due)
            if alloc <= ZERO:
                continue
            self._payments.add_allocation(
                PaymentAllocation(
                    payment_transaction_id=payment.id,
                    invoice_id=invoice.id,
                    amount=alloc,
                )
            )
            remaining -= alloc
            await self._session.flush()
            await recompute_invoice(self._session, invoice)

        # Transaction commit bo'lgach ota-onaga xabar (9-bo'lim: outbox).
        self._outbox.add(
            OutboxEvent(
                event_type=PAYMENT_RECORDED,
                payload={
                    "payment_id": str(payment.id),
                    "child_id": str(data.child_id),
                    "branch_id": str(branch_id),
                    "amount": str(amount),
                },
            )
        )
        self._audit.record(
            action="PAYMENT_RECORDED",
            entity_type="payment_transaction",
            entity_id=payment.id,
            actor_user_id=current_user.id,
            branch_id=branch_id,
            after_data={"amount": str(amount)},
        )
        return payment

    async def reverse(
        self, payment_id: uuid.UUID, current_user: CurrentUser
    ) -> PaymentTransaction:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("To'lov topilmadi.")
        if not self._access.can_manage_branch(current_user, payment.branch_id):
            raise PermissionDeniedError("Bu to'lovni bekor qilish huquqi yo'q.")
        if payment.status == PaymentStatus.REVERSED.value:
            raise ConflictError("To'lov allaqachon bekor qilingan.")

        # Yozuv o'chirilmaydi — status REVERSED bo'ladi (11-bo'lim).
        payment.status = PaymentStatus.REVERSED.value

        # Ta'sirlangan invoice'larni qayta hisoblaymiz (paid_for endi bu to'lovni
        # hisobga olmaydi).
        allocations = await self._payments.allocations_for(payment_id)
        for allocation in allocations:
            invoice = await self._invoices.get_by_id(allocation.invoice_id)
            if invoice is not None:
                await recompute_invoice(self._session, invoice)

        self._audit.record(
            action="PAYMENT_REVERSED",
            entity_type="payment_transaction",
            entity_id=payment.id,
            actor_user_id=current_user.id,
            branch_id=payment.branch_id,
        )
        return payment

    async def list_for_child(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> list[PaymentTransaction]:
        """Bolaning oxirgi to'lovlari — faqat foydalanuvchi boshqaradigan filiallardan.

        Xato kiritilgan to'lovni topib bekor qilish uchun kerak: ilgari
        `reverse` endpointi bor edi, lekin qaysi to'lovni bekor qilishni tanlash
        uchun ro'yxat yo'q edi.
        """
        payments = await self._payments.list_for_child(child_id)
        return [
            p
            for p in payments
            if self._access.can_manage_branch(current_user, p.branch_id)
        ]

    async def allocations_with_unallocated(
        self, payment: PaymentTransaction
    ) -> tuple[list[PaymentAllocation], Decimal]:
        allocations = await self._payments.allocations_for(payment.id)
        allocated = sum(
            (money(Decimal(str(a.amount))) for a in allocations), start=ZERO
        )
        unallocated = money(Decimal(str(payment.amount)) - allocated)
        return allocations, unallocated

    async def get_accessible(
        self, payment_id: uuid.UUID, current_user: CurrentUser
    ) -> PaymentTransaction:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("To'lov topilmadi.")
        if not self._access.can_manage_branch(current_user, payment.branch_id):
            raise PermissionDeniedError("Bu to'lovga kirish huquqi yo'q.")
        return payment
