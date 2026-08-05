"""Guruh va guruh tarbiyachisi endpointlari (5.3-bo'lim)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group
from app.schemas.group import (
    GroupCreateRequest,
    GroupResponse,
    GroupTeacherAssignRequest,
    GroupTeacherResponse,
    GroupUpdateRequest,
    TeacherSummary,
)
from app.services.group_service import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


def _to_response(group: Group) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        branch_id=group.branch_id,
        name=group.name,
        min_age_months=group.min_age_months,
        max_age_months=group.max_age_months,
        capacity=group.capacity,
        is_active=group.is_active,
        monthly_fee=group.monthly_fee,
        room_number=group.room_number,
        teachers=[
            TeacherSummary(teacher_user_id=t.teacher_user_id, is_primary=t.is_primary)
            for t in group.teachers
        ],
    )


@router.get("", response_model=list[GroupResponse], summary="Guruhlar ro'yxati")
async def list_groups(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[GroupResponse]:
    groups = await GroupService(session).list_visible(current_user)
    return [_to_response(g) for g in groups]


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guruh yaratish (MANAGER/OWNER)",
)
async def create_group(
    payload: GroupCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GroupResponse:
    group = await GroupService(session).create(payload, current_user)
    return _to_response(group)


@router.get("/{group_id}", response_model=GroupResponse, summary="Guruh ma'lumoti")
async def get_group(
    group_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GroupResponse:
    group = await GroupService(session).get(group_id, current_user)
    return _to_response(group)


@router.patch("/{group_id}", response_model=GroupResponse, summary="Guruhni tahrirlash")
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GroupResponse:
    group = await GroupService(session).update(group_id, payload, current_user)
    return _to_response(group)


@router.post(
    "/{group_id}/teachers",
    response_model=GroupTeacherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guruhga tarbiyachi biriktirish (MANAGER/OWNER)",
)
async def assign_teacher(
    group_id: uuid.UUID,
    payload: GroupTeacherAssignRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GroupTeacherResponse:
    link = await GroupService(session).assign_teacher(group_id, payload, current_user)
    return GroupTeacherResponse(
        id=link.id,
        group_id=link.group_id,
        teacher_user_id=link.teacher_user_id,
        is_primary=link.is_primary,
    )
