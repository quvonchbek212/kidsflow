"""Fayllar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, file: File) -> None:
        self._session.add(file)

    async def get_by_id(self, file_id: uuid.UUID) -> File | None:
        return await self._session.get(File, file_id)

    async def list_by_ids(self, file_ids: Sequence[uuid.UUID]) -> list[File]:
        if not file_ids:
            return []
        stmt = select(File).where(File.id.in_(file_ids))
        return list((await self._session.execute(stmt)).scalars().all())
