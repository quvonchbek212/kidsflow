"""Davomat (4.3-bo'lim, 5.4-bo'lim).

Har bir bola uchun bir sanada faqat bitta davomat yozuvi bo'ladi.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Attendance(UUIDMixin, TimestampMixin, Base):
    """Bir bola, bir sana uchun davomat yozuvi."""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "child_id", "attendance_date", name="uq_attendance_child_date"
        ),
        CheckConstraint(
            "check_out_at IS NULL OR check_in_at IS NULL "
            "OR check_out_at >= check_in_at",
            name="ck_attendance_checkout_after_checkin",
        ),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    check_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    marked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
