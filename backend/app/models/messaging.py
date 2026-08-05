"""Outbox hodisalari va bildirishnomalar (5.8-bo'lim, 9-bo'lim).

Muhim bildirishnoma HTTP so'rovi ichida to'g'ridan-to'g'ri Telegram'ga
yuborilmaydi: avval `outbox_events` yaratiladi, worker esa uni qayta ishlaydi.
Bu Telegram vaqtincha ishlamasa ham yozuv yo'qolmasligini ta'minlaydi.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin
from app.models.enums import NotificationStatus, OutboxStatus


class OutboxEvent(UUIDMixin, Base):
    """Transaction ichida yaratiladigan, worker qayta ishlaydigan hodisa."""

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=OutboxStatus.PENDING.value,
        index=True,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DailyJobRun(UUIDMixin, Base):
    """Kunlik avtomatik ish (masalan bildirishnoma tekshiruvi) belgisi.

    Worker har necha soniyada bir ishlaydi (5-bo'lim), lekin ba'zi ishlar
    (to'lov eslatmasi, tug'ilgan kun) kuniga bir marta bajarilishi kerak.
    Shu jadvalga (job_name, run_date) unique yozuv qo'shishga urinish orqali
    "bugun allaqachon bajarilganmi" tekshiriladi — alohida scheduler
    kutubxonasi (masalan APScheduler) talab qilinmaydi.
    """

    __tablename__ = "daily_job_runs"
    __table_args__ = (
        UniqueConstraint("job_name", "run_date", name="uq_daily_job_runs_name_date"),
    )

    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Notification(UUIDMixin, Base):
    """Foydalanuvchiga yuboriladigan (yoki yuborilgan) bildirishnoma."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=NotificationStatus.PENDING.value
    )
    # Telegram chat ID (yuborish uchun), yuborilgan vaqt va urinishlar soni.
    target_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
