"""Telegram hisobini bog'lash endpointlari (7-bo'lim).

- Taklif kodini yaratish: MANAGER/OWNER (JWT bilan).
- Hisobni bog'lash: bot (X-Bot-Token bilan), JWT emas.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, require_bot_token
from app.schemas.auth import TokenResponse
from app.schemas.invitation import (
    InvitationCreateResponse,
    TelegramLinkRequest,
    TelegramLinkResponse,
)
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/telegram", tags=["telegram"])


class InvitationCreateRequest(BaseModel):
    user_id: uuid.UUID


class TelegramSessionRequest(BaseModel):
    telegram_user_id: int


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    summary="Ota-ona uchun taklif kodi yaratish (MANAGER/OWNER)",
)
async def create_invitation(
    payload: InvitationCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvitationCreateResponse:
    code, expires_at = await InvitationService(session).create_for_parent(
        payload.user_id, current_user
    )
    return InvitationCreateResponse(
        code=code, user_id=payload.user_id, expires_at=expires_at
    )


@router.post(
    "/link",
    response_model=TelegramLinkResponse,
    summary="Telegram hisobini kod orqali bog'lash (bot)",
    dependencies=[Depends(require_bot_token)],
)
async def link_telegram(
    payload: TelegramLinkRequest,
    session: AsyncSession = Depends(get_session),
) -> TelegramLinkResponse:
    user_id, full_name = await InvitationService(session).link_telegram(
        payload.code, payload.telegram_user_id, payload.telegram_chat_id
    )
    return TelegramLinkResponse(user_id=user_id, full_name=full_name, linked=True)


@router.post(
    "/session",
    response_model=TokenResponse,
    summary="Bog'langan ota-ona uchun token olish (bot)",
    dependencies=[Depends(require_bot_token)],
)
async def telegram_session(
    payload: TelegramSessionRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    return await AuthService(session).issue_for_telegram(payload.telegram_user_id)
