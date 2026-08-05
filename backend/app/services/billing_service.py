"""Tarif rejalari, invoice generatsiyasi va tuzatmalar (4.5, 5.5-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enrollment import Enrollment
from app.models.enums import AdjustmentType, InvoiceStatus, Role
from app.models.finance import FeePlan, Invoice, InvoiceAdjustment
from app.repositories.branch_repository import BranchRepository
from app.repositories.child_repository import EnrollmentRepository
from app.repositories.finance_repository import (
    FeePlanRepository,
    InvoiceRepository,
)
from app.schemas.finance import (
    AdjustmentCreateRequest,
    FeePlanCreateRequest,
    InvoiceGenerateRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.invoice_recompute import recompute_invoice
from app.utils.money import money


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._fee_plans = FeePlanRepository(session)
        self._invoices = InvoiceRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._branches = BranchRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    # --- Tarif rejalari ---

    async def create_fee_plan(
        self, data: FeePlanCreateRequest, current_user: CurrentUser
    ) -> FeePlan:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda tarif yaratish huquqi yo'q.")
        if await self._branches.get_by_id(data.branch_id) is None:
            raise NotFoundError("Filial topilmadi.")

        plan = FeePlan(
            branch_id=data.branch_id,
            name=data.name,
            monthly_amount=money(data.monthly_amount),
            currency=data.currency,
        )
        self._fee_plans.add(plan)
        await self._session.flush()
        self._audit.record(
            action="FEE_PLAN_CREATED",
            entity_type="fee_plan",
            entity_id=plan.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
        )
        return plan

    async def list_fee_plans(self, current_user: CurrentUser) -> list[FeePlan]:
        if current_user.is_owner:
            branch_ids = [b.id for b in await self._branches.list_all()]
        else:
            branch_ids = list(current_user.branches_for(Role.MANAGER))
        return await self._fee_plans.list_by_branches(branch_ids)

    # --- Invoice generatsiyasi ---

    async def generate_invoices(
        self, data: InvoiceGenerateRequest, current_user: CurrentUser
    ) -> tuple[int, int, date]:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda invoice yaratish huquqi yo'q.")

        billing_period = data.billing_period.replace(day=1)
        due_date = billing_period.replace(day=data.due_day)

        # Standart tarif (fallback) ni oldindan yuklaymiz.
        default_plan = None
        if data.fee_plan_id is not None:
            default_plan = await self._fee_plans.get_by_id(data.fee_plan_id)
            if default_plan is None:
                raise NotFoundError("Standart tarif topilmadi.")

        created = 0
        skipped = 0
        new_invoices: list[tuple[Invoice, Enrollment]] = []
        enrollments = await self._enrollments.list_active_in_branch(data.branch_id)
        for enrollment in enrollments:
            plan = default_plan
            if enrollment.fee_plan_id is not None:
                plan = await self._fee_plans.get_by_id(enrollment.fee_plan_id)
            if plan is None:
                skipped += 1
                continue

            existing = await self._invoices.get_for_child_period(
                enrollment.child_id, billing_period
            )
            if existing is not None:
                skipped += 1
                continue

            amount = money(Decimal(str(plan.monthly_amount)))
            invoice = Invoice(
                branch_id=data.branch_id,
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

        self._audit.record(
            action="INVOICES_GENERATED",
            entity_type="invoice_batch",
            entity_id=str(data.branch_id),
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"created": created, "period": billing_period.isoformat()},
        )
        return created, skipped, billing_period

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
