"""Bog'cha sozlamalari uchun DB so'rovlari."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import KindergartenSettings


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self) -> bool:
        """Bog'cha sozlamalari (setup) allaqachon mavjudmi."""
        stmt = select(func.count()).select_from(KindergartenSettings)
        count = (await self._session.execute(stmt)).scalar_one()
        return count > 0

    async def get(self) -> KindergartenSettings | None:
        stmt = select(KindergartenSettings).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    def add(self, settings: KindergartenSettings) -> None:
        self._session.add(settings)
