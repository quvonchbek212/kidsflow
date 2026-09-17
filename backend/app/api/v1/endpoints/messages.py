"""Xabar yuborish endpointlari: ommaviy xabar, filialning bildirishnoma
sozlamalari va ota-ona ↔ xodim yozishmalari."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import require_roles
from app.models.enums import Role
from app.schemas.messaging import (
    BranchNotificationSettingsResponse,
    BranchNotificationSettingsUpdateRequest,
    BroadcastCreateRequest,
    BroadcastResultResponse,
    MessageThreadSummary,
    MessagingStatsResponse,
    ParentMessageCreateRequest,
    ParentMessageResponse,
    StaffReplyRequest,
    UnreadCountResponse,
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


# --- Filial kesimidagi bildirishnoma sozlamalari ---


@router.get(
    "/settings",
    response_model=BranchNotificationSettingsResponse,
    summary="Filialning bildirishnoma sozlamalari (OWNER/MANAGER)",
)
async def get_notification_settings(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> BranchNotificationSettingsResponse:
    return await MessagingService(session).get_branch_settings(branch_id, current_user)


@router.patch(
    "/settings",
    response_model=BranchNotificationSettingsResponse,
    summary="Filialning bildirishnoma sozlamalarini yangilash (OWNER/MANAGER)",
)
async def update_notification_settings(
    payload: BranchNotificationSettingsUpdateRequest,
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> BranchNotificationSettingsResponse:
    return await MessagingService(session).update_branch_settings(
        branch_id, payload, current_user
    )


# --- Ota-ona ↔ xodim yozishmalari ---


@router.post(
    "/from-parent",
    status_code=201,
    summary="Ota-ona savolini yuborish (ota-ona tokeni bilan, bot orqali)",
)
async def send_from_parent(
    payload: ParentMessageCreateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.PARENT)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    message_id = await MessagingService(session).send_from_parent(
        current_user.id, payload.text
    )
    return {"id": str(message_id)}


@router.get(
    "/threads",
    response_model=list[MessageThreadSummary],
    summary="Ota-onalar bilan yozishmalar ro'yxati (OWNER/MANAGER)",
)
async def list_threads(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[MessageThreadSummary]:
    return await MessagingService(session).list_threads(branch_id, current_user)


@router.get(
    "/threads/{guardian_user_id}",
    response_model=list[ParentMessageResponse],
    summary="Bitta ota-ona bilan yozishma (OWNER/MANAGER)",
)
async def get_thread(
    guardian_user_id: uuid.UUID,
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[ParentMessageResponse]:
    return await MessagingService(session).get_thread(
        branch_id, guardian_user_id, current_user
    )


@router.post(
    "/threads/{guardian_user_id}/reply",
    response_model=ParentMessageResponse,
    status_code=201,
    summary="Ota-onaga javob yozish (OWNER/MANAGER)",
)
async def reply_to_parent(
    guardian_user_id: uuid.UUID,
    payload: StaffReplyRequest,
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> ParentMessageResponse:
    return await MessagingService(session).reply_to_parent(
        branch_id, guardian_user_id, payload.text, current_user
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="O'qilmagan savollar soni (qo'ng'iroqcha uchun)",
)
async def unread_count(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> UnreadCountResponse:
    count = await MessagingService(session).unread_count(branch_id, current_user)
    return UnreadCountResponse(unread_count=count)
