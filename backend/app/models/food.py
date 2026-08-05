"""Oziq-ovqat va oshxona ombori: mahsulotlar, ombor harakati, ovqat menyusi.

Ombor qoldig'i alohida ustunda saqlanmaydi — har doim `food_stock_movements`
yozuvlaridan (append-only ledger) hisoblanadi, moliya modulidagi kabi (11-bo'lim:
yozuvlar o'zgartirilmaydi, faqat yangi harakat qo'shiladi).
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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

_QTY = Numeric(18, 3)
_MONEY = Numeric(18, 2)


class FoodProduct(UUIDMixin, TimestampMixin, Base):
    """Ombordagi mahsulot (masalan: guruch, kartoshka, sut)."""

    __tablename__ = "food_products"
    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_food_product_branch_name"),
    )

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)  # kg, litr, dona...
    unit_cost: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FoodStockMovement(UUIDMixin, Base):
    """Ombor harakati (kirim/chiqim) — o'zgarmas yozuv (append-only ledger)."""

    __tablename__ = "food_stock_movements"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("food_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(8), nullable=False)  # IN/OUT
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meal_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("meal_logs.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Meal(UUIDMixin, TimestampMixin, Base):
    """Ovqat turi/menyusi (masalan: osh, sho'rva)."""

    __tablename__ = "meals"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ingredients: Mapped[list[MealIngredient]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MealIngredient(UUIDMixin, Base):
    """Ovqat retsepti — bir porsiya uchun mahsulot sarfi."""

    __tablename__ = "meal_ingredients"
    __table_args__ = (
        UniqueConstraint("meal_id", "product_id", name="uq_meal_ingredient_pair"),
    )

    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("food_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity_per_serving: Mapped[Decimal] = mapped_column(_QTY, nullable=False)

    meal: Mapped[Meal] = relationship(back_populates="ingredients")


class MealLog(UUIDMixin, Base):
    """Ovqat berilgani haqidagi yozuv — mahsulot sarfini avtomatik hisoblaydi."""

    __tablename__ = "meal_logs"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meals.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    serving_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    servings_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
