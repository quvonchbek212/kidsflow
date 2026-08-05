"""Kunlik hisobot endpointlari (4.4-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.daily_report import (
    DailyReportCreateRequest,
    DailyReportResponse,
    DailyReportRosterRow,
    DailyReportUpdateRequest,
)
from app.services.daily_report_service import DailyReportService

router = APIRouter(tags=["daily-reports"])


@router.post(
    "/daily-reports",
    response_model=DailyReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kunlik hisobot yaratish (TEACHER/MANAGER)",
)
async def create_report(
    payload: DailyReportCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyReportResponse:
    service = DailyReportService(session)
    report = await service.create(payload, current_user)
    return await service.to_response(report)


@router.patch(
    "/daily-reports/{report_id}",
    response_model=DailyReportResponse,
    summary="Qoralama hisobotni tahrirlash",
)
async def update_report(
    report_id: uuid.UUID,
    payload: DailyReportUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyReportResponse:
    service = DailyReportService(session)
    report = await service.update(report_id, payload, current_user)
    return await service.to_response(report)


@router.post(
    "/daily-reports/{report_id}/publish",
    response_model=DailyReportResponse,
    summary="Hisobotni e'lon qilish (ota-onaga bildirishnoma navbatga qo'yiladi)",
)
async def publish_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyReportResponse:
    service = DailyReportService(session)
    report = await service.publish(report_id, current_user)
    return await service.to_response(report)


@router.get(
    "/daily-reports/roster",
    response_model=list[DailyReportRosterRow],
    summary="Guruh bo'yicha kunlik hisobot rosteri (TEACHER/MANAGER/OWNER)",
)
async def daily_report_roster(
    group_id: uuid.UUID = Query(...),
    report_date: date = Query(..., alias="date"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DailyReportRosterRow]:
    return await DailyReportService(session).roster_for_group(
        group_id, report_date, current_user
    )


# DIQQAT: bu marshrut `/daily-reports/roster` dan KEYIN turishi shart — aks holda
# FastAPI "roster" so'zini `report_id` deb o'qib, UUID validatsiyasida yiqiladi.
@router.get(
    "/daily-reports/{report_id}",
    response_model=DailyReportResponse,
    summary="Hisobotni ko'rish",
)
async def get_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyReportResponse:
    service = DailyReportService(session)
    report = await service.get(report_id, current_user)
    return await service.to_response(report)


@router.get(
    "/children/{child_id}/daily-reports",
    response_model=list[DailyReportResponse],
    summary="Bola kunlik hisobotlari (ota-ona faqat e'lon qilinganini ko'radi)",
)
async def list_child_reports(
    child_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DailyReportResponse]:
    service = DailyReportService(session)
    reports = await service.list_for_child(child_id, current_user)
    return await service.to_responses(reports)
