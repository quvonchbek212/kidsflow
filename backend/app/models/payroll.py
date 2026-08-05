"""Oylik hisob-kitobi (payroll run) — 7-bosqich B kengaytmasi.

Har bir hisoblash bitta xodim, bitta oy uchun; natijada bog'langan `Expense`
yozuvi ("Ish haqi" kategoriyasi) yaratiladi — shu orqali xarajat hisobotlari/
break-even hisob-kitobida payroll avtomatik hisobga olinadi. Moliyaviy
yozuvlar o'chirilmaydi — noto'g'ri hisoblash `reverse` orqali tuzatiladi
(11-bo'lim), xuddi Expense/PaymentTransaction kabi.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import PayrollStatus

_Money = Numeric(18, 2)


class PayrollRun(UUIDMixin, TimestampMixin, Base):
    """Bir xodim, bir oy uchun oylik hisoblash va to'lash yozuvi.

    Bir xodimda bir davr uchun faqat bitta FAOL (RECORDED) yozuv bo'lishi
    mumkin — xuddi `Enrollment`dagi "bitta faol enrollment" qoidasi kabi,
    partial unique index orqali (11-bo'lim: yozuvlar o'chirilmaydi, faqat
    REVERSED qilinadi, shu sabab bekor qilingandan keyin xuddi shu davr uchun
    qayta hisoblash — yangi qator sifatida — mumkin bo'lishi kerak).
    """

    __tablename__ = "payroll_runs"
    __table_args__ = (
        Index(
            "uq_payroll_runs_one_active_per_period",
            "user_id",
            "period",
            unique=True,
            sqlite_where=text("status = 'RECORDED'"),
            postgresql_where=text("status = 'RECORDED'"),
        ),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Oyning birinchi sanasi (invoice/expense'dagi kabi normalizatsiya).
    period: Mapped[date] = mapped_column(Date, nullable=False)

    base_salary: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    bonus: Mapped[Decimal] = mapped_column(
        _Money, nullable=False, default=Decimal("0.00")
    )
    deduction: Mapped[Decimal] = mapped_column(
        _Money, nullable=False, default=Decimal("0.00")
    )
    advance_deducted: Mapped[Decimal] = mapped_column(
        _Money, nullable=False, default=Decimal("0.00")
    )
    net_pay: Mapped[Decimal] = mapped_column(_Money, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PayrollStatus.RECORDED.value, index=True
    )
    # Bog'langan xarajat yozuvi — payroll xarajat hisobotlarida ko'rinishi uchun.
    expense_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_payroll_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="SET NULL"), nullable=True
    )
