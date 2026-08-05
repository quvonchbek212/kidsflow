"""Davomat endpointlari (4.3-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.attendance import Attendance
from app.schemas.attendance import (
    AttendanceBulkMarkRequest,
    AttendanceMarkRequest,
    AttendanceResponse,
    AttendanceRosterRow,
    AttendanceTrendResponse,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _to_response(record: Attendance) -> AttendanceResponse:
    return AttendanceResponse(
        id=record.id,
        branch_id=record.branch_id,
        child_id=record.child_id,
        attendance_date=record.attendance_date,
        status=record.status,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        note=record.note,
        marked_by=record.marked_by,
    )


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Davomat belgilash (TEACHER/MANAGER/OWNER)",
)
async def mark_attendance(
    payload: AttendanceMarkRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AttendanceResponse:
    record = await AttendanceService(session).mark(payload, current_user)
    return _to_response(record)


@router.get(
    "/child/{child_id}",
    response_model=list[AttendanceResponse],
    summary="Bola davomati tarixi (kirish huquqiga ega rollar)",
)
async def child_attendance(
    child_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AttendanceResponse]:
    records = await AttendanceService(session).list_for_child(child_id, current_user)
    return [_to_response(r) for r in records]


@router.get(
    "/roster",
    response_model=list[AttendanceRosterRow],
    summary="Guruh davomat rosteri (TEACHER/MANAGER/OWNER)",
)
async def group_roster(
    group_id: uuid.UUID = Query(...),
    roster_date: date = Query(..., alias="date"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AttendanceRosterRow]:
    return await AttendanceService(session).roster_for_group(
        group_id, roster_date, current_user
    )


@router.post(
    "/bulk",
    response_model=list[AttendanceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bir guruh, bir kun uchun ko'plab bolani birdaniga belgilash "
    "(TEACHER/MANAGER/OWNER)",
)
async def mark_attendance_bulk(
    payload: AttendanceBulkMarkRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AttendanceResponse]:
    records = await AttendanceService(session).mark_bulk(payload, current_user)
    return [_to_response(r) for r in records]


@router.get(
    "/trend",
    response_model=AttendanceTrendResponse,
    summary="Guruhning so'nggi N kunlik davomat trendi",
)
async def attendance_trend(
    group_id: uuid.UUID = Query(...),
    days: int = Query(default=11, ge=1, le=90),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AttendanceTrendResponse:
    points = await AttendanceService(session).trend_for_group(
        group_id, days, current_user
    )
    return AttendanceTrendResponse(group_id=group_id, points=points)
