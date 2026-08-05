"""Filiallar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Branch


class BranchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, branch_id: uuid.UUID) -> Branch | None:
        return await self._session.get(Branch, branch_id)

    async def list_all(self) -> list[Branch]:
        stmt = select(Branch).order_by(Branch.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_ids(self, branch_ids: Sequence[uuid.UUID]) -> list[Branch]:
        if not branch_ids:
            return []
        stmt = select(Branch).where(Branch.id.in_(branch_ids)).order_by(Branch.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def add(self, branch: Branch) -> None:
        self._session.add(branch)
