"""Telegram taklif kodi va hisobni bog'lash sxemalari (7-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InvitationCreateResponse(BaseModel):
    """Menejerga qaytariladi — kod ota-onaga og'zaki/qo'lda beriladi."""

    code: str
    user_id: uuid.UUID
    expires_at: datetime


class TelegramLinkRequest(BaseModel):
    """Bot backendga yuboradigan so'rov (bot API token bilan himoyalangan)."""

    code: str = Field(min_length=1, max_length=64)
    telegram_user_id: int
    telegram_chat_id: int | None = None


class TelegramLinkResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    linked: bool
