"""Outbox hodisalari va bildirishnomalar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationStatus, OutboxStatus
from app.models.messaging import DailyJobRun, Notification, OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: OutboxEvent) -> None:
        self._session.add(event)

    async def fetch_pending(self, limit: int = 50) -> list[OutboxEvent]:
        """Qayta ishlashga tayyor (PENDING va available_at o'tgan) hodisalar."""
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxStatus.PENDING.value,
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.available_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, notification: Notification) -> None:
        self._session.add(notification)

    async def fetch_pending(self, limit: int = 50) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING.value)
            .order_by(Notification.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_user(
        self, user_id: uuid.UUID, limit: int = 100
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_sent_for_users_since(
        self, user_ids: list[uuid.UUID], since: datetime
    ) -> int:
        """Berilgan foydalanuvchilarga shu sanadan beri yuborilgan xabarlar soni."""
        if not user_ids:
            return 0
        stmt = select(func.count()).where(
            Notification.user_id.in_(user_ids),
            Notification.status == NotificationStatus.SENT.value,
            Notification.sent_at >= since,
        )
        return int((await self._session.execute(stmt)).scalar_one())


class DailyJobRepository:
    """Kunlik ish (scheduler) belgisi — bir kunda bir marta bajarilishini
    ta'minlaydi, alohida scheduling kutubxonasisiz (9-bo'lim kengaytmasi)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_claim(self, job_name: str, run_date: date) -> bool:
        """Bugungi kun uchun ishni "band qilishga" urinadi.

        `True` — hech kim hali bajarmagan (endi sen bajarasan). `False` —
        allaqachon bajarilgan (yoki parallel ravishda band qilingan).
        SAVEPOINT (`begin_nested`) ishlatiladi — muvaffaqiyatsizlikda faqat
        shu urinish bekor bo'ladi, sessiyadagi boshqa o'zgarishlar saqlanadi.
        """
        try:
            async with self._session.begin_nested():
                self._session.add(DailyJobRun(job_name=job_name, run_date=run_date))
                await self._session.flush()
        except IntegrityError:
            return False
        return True
