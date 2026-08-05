"""Enrollment — bolani filial va guruhga qabul qilish (5.3-bo'lim).

Bola guruh tarixi shu jadval orqali saqlanadi (16-bo'lim 9-qoida). Bir bolada
bir vaqtda faqat bitta faol enrollment bo'lishi kerak — bu partial unique index
va service qatlami bilan ta'minlanadi.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import EnrollmentStatus


class Enrollment(UUIDMixin, TimestampMixin, Base):
    """Bolaning filial+guruhdagi a'zoligi."""

    __tablename__ = "enrollments"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_enrollments_date_range",
        ),
        # Bir bolada bir vaqtda faqat bitta ACTIVE enrollment (16-bo'lim).
        # Partial unique index: faqat status='ACTIVE' bo'lgan qatorlarga tegishli.
        Index(
            "uq_enrollments_one_active_per_child",
            "child_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=EnrollmentStatus.PLANNED.value
    )
    # fee_plans jadvali 4-bosqichda qo'shiladi; hozircha FK'siz ustun.
    fee_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Doimiy (standing) chegirma — invoice generatsiyasida avtomatik qo'llanadi
    # (frontend v2: bola formasidagi "Chegirma" maydoni, DiscountType enum).
    discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discount_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
