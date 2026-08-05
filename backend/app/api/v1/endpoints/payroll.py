"""Payroll (oylik hisoblash) endpointlari (7-bosqich B)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import require_roles
from app.models.enums import Role
from app.models.payroll import PayrollRun
from app.schemas.payroll import PayrollRunCreateRequest, PayrollRunResponse
from app.services.payroll_service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll"])


def _to_response(run: PayrollRun) -> PayrollRunResponse:
    return PayrollRunResponse(
        id=run.id,
        branch_id=run.branch_id,
        user_id=run.user_id,
        period=run.period,
        base_salary=run.base_salary,
        bonus=run.bonus,
        deduction=run.deduction,
        advance_deducted=run.advance_deducted,
        net_pay=run.net_pay,
        status=run.status,
        expense_id=run.expense_id,
        paid_at=run.paid_at,
    )


@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Oylikni hisoblash va to'lash (OWNER/MANAGER)",
)
async def create_payroll_run(
    payload: PayrollRunCreateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> PayrollRunResponse:
    run = await PayrollService(session).calculate_and_pay(payload, current_user)
    return _to_response(run)


@router.get(
    "/runs",
    response_model=list[PayrollRunResponse],
    summary="Payroll yozuvlari ro'yxati (OWNER/MANAGER)",
)
async def list_payroll_runs(
    user_id: uuid.UUID | None = Query(default=None),
    branch_id: uuid.UUID | None = Query(default=None),
    period: date | None = Query(default=None),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[PayrollRunResponse]:
    service = PayrollService(session)
    if user_id is not None:
        runs = await service.list_for_user(user_id)
    elif branch_id is not None:
        runs = await service.list_for_branch(branch_id, current_user, period)
    else:
        runs = []
    return [_to_response(r) for r in runs]


@router.post(
    "/runs/{run_id}/reverse",
    response_model=PayrollRunResponse,
    summary="Payroll yozuvini bekor qilish (OWNER/MANAGER)",
)
async def reverse_payroll_run(
    run_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> PayrollRunResponse:
    run = await PayrollService(session).reverse(run_id, current_user)
    return _to_response(run)
