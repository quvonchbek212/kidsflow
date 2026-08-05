"""AI foydalanish jurnali va bilim bazasi uchun DB so'rovlari (10-bo'lim)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIUsageLog, KnowledgeDocument


class AIUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, log: AIUsageLog) -> None:
        self._session.add(log)

    async def tokens_since(self, since: date) -> int:
        """Berilgan sanadan beri sarflangan umumiy tokenlar (limit uchun)."""
        stmt = select(
            func.coalesce(
                func.sum(AIUsageLog.input_tokens + AIUsageLog.output_tokens), 0
            )
        ).where(func.date(AIUsageLog.created_at) >= since)
        return int((await self._session.execute(stmt)).scalar_one())

    async def recent(self, limit: int = 100) -> list[AIUsageLog]:
        stmt = select(AIUsageLog).order_by(AIUsageLog.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars().all())


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, doc: KnowledgeDocument) -> None:
        self._session.add(doc)

    async def list_active(
        self, branch_ids: Sequence[uuid.UUID]
    ) -> list[KnowledgeDocument]:
        """Faol hujjatlar: umumiy (branch_id NULL) yoki berilgan filiallarga xos."""
        conditions = [KnowledgeDocument.branch_id.is_(None)]
        if branch_ids:
            conditions.append(KnowledgeDocument.branch_id.in_(branch_ids))
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.is_active.is_(True),
                or_(*conditions),
            )
            .order_by(KnowledgeDocument.title)
        )
        return list((await self._session.execute(stmt)).scalars().all())
