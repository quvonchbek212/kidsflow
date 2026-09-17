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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
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


class BranchNotificationSettings(UUIDMixin, TimestampMixin, Base):
    """Bildirishnoma sozlamalari — HAR FILIAL uchun alohida.

    Ilgari bu sozlamalar yagona global `kindergarten_settings.notification_toggles`
    da turardi, ya'ni bir filialda o'chirilgan tur hamma filialda o'chib qolardi.
    Filiallar mustaqil ishlagani uchun (o'z guruhlari, xodimlari, hisobotlari)
    bildirishnoma qoidalari ham filialga bog'lanadi.
    """

    __tablename__ = "branch_notification_settings"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Tur nomi -> yoqilganmi. Kalit topilmasa yoqilgan hisoblanadi.
    toggles: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # To'lov muddati yaqinlashganda necha kun oldin eslatiladi.
    payment_reminder_days_before: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    # Muddatdan necha kun o'tgach qarz ogohlantirishi yuboriladi.
    debt_warning_days_late: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    # Oylik hisob-faktura to'lov muddati — har oyning shu sanasi (1–28).
    # Hisob-fakturalar avtomatik yaratiladi (`auto_billing`), shuning uchun
    # muddat ham qo'lda kiritilmaydi, filial sozlamasidan olinadi.
    invoice_due_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


class ParentMessage(UUIDMixin, Base):
    """Ota-ona bilan xodim o'rtasidagi yozishma.

    `Notification` faqat CHIQUVCHI xabar uchun (foydalanuvchi + chat id), ya'ni
    ota-onadan kelgan savolni saqlaydigan joy yo'q edi. Bu jadval ikkala
    yo'nalishni ham bitta suhbat sifatida saqlaydi.
    """

    __tablename__ = "parent_messages"
    __table_args__ = (
        Index(
            "ix_parent_messages_thread",
            "branch_id",
            "guardian_user_id",
            "created_at",
        ),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guardian_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Xodim o'qigan vaqt — faqat `IN` xabarlar uchun ma'noga ega.
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Javobni kim yozgani — faqat `OUT` uchun. Xodim o'chirilsa NULL bo'ladi,
    # yozishma esa saqlanib qoladi.
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
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
    __table_args__ = (
        # Worker har 5 soniyada navbatni so'raydi; jadval esa doim o'sadi.
        # Qisman indeks faqat kutayotgan yozuvlarni qamraydi — kichik qoladi.
        Index(
            "ix_notifications_pending",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
            sqlite_where=text("status = 'PENDING'"),
        ),
    )

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
