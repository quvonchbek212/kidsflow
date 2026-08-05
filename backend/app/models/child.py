"""Bolalar va vasiylar (5.3-bo'lim).

Bola modeli ichida bitta `parent_id` yoki doimiy `group_id` saqlanmaydi —
aloqalar tarixni saqlaydigan jadvallar orqali yuritiladi (4.2-bo'lim).
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Child(UUIDMixin, TimestampMixin, Base):
    """Bola profili."""

    __tablename__ = "children"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Tibbiy izohlar shifrlangan holda saqlanadi (11-bo'lim).
    medical_notes_encrypted: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    photo_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    guardians: Mapped[list[ChildGuardian]] = relationship(
        back_populates="child",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChildGuardian(UUIDMixin, TimestampMixin, Base):
    """Bola–vasiy aloqasi (many-to-many, 16-bo'lim 8-qoida)."""

    __tablename__ = "child_guardians"
    __table_args__ = (
        UniqueConstraint("child_id", "guardian_user_id", name="uq_child_guardian_pair"),
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guardian_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(16), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_pick_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    receives_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    child: Mapped[Child] = relationship(back_populates="guardians")
