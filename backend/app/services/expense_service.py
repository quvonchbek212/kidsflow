"""Xarajat xizmati: kiritish, reversal, kategoriyalar (5.6-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import ExpenseStatus, Role
from app.models.finance import Expense, ExpenseCategory
from app.repositories.finance_repository import ExpenseRepository
from app.schemas.finance import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryUpdateRequest,
    ExpenseRecordRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils.money import money

# Standart tizim kategoriyalari (5.6-bo'lim). "Oziq-ovqat" — zararsizlik
# hisobida bola soniga bog'liq o'zgaruvchan xarajat (is_variable=True), qolgani
# doimiy xarajat sifatida hisoblanadi.
_DEFAULT_CATEGORIES: list[tuple[str, bool]] = [
    ("Ish haqi", False),
    ("Ijara", False),
    ("Oziq-ovqat", True),
    ("Kommunal xizmat", False),
    ("Jihoz", False),
    ("Ta'mirlash", False),
    ("Transport", False),
    ("Soliq", False),
    ("Boshqa", False),
]


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._expenses = ExpenseRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def list_categories(self) -> list[ExpenseCategory]:
        """Kategoriyalarni qaytaradi; bo'sh bo'lsa standartlarni seed qiladi."""
        categories = await self._expenses.list_categories()
        if not categories:
            for name, is_variable in _DEFAULT_CATEGORIES:
                self._expenses.add_category(
                    ExpenseCategory(name=name, is_system=True, is_variable=is_variable)
                )
            await self._session.flush()
            categories = await self._expenses.list_categories()
        return categories

    async def create_category(
        self, data: ExpenseCategoryCreateRequest, current_user: CurrentUser
    ) -> ExpenseCategory:
        if not (current_user.is_owner or current_user.has_any_role(Role.MANAGER)):
            raise PermissionDeniedError(
                "Xarajat kategoriyasini faqat OWNER/MANAGER qo'shadi."
            )
        if await self._expenses.category_name_exists(data.name):
            raise ConflictError("Shu nomdagi kategoriya allaqachon mavjud.")

        category = ExpenseCategory(
            name=data.name, is_system=False, is_variable=data.is_variable
        )
        self._expenses.add_category(category)
        await self._session.flush()
        self._audit.record(
            action="EXPENSE_CATEGORY_CREATED",
            entity_type="expense_category",
            entity_id=category.id,
            actor_user_id=current_user.id,
            after_data={"name": category.name},
        )
        return category

    async def update_category(
        self,
        category_id: uuid.UUID,
        data: ExpenseCategoryUpdateRequest,
        current_user: CurrentUser,
    ) -> ExpenseCategory:
        if not (current_user.is_owner or current_user.has_any_role(Role.MANAGER)):
            raise PermissionDeniedError(
                "Xarajat kategoriyasini faqat OWNER/MANAGER tahrirlaydi."
            )
        category = await self._expenses.get_category(category_id)
        if category is None:
            raise NotFoundError("Xarajat kategoriyasi topilmadi.")

        fields = data.model_dump(exclude_unset=True)
        if (
            "name" in fields
            and fields["name"] != category.name
            and (await self._expenses.category_name_exists(fields["name"]))
        ):
            raise ConflictError("Shu nomdagi kategoriya allaqachon mavjud.")
        for field, value in fields.items():
            setattr(category, field, value)

        self._audit.record(
            action="EXPENSE_CATEGORY_UPDATED",
            entity_type="expense_category",
            entity_id=category.id,
            actor_user_id=current_user.id,
        )
        return category

    async def record(
        self, data: ExpenseRecordRequest, current_user: CurrentUser
    ) -> Expense:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda xarajat kiritish huquqi yo'q.")
        if await self._expenses.get_category(data.category_id) is None:
            raise NotFoundError("Xarajat kategoriyasi topilmadi.")

        expense = Expense(
            branch_id=data.branch_id,
            category_id=data.category_id,
            amount=money(data.amount),
            expense_date=data.expense_date,
            vendor=data.vendor,
            description=data.description,
            receipt_file_id=data.receipt_file_id,
            status=ExpenseStatus.RECORDED.value,
            recorded_by=current_user.id,
            is_recurring=data.is_recurring,
        )
        self._expenses.add(expense)
        await self._session.flush()
        self._audit.record(
            action="EXPENSE_RECORDED",
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"amount": str(money(data.amount))},
        )
        return expense

    async def reverse(
        self, expense_id: uuid.UUID, current_user: CurrentUser
    ) -> Expense:
        expense = await self._expenses.get_by_id(expense_id)
        if expense is None:
            raise NotFoundError("Xarajat topilmadi.")
        if not self._access.can_manage_branch(current_user, expense.branch_id):
            raise PermissionDeniedError("Bu xarajatni bekor qilish huquqi yo'q.")
        if expense.status == ExpenseStatus.REVERSED.value:
            raise ConflictError("Xarajat allaqachon bekor qilingan.")

        # O'chirilmaydi — status REVERSED (11-bo'lim).
        expense.status = ExpenseStatus.REVERSED.value
        self._audit.record(
            action="EXPENSE_REVERSED",
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=current_user.id,
            branch_id=expense.branch_id,
        )
        return expense

    async def get_accessible(
        self, expense_id: uuid.UUID, current_user: CurrentUser
    ) -> Expense:
        expense = await self._expenses.get_by_id(expense_id)
        if expense is None:
            raise NotFoundError("Xarajat topilmadi.")
        if not self._access.can_manage_branch(current_user, expense.branch_id):
            raise PermissionDeniedError("Bu xarajatga kirish huquqi yo'q.")
        return expense

    async def list_for_branch(
        self,
        branch_id: uuid.UUID,
        current_user: CurrentUser,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[Expense]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial xarajatlariga kirish huquqi yo'q.")
        return await self._expenses.list_by_branch(branch_id, period_start, period_end)
