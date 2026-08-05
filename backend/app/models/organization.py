"""Tizim sozlamalari va filiallar (5.1-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class KindergartenSettings(UUIDMixin, TimestampMixin, Base):
    """Bog'chaning umumiy sozlamalari. Faqat bitta faol yozuv bo'ladi."""

    __tablename__ = "kindergarten_settings"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    logo_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Tashkent"
    )
    default_language: Mapped[str] = mapped_column(
        String(8), nullable=False, default="uz"
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    setup_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Sozlamalar sahifasi kengaytmasi (7-bosqich B). Payme/Click/2FA uchun
    # ATAYLAB hech qanday maydon qo'shilmagan (loyiha qarori).
    hours_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auto_invoice_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Avtomatik bildirishnoma turlari yoqiq/o'chiqligi, masalan
    # {"CHILD_SICK": true, "DEBT_WARNING": false}. Kalit yo'q bo'lsa — yoqiq
    # deb hisoblanadi (standart xatti-harakat, `notification_scheduler.py`).
    notification_toggles: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )


class Branch(UUIDMixin, TimestampMixin, Base):
    """Bog'cha filiali. Ma'lumotlar `branch_id` orqali ajratiladi (2.1-bo'lim)."""

    __tablename__ = "branches"
    __table_args__ = (
        # Guruh/filial sig'imi noldan katta bo'lishi kerak (5.9-bo'lim).
        CheckConstraint(
            "capacity IS NULL OR capacity > 0", name="ck_branches_capacity_positive"
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
