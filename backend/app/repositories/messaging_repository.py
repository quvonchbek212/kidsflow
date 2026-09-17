"""Outbox hodisalari va bildirishnomalar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MessageDirection, NotificationStatus, OutboxStatus
from app.models.messaging import (
    BranchNotificationSettings,
    DailyJobRun,
    Notification,
    OutboxEvent,
    ParentMessage,
)


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

    async def fetch_pending(
        self, limit: int = 50, max_retries: int = 5
    ) -> list[Notification]:
        """Yuborishga navbatdagi bildirishnomalar.

        Urinishlari tugaganlari olinmaydi: ilgari yuborib bo'lmaydigan xabarlar
        (bot bloklangan, chat_id yo'q) `PENDING` bo'lib qolaverar va eng eski
        bo'lgani uchun har siklda birinchi 50 o'rinni egallardi — 50 tasi
        yig'ilgach yangi bildirishnomalar umuman yuborilmay qolardi.

        `skip_locked` — ikkinchi worker nusxasi o'sha yozuvlarni qayta olmasin.
        """
        stmt = (
            select(Notification)
            .where(
                Notification.status == NotificationStatus.PENDING.value,
                Notification.retry_count < max_retries,
            )
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
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


class BranchNotificationSettingsRepository:
    """Filial kesimidagi bildirishnoma sozlamalari.

    Yozuv topilmasa standart qiymatlar ishlatiladi (yangi filial uchun alohida
    qator yaratish shart emas) — `get_or_create()` shu uchun.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, branch_id: uuid.UUID) -> BranchNotificationSettings | None:
        stmt = select(BranchNotificationSettings).where(
            BranchNotificationSettings.branch_id == branch_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_branches(
        self, branch_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, BranchNotificationSettings]:
        """Bir nechta filial sozlamalarini bitta so'rovda oladi (worker uchun)."""
        if not branch_ids:
            return {}
        stmt = select(BranchNotificationSettings).where(
            BranchNotificationSettings.branch_id.in_(branch_ids)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {row.branch_id: row for row in rows}

    async def get_or_create(self, branch_id: uuid.UUID) -> BranchNotificationSettings:
        existing = await self.get(branch_id)
        if existing is not None:
            return existing
        created = BranchNotificationSettings(branch_id=branch_id, toggles={})
        self._session.add(created)
        await self._session.flush()
        return created


class ParentMessageRepository:
    """Ota-ona ↔ xodim yozishmalari."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, message: ParentMessage) -> None:
        self._session.add(message)

    async def list_thread(
        self, branch_id: uuid.UUID, guardian_user_id: uuid.UUID, limit: int = 200
    ) -> list[ParentMessage]:
        stmt = (
            select(ParentMessage)
            .where(
                ParentMessage.branch_id == branch_id,
                ParentMessage.guardian_user_id == guardian_user_id,
            )
            .order_by(ParentMessage.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def thread_summaries(self, branch_id: uuid.UUID) -> list[tuple]:
        """Suhbatlar ro'yxati: vasiy, oxirgi xabar vaqti va o'qilmaganlar soni.

        Bitta so'rovda — suhbat boshiga alohida so'rov yubormaslik uchun.
        """
        stmt = (
            select(
                ParentMessage.guardian_user_id,
                func.max(ParentMessage.created_at).label("last_at"),
                func.sum(
                    case(
                        (
                            (ParentMessage.direction == MessageDirection.IN.value)
                            & ParentMessage.read_at.is_(None),
                            1,
                        ),
                        else_=0,
                    )
                ).label("unread"),
            )
            .where(ParentMessage.branch_id == branch_id)
            .group_by(ParentMessage.guardian_user_id)
            .order_by(func.max(ParentMessage.created_at).desc())
        )
        return list((await self._session.execute(stmt)).all())

    async def last_message_texts(self, branch_id: uuid.UUID) -> dict[uuid.UUID, str]:
        """Har bir suhbatning eng so'nggi xabar matni — BITTA so'rovda.

        Suhbatlar ro'yxatida "nima haqida" ekanini ko'rsatish uchun kerak.
        Har suhbat uchun alohida so'rov yuborilsa N+1 bo'lardi, shuning uchun
        eng katta `created_at` bo'yicha o'z-o'ziga join qilinadi (bu SQLite va
        PostgreSQL da bir xil ishlaydi — `DISTINCT ON` esa faqat Postgres'da).
        """
        latest = (
            select(
                ParentMessage.guardian_user_id.label("gid"),
                func.max(ParentMessage.created_at).label("mx"),
            )
            .where(ParentMessage.branch_id == branch_id)
            .group_by(ParentMessage.guardian_user_id)
            .subquery()
        )
        stmt = (
            select(ParentMessage.guardian_user_id, ParentMessage.text)
            .join(
                latest,
                (ParentMessage.guardian_user_id == latest.c.gid)
                & (ParentMessage.created_at == latest.c.mx),
            )
            .where(ParentMessage.branch_id == branch_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}

    async def unread_count(self, branch_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            ParentMessage.branch_id == branch_id,
            ParentMessage.direction == MessageDirection.IN.value,
            ParentMessage.read_at.is_(None),
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def mark_thread_read(
        self, branch_id: uuid.UUID, guardian_user_id: uuid.UUID
    ) -> None:
        stmt = (
            update(ParentMessage)
            .where(
                ParentMessage.branch_id == branch_id,
                ParentMessage.guardian_user_id == guardian_user_id,
                ParentMessage.direction == MessageDirection.IN.value,
                ParentMessage.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
