"""Invoice generatsiyasi va tuzatmalar (4.5, 5.5-bo'lim).

Oylik summa bolaning guruhidagi tarifdan olinadi.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enrollment import Enrollment
from app.models.enums import AdjustmentType, InvoiceStatus
from app.models.finance import Invoice, InvoiceAdjustment
from app.repositories.branch_repository import BranchRepository
from app.repositories.child_repository import EnrollmentRepository
from app.repositories.finance_repository import InvoiceRepository
from app.repositories.messaging_repository import BranchNotificationSettingsRepository
from app.schemas.finance import (
    AdjustmentCreateRequest,
    InvoiceGenerateRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.invoice_recompute import recompute_invoice
from app.services.payment_allocation import apply_unallocated
from app.utils.money import money

# Filialda sozlama yozuvi bo'lmasa: har oyning 10-sanasi (avvalgi qo'lda
# yaratish formasidagi standart qiymat).
DEFAULT_INVOICE_DUE_DAY = 10


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invoices = InvoiceRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._branches = BranchRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    # --- Invoice generatsiyasi ---

    async def generate_invoices(
        self, data: InvoiceGenerateRequest, current_user: CurrentUser
    ) -> tuple[int, int, date]:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda invoice yaratish huquqi yo'q.")

        billing_period = data.billing_period.replace(day=1)
        created, skipped = await self.generate_for_branch(
            data.branch_id, billing_period, data.due_day
        )

        self._audit.record(
            action="INVOICES_GENERATED",
            entity_type="invoice_batch",
            entity_id=str(data.branch_id),
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"created": created, "period": billing_period.isoformat()},
        )
        return created, skipped, billing_period

    async def due_day_for(self, branch_id: uuid.UUID) -> int:
        """Filialning oylik to'lov muddati (oyning sanasi)."""
        configs = await BranchNotificationSettingsRepository(
            self._session
        ).list_by_branches([branch_id])
        config = configs.get(branch_id)
        return config.invoice_due_day if config else DEFAULT_INVOICE_DUE_DAY

    async def generate_for_branch(
        self,
        branch_id: uuid.UUID,
        billing_period: date,
        due_day: int,
        *,
        child_id: uuid.UUID | None = None,
        not_before: date | None = None,
    ) -> tuple[int, int]:
        """Filialdagi faol bolalarga bir oy uchun hisob-faktura yaratadi.

        Huquq TEKSHIRILMAYDI — chaqiruvchi javobgar: HTTP endpoint (menejer),
        kunlik worker (`auto_billing`) va bola ro'yxatga olinganda
        (`EnrollmentService`).

        Idempotent: bolaning shu oyga hisobi bo'lsa (bekor qilingan bo'lsa ham)
        qayta yaratilmaydi — bekor qilish qarori saqlanadi.

        `child_id` — faqat shu bola uchun. `not_before` — muddat bundan oldin
        bo'lmaydi: oy o'rtasida qo'shilgan bolaning hisobi yaratilgan zahoti
        "kechikkan" bo'lib chiqmasin.

        Yangi hisobdan keyin bolaning oldindan to'lagan (hech bir hisobga
        yozilmagan) puli unga avtomatik yoziladi.
        """
        billing_period = billing_period.replace(day=1)
        due_date = billing_period.replace(day=due_day)
        if not_before is not None and due_date < not_before:
            due_date = not_before
        next_period = (billing_period + timedelta(days=32)).replace(day=1)

        created = 0
        skipped = 0
        new_invoices: list[tuple[Invoice, Enrollment]] = []
        enrollments = await self._enrollments.list_active_in_branch(branch_id)
        # Mavjud hisoblar sikldan oldin bitta so'rov bilan — ilgari har bir
        # bola uchun alohida SELECT ketardi.
        already_billed = await self._invoices.child_ids_billed_for(
            [e.child_id for e, _ in enrollments], billing_period
        )
        for enrollment, group_monthly_fee in enrollments:
            if child_id is not None and enrollment.child_id != child_id:
                continue
            # Keyingi oydan boshlaydigan bola bu oy uchun to'lamaydi.
            if enrollment.start_date >= next_period:
                skipped += 1
                continue

            # Tarif — bolaning guruhidagi oylik tarif ("Guruhlar" formasida
            # kiritiladi). Tarif belgilanmagan guruh uchun hisob yaratilmaydi.
            monthly_amount = (
                Decimal(str(group_monthly_fee))
                if group_monthly_fee is not None
                else None
            )

            if monthly_amount is None or monthly_amount <= 0:
                skipped += 1
                continue

            if enrollment.child_id in already_billed:
                skipped += 1
                continue
            already_billed.add(enrollment.child_id)

            amount = money(monthly_amount)
            invoice = Invoice(
                branch_id=branch_id,
                child_id=enrollment.child_id,
                enrollment_id=enrollment.id,
                billing_period=billing_period,
                due_date=due_date,
                original_amount=amount,
                discount_amount=money(Decimal("0")),
                adjusted_amount=amount,
                paid_amount=money(Decimal("0")),
                outstanding_amount=amount,
                status=InvoiceStatus.OPEN.value,
            )
            self._invoices.add(invoice)
            new_invoices.append((invoice, enrollment))
            created += 1

        # Invoice ID'lari flush'dan keyin mavjud bo'ladi — chegirmani shundan
        # keyin, invoice_adjustments orqali qo'shamiz (5.5-bo'lim: to'lanadigan
        # summa faqat adjustment yozuvlari orqali o'zgaradi).
        await self._session.flush()

        for invoice, enrollment in new_invoices:
            if enrollment.discount_percent and enrollment.discount_percent > 0:
                discount_amount = money(
                    invoice.original_amount
                    * Decimal(str(enrollment.discount_percent))
                    / Decimal("100")
                )
                self._invoices.add_adjustment(
                    InvoiceAdjustment(
                        invoice_id=invoice.id,
                        adjustment_type=AdjustmentType.DISCOUNT.value,
                        amount=discount_amount,
                        reason=f"Doimiy chegirma: {enrollment.discount_type or 'OTHER'}",
                    )
                )
        await self._session.flush()
        for invoice, enrollment in new_invoices:
            if enrollment.discount_percent and enrollment.discount_percent > 0:
                await recompute_invoice(self._session, invoice)

        # Oldindan to'langan pul yangi hisoblarga yoziladi.
        for billed_child_id in {invoice.child_id for invoice, _ in new_invoices}:
            await apply_unallocated(self._session, billed_child_id)

        return created, skipped

    async def list_invoices_for_child(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> list[Invoice]:
        if not await self._access.can_view_child(current_user, child_id):
            raise PermissionDeniedError("Bu bola invoice'lariga kirish huquqi yo'q.")
        return await self._invoices.list_for_child(child_id)

    async def list_invoices_for_branch_period(
        self,
        branch_id: uuid.UUID,
        billing_period: date,
        current_user: CurrentUser,
    ) -> list[Invoice]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial invoice'lariga kirish huquqi yo'q.")
        period = billing_period.replace(day=1)
        return await self._invoices.list_by_branch_period(branch_id, period)

    # --- Tuzatma va bekor qilish ---

    async def add_adjustment(
        self,
        invoice_id: uuid.UUID,
        data: AdjustmentCreateRequest,
        current_user: CurrentUser,
    ) -> Invoice:
        invoice = await self._invoices.get_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice topilmadi.")
        if not self._access.can_manage_branch(current_user, invoice.branch_id):
            raise PermissionDeniedError("Bu invoice'ni tuzatish huquqi yo'q.")
        if invoice.status == InvoiceStatus.CANCELLED.value:
            raise ConflictError("Bekor qilingan invoice tuzatilmaydi.")

        self._invoices.add_adjustment(
            InvoiceAdjustment(
                invoice_id=invoice_id,
                adjustment_type=data.adjustment_type.value,
                amount=money(data.amount),
                reason=data.reason,
                created_by=current_user.id,
            )
        )
        await self._session.flush()
        await recompute_invoice(self._session, invoice)
        self._audit.record(
            action="INVOICE_ADJUSTED",
            entity_type="invoice",
            entity_id=invoice.id,
            actor_user_id=current_user.id,
            branch_id=invoice.branch_id,
            after_data={
                "type": data.adjustment_type.value,
                "amount": str(money(data.amount)),
            },
        )
        return invoice

    async def cancel_invoice(
        self, invoice_id: uuid.UUID, current_user: CurrentUser
    ) -> Invoice:
        invoice = await self._invoices.get_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice topilmadi.")
        if not self._access.can_manage_branch(current_user, invoice.branch_id):
            raise PermissionDeniedError("Bu invoice'ni bekor qilish huquqi yo'q.")
        if invoice.paid_amount > money(Decimal("0")):
            raise ConflictError(
                "To'lov qilingan invoice bekor qilinmaydi — reversal ishlating."
            )

        await recompute_invoice(self._session, invoice, cancelled=True)
        self._audit.record(
            action="INVOICE_CANCELLED",
            entity_type="invoice",
            entity_id=invoice.id,
            actor_user_id=current_user.id,
            branch_id=invoice.branch_id,
        )
        return invoice
