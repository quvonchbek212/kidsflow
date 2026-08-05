"""Kunlik hisobot va unga biriktirilgan fayllar (4.4-bo'lim, 5.4-bo'lim).

`published_at` bo'sh bo'lsa hisobot qoralama (draft) hisoblanadi. `ai_draft`
3-bosqichda ishlatilmaydi (AI 6-bosqichda qo'shiladi); `final_summary` tarbiyachi
tasdiqlagan matn.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class DailyReport(UUIDMixin, TimestampMixin, Base):
    """Bir bola, bir sana uchun kunlik hisobot."""

    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint("child_id", "report_date", name="uq_daily_report_child_date"),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    meal_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    nap_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activities_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    files: Mapped[list[DailyReportFile]] = relationship(
        back_populates="daily_report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DailyReportFile.sort_order",
    )


class DailyReportFile(UUIDMixin, Base):
    """Kunlik hisobotga biriktirilgan fayl (foto/hujjat)."""

    __tablename__ = "daily_report_files"
    __table_args__ = (
        UniqueConstraint(
            "daily_report_id", "file_id", name="uq_daily_report_file_pair"
        ),
    )

    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    daily_report: Mapped[DailyReport] = relationship(back_populates="files")
