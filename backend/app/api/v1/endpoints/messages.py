"""Ommaviy xabar yuborish endpointlari (7-bosqich B)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import require_roles
from app.models.enums import Role
from app.schemas.messaging import (
    BroadcastCreateRequest,
    BroadcastResultResponse,
    MessagingStatsResponse,
)
from app.services.messaging_service import MessagingService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post(
    "/broadcast",
    response_model=BroadcastResultResponse,
    summary="Ota-onalarga ommaviy xabar yuborish (OWNER/MANAGER)",
)
async def broadcast(
    payload: BroadcastCreateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> BroadcastResultResponse:
    queued = await MessagingService(session).broadcast(payload, current_user)
    return BroadcastResultResponse(queued_count=queued)


@router.get(
    "/stats",
    response_model=MessagingStatsResponse,
    summary="Xabar yuborish statistikasi (OWNER/MANAGER)",
)
async def get_stats(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> MessagingStatsResponse:
    return await MessagingService(session).stats(branch_id, current_user)
