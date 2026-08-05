"""Telegram hisobini bog'lash uchun taklif kodlari (7-bo'lim).

Kod ochiq saqlanmaydi — faqat SHA-256 hash saqlanadi. Kod qisqa muddatli va bir
martalik: ishlatilgach `used_at` belgilanadi.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TelegramInvitation(UUIDMixin, TimestampMixin, Base):
    """Ota-onaning Telegram hisobini profilga bog'lash uchun taklif."""

    __tablename__ = "telegram_invitations"
    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_telegram_invitations_code_hash"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
