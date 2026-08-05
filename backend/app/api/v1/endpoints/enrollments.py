"""Enrollment endpointlari (5.3-bo'lim).

Enrollment yaratish `/children/{child_id}/enrollments` orqali, tahrirlash esa
`/enrollments/{id}` orqali amalga oshiriladi.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.enrollment import Enrollment
from app.schemas.enrollment import (
    ChildTransferRequest,
    EnrollmentCreateRequest,
    EnrollmentResponse,
    EnrollmentUpdateRequest,
)
from app.services.enrollment_service import EnrollmentService

router = APIRouter(tags=["enrollments"])


def _to_response(enrollment: Enrollment) -> EnrollmentResponse:
    return EnrollmentResponse(
        id=enrollment.id,
        child_id=enrollment.child_id,
        branch_id=enrollment.branch_id,
        group_id=enrollment.group_id,
        start_date=enrollment.start_date,
        end_date=enrollment.end_date,
        status=enrollment.status,
        notes=enrollment.notes,
        discount_type=enrollment.discount_type,
        discount_percent=enrollment.discount_percent,
    )


@router.post(
    "/children/{child_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bolani filial va guruhga qabul qilish (MANAGER/OWNER)",
)
async def create_enrollment(
    child_id: uuid.UUID,
    payload: EnrollmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EnrollmentResponse:
    enrollment = await EnrollmentService(session).create(
        child_id, payload, current_user
    )
    return _to_response(enrollment)


@router.patch(
    "/enrollments/{enrollment_id}",
    response_model=EnrollmentResponse,
    summary="Enrollment holatini o'zgartirish (MANAGER/OWNER)",
)
async def update_enrollment(
    enrollment_id: uuid.UUID,
    payload: EnrollmentUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EnrollmentResponse:
    enrollment = await EnrollmentService(session).update(
        enrollment_id, payload, current_user
    )
    return _to_response(enrollment)


@router.post(
    "/children/{child_id}/transfer",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bolani boshqa guruhga o'tkazish, tarix bilan (MANAGER/OWNER)",
)
async def transfer_child(
    child_id: uuid.UUID,
    payload: ChildTransferRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EnrollmentResponse:
    enrollment = await EnrollmentService(session).transfer(
        child_id, payload, current_user
    )
    return _to_response(enrollment)
