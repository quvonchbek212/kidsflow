"""Moliyaviy dashboard endpointi (4.7-bo'lim)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import require_roles
from app.models.enums import Role
from app.schemas.finance import FinanceDashboardResponse
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
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> FinanceDashboardResponse:
    return await AnalyticsService(session).dashboard(
        current_user, period_start, period_end
    )
