"""Fayl metama'lumotlari (5.8-bo'lim, 11-bo'lim).

Fayl mazmuni maxfiy joyda (storage_key bo'yicha) saqlanadi; jadval faqat
metama'lumot va xavfsizlik tekshiruvi holatini saqlaydi. Original fayl nomi
storage path sifatida ishlatilmaydi (11-bo'lim).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin
from app.models.enums import FileScanStatus


class File(UUIDMixin, Base):
    """Yuklangan fayl metama'lumoti."""

    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("storage_key", name="uq_files_storage_key"),)

    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scan_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=FileScanStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
