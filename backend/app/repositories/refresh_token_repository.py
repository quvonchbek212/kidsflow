"""Refresh tokenlar uchun DB so'rovlari."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, token: RefreshToken) -> None:
        self._session.add(token)

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Bekor qilinmagan va muddati o'tmagan tokenni qaytaradi."""
        now = datetime.now(UTC)
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def revoke(token: RefreshToken) -> None:
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
