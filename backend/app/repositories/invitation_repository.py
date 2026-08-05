"""Telegram taklif kodlari uchun DB so'rovlari."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import TelegramInvitation


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, invitation: TelegramInvitation) -> None:
        self._session.add(invitation)

    async def get_active_by_hash(self, code_hash: str) -> TelegramInvitation | None:
        """Ishlatilmagan va muddati o'tmagan taklifni qaytaradi."""
        now = datetime.now(UTC)
        stmt = (
            select(TelegramInvitation)
            .where(
                TelegramInvitation.code_hash == code_hash,
                TelegramInvitation.used_at.is_(None),
                TelegramInvitation.expires_at > now,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
