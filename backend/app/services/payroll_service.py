"""Payroll (oylik hisoblash va to'lash) biznes xizmati (7-bosqich B).

Har bir hisoblash bog'langan `Expense` yozuvini ("Ish haqi" kategoriyasi)
avtomatik yaratadi — shu orqali payroll xarajat hisobotlari/break-even
hisob-kitobida avtomatik hisobga olinadi (qo'lda ikki marta kiritilmaydi).
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import ExpenseStatus, PayrollStatus
from app.models.finance import Expense
from app.models.payroll import PayrollRun
from app.repositories.finance_repository import ExpenseRepository
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payroll import PayrollRunCreateRequest
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.expense_service import ExpenseService
from app.utils.money import ZERO, money


class PayrollService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payroll = PayrollRepository(session)
        self._expenses_repo = ExpenseRepository(session)
        self._expenses = ExpenseService(session)
        self._users = UserRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def calculate_and_pay(
        self, data: PayrollRunCreateRequest, current_user: CurrentUser
    ) -> PayrollRun:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda payroll hisoblash huquqi yo'q.")

        user = await self._users.get_by_id(data.user_id)
        if user is None:
            raise NotFoundError("Xodim topilmadi.")

        base = data.base_salary if data.base_salary is not None else user.monthly_salary
        if base is None:
            raise ConflictError(
                "Xodimning asosiy oyligi belgilanmagan — base_salary ko'rsating."
            )
        base = money(base)
        net = money(base + data.bonus - data.deduction - data.advance_deducted)
        if net < ZERO:
            raise ConflictError("Sof to'lov summasi manfiy bo'lishi mumkin emas.")

        period = data.period.replace(day=1)
        existing = await self._payroll.get_active_for_user_period(data.user_id, period)
        if existing is not None:
            raise ConflictError(
                "Bu xodim uchun shu davrda allaqachon hisoblangan (avval bekor qiling)."
            )

        categories = await self._expenses.list_categories()
        payroll_category = next((c for c in categories if c.name == "Ish haqi"), None)
        if payroll_category is None:
            raise ConflictError("'Ish haqi' xarajat kategoriyasi topilmadi.")

        expense = Expense(
            branch_id=data.branch_id,
            category_id=payroll_category.id,
            amount=net,
            expense_date=data.paid_at.date(),
            vendor=user.full_name,
            description=f"Oylik hisob-kitob — {period.isoformat()[:7]}",
            status=ExpenseStatus.RECORDED.value,
            recorded_by=current_user.id,
        )
        self._expenses_repo.add(expense)
        await self._session.flush()

        run = PayrollRun(
            branch_id=data.branch_id,
            user_id=data.user_id,
            period=period,
            base_salary=base,
            bonus=money(data.bonus),
            deduction=money(data.deduction),
            advance_deducted=money(data.advance_deducted),
            net_pay=net,
            status=PayrollStatus.RECORDED.value,
            expense_id=expense.id,
            paid_at=data.paid_at,
            recorded_by=current_user.id,
        )
        self._payroll.add(run)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "Bu xodim uchun shu davrda allaqachon hisoblangan (poyga holati)."
            ) from exc

        self._audit.record(
            action="PAYROLL_RUN_CREATED",
            entity_type="payroll_run",
            entity_id=run.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"user_id": str(data.user_id), "net_pay": str(net)},
        )
        return run

    async def reverse(self, run_id: uuid.UUID, current_user: CurrentUser) -> PayrollRun:
        run = await self._payroll.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Payroll yozuvi topilmadi.")
        if not self._access.can_manage_branch(current_user, run.branch_id):
            raise PermissionDeniedError("Bu payroll yozuvini bekor qilish huquqi yo'q.")
        if run.status == PayrollStatus.REVERSED.value:
            raise ConflictError("Payroll yozuvi allaqachon bekor qilingan.")

        run.status = PayrollStatus.REVERSED.value
        if run.expense_id is not None:
            expense = await self._expenses_repo.get_by_id(run.expense_id)
            if expense is not None and expense.status != ExpenseStatus.REVERSED.value:
                await self._expenses.reverse(run.expense_id, current_user)

        self._audit.record(
            action="PAYROLL_RUN_REVERSED",
            entity_type="payroll_run",
            entity_id=run.id,
            actor_user_id=current_user.id,
            branch_id=run.branch_id,
        )
        return run

    async def list_for_user(self, user_id: uuid.UUID) -> list[PayrollRun]:
        # Ruxsat endpoint darajasida tekshiriladi (OWNER/MANAGER) — xuddi
        # `GET /users/payroll-summary` namunasida.
        return await self._payroll.list_for_user(user_id)

    async def list_for_branch(
        self,
        branch_id: uuid.UUID,
        current_user: CurrentUser,
        period: date | None = None,
    ) -> list[PayrollRun]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError(
                "Bu filial payroll yozuvlariga kirish huquqi yo'q."
            )
        return await self._payroll.list_for_branch(branch_id, period)
