"""Oziq-ovqat va oshxona ombori sxemalari."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import StockMovementReason, StockMovementType

# --- Mahsulot (ombor) ---


class ProductCreateRequest(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=16)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    unit: str
    unit_cost: Decimal | None
    current_stock: Decimal
    is_active: bool


# --- Ombor harakati ---


class StockMovementRequest(BaseModel):
    product_id: uuid.UUID
    movement_type: StockMovementType
    quantity: Decimal = Field(gt=0)
    reason: StockMovementReason
    unit_cost: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None


class StockMovementResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    product_id: uuid.UUID
    movement_type: str
    quantity: Decimal
    reason: str
    unit_cost: Decimal | None
    note: str | None
    occurred_at: datetime


# --- Ovqat (menyu) ---


class MealIngredientInput(BaseModel):
    product_id: uuid.UUID
    quantity_per_serving: Decimal = Field(gt=0)


class MealCreateRequest(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    ingredients: list[MealIngredientInput] = Field(default_factory=list)


class MealIngredientOut(BaseModel):
    product_id: uuid.UUID
    quantity_per_serving: Decimal


class MealResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    ingredients: list[MealIngredientOut]


# --- Ovqat berilgani (meal log) ---


class MealLogRequest(BaseModel):
    meal_id: uuid.UUID
    serving_date: date
    servings_count: int = Field(gt=0)


class MealLogResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    meal_id: uuid.UUID
    serving_date: date
    servings_count: int


# --- Hisob-kitob (ombor hisoboti) ---


class StockReportRow(BaseModel):
    product_id: uuid.UUID
    product_name: str
    unit: str
    opening_stock: Decimal
    stock_in: Decimal
    stock_out: Decimal
    closing_stock: Decimal
    unit_cost: Decimal | None
    closing_value: Decimal


class StockReportResponse(BaseModel):
    branch_id: uuid.UUID
    period_start: date
    period_end: date
    rows: list[StockReportRow]
    total_value: Decimal
