"""Guruhlar va guruh tarbiyachilari (5.3-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Group(UUIDMixin, TimestampMixin, Base):
    """Filial ichidagi guruh."""

    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_groups_capacity_positive"),
        CheckConstraint(
            "min_age_months IS NULL OR max_age_months IS NULL "
            "OR min_age_months <= max_age_months",
            name="ck_groups_age_range",
        ),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Guruhga bog'langan oylik tarif (mockup: guruh = tarif). Hisob-faktura
    # summasining yagona manbai; belgilanmagan guruhga hisob yaratilmaydi.
    monthly_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    teachers: Mapped[list[GroupTeacher]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GroupTeacher(UUIDMixin, TimestampMixin, Base):
    """Guruh–tarbiyachi aloqasi (many-to-many, 16-bo'lim 8-qoida)."""

    __tablename__ = "group_teachers"

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    group: Mapped[Group] = relationship(back_populates="teachers")
