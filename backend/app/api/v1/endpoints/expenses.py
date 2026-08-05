"""Xarajat endpointlari (5.6-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, require_roles
from app.models.enums import Role
from app.models.finance import Expense, ExpenseCategory
from app.schemas.finance import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryResponse,
    ExpenseCategoryUpdateRequest,
    ExpenseRecordRequest,
    ExpenseResponse,
)
from app.services.expense_service import ExpenseService

router = APIRouter(tags=["expenses"])


def _expense_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        branch_id=expense.branch_id,
        category_id=expense.category_id,
        amount=expense.amount,
        expense_date=expense.expense_date,
        vendor=expense.vendor,
        description=expense.description,
        status=expense.status,
        is_recurring=expense.is_recurring,
    )


def _category_response(category: ExpenseCategory) -> ExpenseCategoryResponse:
    return ExpenseCategoryResponse(
        id=category.id,
        name=category.name,
        is_system=category.is_system,
        is_active=category.is_active,
        is_variable=category.is_variable,
    )


@router.get(
    "/expense-categories",
    response_model=list[ExpenseCategoryResponse],
    summary="Xarajat kategoriyalari",
)
async def list_categories(
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[ExpenseCategoryResponse]:
    categories = await ExpenseService(session).list_categories()
    return [_category_response(c) for c in categories]


@router.post(
    "/expense-categories",
    response_model=ExpenseCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Xarajat kategoriyasi qo'shish (OWNER/MANAGER)",
)
async def create_category(
    payload: ExpenseCategoryCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpenseCategoryResponse:
    category = await ExpenseService(session).create_category(payload, current_user)
    return _category_response(category)


@router.patch(
    "/expense-categories/{category_id}",
    response_model=ExpenseCategoryResponse,
    summary="Xarajat kategoriyasini tahrirlash (OWNER/MANAGER)",
)
async def update_category(
    category_id: uuid.UUID,
    payload: ExpenseCategoryUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpenseCategoryResponse:
    category = await ExpenseService(session).update_category(
        category_id, payload, current_user
    )
    return _category_response(category)


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Xarajat kiritish (MANAGER/OWNER)",
)
async def record_expense(
    payload: ExpenseRecordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpenseResponse:
    expense = await ExpenseService(session).record(payload, current_user)
    return _expense_response(expense)


@router.get(
    "/expenses",
    response_model=list[ExpenseResponse],
    summary="Filial xarajatlari ro'yxati (MANAGER/OWNER)",
)
async def list_expenses(
    branch_id: uuid.UUID = Query(...),
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExpenseResponse]:
    expenses = await ExpenseService(session).list_for_branch(
        branch_id, current_user, period_start, period_end
    )
    return [_expense_response(e) for e in expenses]


@router.get(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
    summary="Xarajat ma'lumoti",
)
async def get_expense(
    expense_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpenseResponse:
    expense = await ExpenseService(session).get_accessible(expense_id, current_user)
    return _expense_response(expense)


@router.post(
    "/expenses/{expense_id}/reverse",
    response_model=ExpenseResponse,
    summary="Xarajatni bekor qilish (reversal)",
)
async def reverse_expense(
    expense_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpenseResponse:
    expense = await ExpenseService(session).reverse(expense_id, current_user)
    return _expense_response(expense)
