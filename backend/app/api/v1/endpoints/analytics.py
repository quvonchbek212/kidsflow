"""Moliyaviy dashboard endpointi (4.7-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import require_roles
from app.models.enums import Role
from app.schemas.finance import FinanceDashboardResponse, MonthlyFinanceResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/dashboard",
    response_model=FinanceDashboardResponse,
    summary="Moliyaviy dashboard (OWNER/MANAGER)",
)
async def finance_dashboard(
    period_start: date = Query(..., description="Davr boshi (YYYY-MM-DD)"),
    period_end: date = Query(..., description="Davr oxiri (YYYY-MM-DD)"),
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha ko'rinadigan"
    ),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> FinanceDashboardResponse:
    return await AnalyticsService(session).dashboard(
        current_user, period_start, period_end, branch_id
    )


@router.get(
    "/monthly",
    response_model=MonthlyFinanceResponse,
    summary="Oylik moliyaviy tendensiya (OWNER/MANAGER)",
)
async def monthly_finance(
    months: int = Query(default=6, ge=1, le=24),
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha ko'rinadigan"
    ),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> MonthlyFinanceResponse:
    """Bosh sahifadagi tendensiya grafigi uchun.

    Ilgari frontend har bir oy uchun `/analytics/dashboard` ni alohida
    chaqirardi — 6 oylik grafik 6 ta to'liq hisob degani edi.
    """
    return await AnalyticsService(session).monthly(current_user, months, branch_id)
