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
from app.models.enums import ExpenseStatus, PayrollStatus, Role
from app.models.finance import Expense
from app.models.payroll import PayrollRun, SalaryAdvance
from app.repositories.finance_repository import ExpenseRepository
from app.repositories.payroll_repository import (
    PayrollRepository,
    SalaryAdvanceRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.payroll import PayrollRunCreateRequest, SalaryAdvanceCreateRequest
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.expense_service import ExpenseService
from app.utils.money import ZERO, money
from app.utils.timezone import local_zone


class PayrollService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payroll = PayrollRepository(session)
        self._advances = SalaryAdvanceRepository(session)
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
        await self._require_staff_in_branch(data.user_id, data.branch_id)

        base = data.base_salary if data.base_salary is not None else user.monthly_salary
        if base is None:
            raise ConflictError(
                "Xodimning asosiy oyligi belgilanmagan — base_salary ko'rsating."
            )
        base = money(base)
        period = data.period.replace(day=1)

        # Shu oy berilgan avanslar yozib qo'yilgan bo'lsa, ular o'zi ushlanadi:
        # qo'lda kiritishda unutib, avansni ikkinchi marta to'lab yuborish
        # xavfi yo'qoladi. Yozuv bo'lmasa — eski oqim, qo'lda kiritilgan son.
        recorded_advances = await self._advances.total_for_user_period(
            data.user_id, period
        )
        advance = money(
            recorded_advances
            if recorded_advances > ZERO
            else (data.advance_deducted or ZERO)
        )
        net = money(base + data.bonus - data.deduction - advance)
        if net < ZERO:
            raise ConflictError("Sof to'lov summasi manfiy bo'lishi mumkin emas.")

        existing = await self._payroll.get_active_for_user_period(data.user_id, period)
        if existing is not None:
            raise ConflictError(
                "Bu xodim uchun shu davrda allaqachon hisoblangan (avval bekor qiling)."
            )

        expense = Expense(
            branch_id=data.branch_id,
            category_id=await self._payroll_category_id(),
            amount=net,
            # Mahalliy sana: UTC bo'yicha Toshkentda 00:00–05:00 orasidagi
            # to'lov oldingi kunga (oy boshida — oldingi oyga) tushardi.
            expense_date=data.paid_at.astimezone(local_zone()).date(),
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
            advance_deducted=advance,
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

    async def _require_staff_in_branch(
        self, user_id: uuid.UUID, branch_id: uuid.UUID
    ) -> None:
        """Oylik/avans faqat shu filialga biriktirilgan xodimga yoziladi.

        Aks holda A filial menejeri B filial xodimiga o'z filialidan "oylik
        to'lar" va xarajat noto'g'ri filialga tushardi.
        """
        if branch_id not in await self._users.branch_ids_for(user_id):
            raise ConflictError("Xodim bu filialga biriktirilmagan.")

    async def _require_can_view_staff(
        self, user_id: uuid.UUID, current_user: CurrentUser
    ) -> None:
        if current_user.is_owner:
            return
        managed = current_user.branches_for(Role.MANAGER)
        if not (await self._users.branch_ids_for(user_id)) & managed:
            raise PermissionDeniedError("Bu xodim sizning filialingizga tegishli emas.")

    async def _payroll_category_id(self) -> uuid.UUID:
        categories = await self._expenses.list_categories()
        payroll_category = next((c for c in categories if c.name == "Ish haqi"), None)
        if payroll_category is None:
            raise ConflictError("'Ish haqi' xarajat kategoriyasi topilmadi.")
        return payroll_category.id

    # --- Avans ---

    async def give_advance(
        self, data: SalaryAdvanceCreateRequest, current_user: CurrentUser
    ) -> SalaryAdvance:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda avans berish huquqi yo'q.")

        user = await self._users.get_by_id(data.user_id)
        if user is None:
            raise NotFoundError("Xodim topilmadi.")
        await self._require_staff_in_branch(data.user_id, data.branch_id)

        # Avans qaysi oyga tegishli — mahalliy taqvim bo'yicha (UTC da oyning
        # oxirgi kechasi berilgan avans keyingi oyga tushib qolmasin).
        paid_local = data.paid_at.astimezone(local_zone()).date()
        period = paid_local.replace(day=1)

        if await self._payroll.get_active_for_user_period(data.user_id, period):
            raise ConflictError(
                "Bu oy uchun oylik allaqachon hisoblangan — avans berib bo'lmaydi."
            )

        amount = money(data.amount)
        if user.monthly_salary is not None:
            already = await self._advances.total_for_user_period(data.user_id, period)
            if already + amount > money(user.monthly_salary):
                raise ConflictError(
                    "Shu oydagi avanslar xodimning oyligidan oshib ketadi."
                )

        expense = Expense(
            branch_id=data.branch_id,
            category_id=await self._payroll_category_id(),
            amount=amount,
            expense_date=paid_local,
            vendor=user.full_name,
            description=f"Avans — {period.isoformat()[:7]}",
            status=ExpenseStatus.RECORDED.value,
            recorded_by=current_user.id,
        )
        self._expenses_repo.add(expense)
        await self._session.flush()

        advance = SalaryAdvance(
            branch_id=data.branch_id,
            user_id=data.user_id,
            period=period,
            amount=amount,
            note=data.note,
            status=PayrollStatus.RECORDED.value,
            expense_id=expense.id,
            paid_at=data.paid_at,
            recorded_by=current_user.id,
        )
        self._advances.add(advance)
        await self._session.flush()

        self._audit.record(
            action="SALARY_ADVANCE_CREATED",
            entity_type="salary_advance",
            entity_id=advance.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"user_id": str(data.user_id), "amount": str(amount)},
        )
        return advance

    async def reverse_advance(
        self, advance_id: uuid.UUID, current_user: CurrentUser
    ) -> SalaryAdvance:
        advance = await self._advances.get_by_id(advance_id)
        if advance is None:
            raise NotFoundError("Avans yozuvi topilmadi.")
        if not self._access.can_manage_branch(current_user, advance.branch_id):
            raise PermissionDeniedError("Bu avansni bekor qilish huquqi yo'q.")
        if advance.status == PayrollStatus.REVERSED.value:
            raise ConflictError("Avans allaqachon bekor qilingan.")
        # Oylik hisobida ushlangan avansni bekor qilsak, sof summa noto'g'ri
        # bo'lib qoladi — avval oylik hisobining o'zi bekor qilinadi.
        if await self._payroll.get_active_for_user_period(
            advance.user_id, advance.period
        ):
            raise ConflictError(
                "Bu avans oylik hisobida ushlangan — avval oylik hisobini bekor qiling."
            )

        advance.status = PayrollStatus.REVERSED.value
        if advance.expense_id is not None:
            expense = await self._expenses_repo.get_by_id(advance.expense_id)
            if expense is not None and expense.status != ExpenseStatus.REVERSED.value:
                await self._expenses.reverse(advance.expense_id, current_user)

        self._audit.record(
            action="SALARY_ADVANCE_REVERSED",
            entity_type="salary_advance",
            entity_id=advance.id,
            actor_user_id=current_user.id,
            branch_id=advance.branch_id,
        )
        return advance

    async def list_advances_for_user(
        self, user_id: uuid.UUID, current_user: CurrentUser
    ) -> list[SalaryAdvance]:
        await self._require_can_view_staff(user_id, current_user)
        return await self._advances.list_for_user(user_id)

    async def list_advances_for_branch(
        self,
        branch_id: uuid.UUID,
        current_user: CurrentUser,
        period: date | None = None,
    ) -> list[SalaryAdvance]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial avanslariga kirish huquqi yo'q.")
        return await self._advances.list_for_branch(branch_id, period)

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

    async def list_for_user(
        self, user_id: uuid.UUID, current_user: CurrentUser
    ) -> list[PayrollRun]:
        # Rol endpointda tekshiriladi (OWNER/MANAGER); filial esa shu yerda —
        # ilgari istalgan menejer har qanday xodimning oylik tarixini ko'rardi.
        await self._require_can_view_staff(user_id, current_user)
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
