"""ORM modellar uchun umumiy ustunlar (5-bo'lim: id/created_at/updated_at).

UUID kalitlari va vaqt belgilari barcha asosiy jadvallarda bo'ladi. Turlar
cross-database (PostgreSQL va testdagi SQLite) ishlashi uchun umumiy SQLAlchemy
tiplaridan foydalaniladi.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """UUID birlamchi kalit."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Yaratilgan va tahrirlangan vaqt (UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
