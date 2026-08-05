"""Moliyaviy modellar: tarif, invoice, to'lov, tuzatma va xarajat (5.5, 5.6-bo'lim).

Pul qiymatlari NUMERIC(18,2) (Decimal). Moliyaviy yozuvlar o'chirilmaydi —
noto'g'ri yozuv reversal yoki adjustment bilan tuzatiladi (11-bo'lim).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import (
    ExpenseStatus,
    InvoiceStatus,
    PaymentStatus,
)

# Pul ustuni turi.
_Money = Numeric(18, 2)


class FeePlan(UUIDMixin, TimestampMixin, Base):
    """Filial uchun oylik tarif rejasi."""

    __tablename__ = "fee_plans"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Invoice(UUIDMixin, TimestampMixin, Base):
    """Bir bola, bir billing_period uchun hisob-faktura."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("child_id", "billing_period", name="uq_invoice_child_period"),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True
    )
    # Oyning birinchi sanasi (5.5-bo'lim: matn emas, DATE).
    billing_period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    original_amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        _Money, nullable=False, default=Decimal("0.00")
    )
    adjusted_amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        _Money, nullable=False, default=Decimal("0.00")
    )
    outstanding_amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=InvoiceStatus.OPEN.value, index=True
    )


class PaymentTransaction(UUIDMixin, TimestampMixin, Base):
    """Real to'lov tranzaksiyasi (menejer qo'lda kiritadi, 4.5-bo'lim)."""

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PaymentStatus.RECORDED.value, index=True
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PaymentAllocation(UUIDMixin, Base):
    """To'lovning invoice'ga taqsimlangan qismi."""

    __tablename__ = "payment_allocations"

    payment_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payment_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)


class InvoiceAdjustment(UUIDMixin, TimestampMixin, Base):
    """Invoice tuzatmasi: chegirma, qo'shimcha yoki qarzni kechirish."""

    __tablename__ = "invoice_adjustments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adjustment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ExpenseCategory(UUIDMixin, TimestampMixin, Base):
    """Xarajat kategoriyasi (5.6-bo'lim)."""

    __tablename__ = "expense_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_expense_category_name"),)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Zararsizlik (break-even) hisobida "o'zgaruvchan xarajat" sifatida
    # hisoblanadimi (masalan Oziq-ovqat — bola soniga bog'liq). Standart holda
    # doimiy xarajat deb hisoblanadi (False).
    is_variable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Expense(UUIDMixin, TimestampMixin, Base):
    """Filial xarajati (5.6-bo'lim)."""

    __tablename__ = "expenses"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(_Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ExpenseStatus.RECORDED.value, index=True
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_expense_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True
    )
    # Har oy takrorlanadigan xarajatmi (ijara, internet) — faqat belgi, avtomatik
    # qayta yaratilmaydi (mockup: shunchaki checkbox).
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
