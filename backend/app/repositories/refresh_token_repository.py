"""Refresh tokenlar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
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

    async def delete_stale(self, now: datetime) -> int:
        """Muddati o'tgan yoki bekor qilingan tokenlarni o'chiradi."""
        stmt = delete(RefreshToken).where(
            or_(RefreshToken.expires_at < now, RefreshToken.revoked_at.is_not(None))
        )
        result = await self._session.execute(stmt)
        return int(getattr(result, "rowcount", 0) or 0)

    @staticmethod
    def revoke(token: RefreshToken) -> None:
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Foydalanuvchining barcha faol sessiyalarini yopadi.

        Parol almashganda chaqiriladi. Access token qisqa umrli (15 daqiqa),
        refresh esa 30 kun yashaydi — shuning uchun parolni almashtirish eski
        refresh tokenni bekor qilmasa, o'g'irlangan sessiya bir oygacha ishlab
        turaverardi.
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        return (await self._session.execute(stmt)).rowcount or 0
