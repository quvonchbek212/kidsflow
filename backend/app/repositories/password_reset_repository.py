"""Parolni tiklash tokenlari uchun DB so'rovlari."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, token: PasswordResetToken) -> None:
        self._session.add(token)

    async def get_active_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        """Ishlatilmagan va muddati o'tmagan tokenni qaytaradi."""
        now = datetime.now(UTC)
        stmt = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def mark_used(token: PasswordResetToken) -> None:
        if token.used_at is None:
            token.used_at = datetime.now(UTC)
