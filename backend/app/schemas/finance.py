"""Moliyaviy sxemalar: tarif, invoice, to'lov, tuzatma, xarajat, dashboard."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AdjustmentType, PaymentMethod

# --- Fee plan ---


class FeePlanCreateRequest(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    monthly_amount: Decimal = Field(gt=0)
    currency: str = "UZS"


class FeePlanResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    monthly_amount: Decimal
    currency: str
    is_active: bool


# --- Invoice ---


class InvoiceGenerateRequest(BaseModel):
    branch_id: uuid.UUID
    billing_period: date  # oyning istalgan sanasi — birinchi kunga normallashtiriladi
    due_day: int = Field(default=10, ge=1, le=28)
    # Enrollment'da fee_plan bo'lmasa ishlatiladigan standart tarif.
    fee_plan_id: uuid.UUID | None = None


class InvoiceGenerateResponse(BaseModel):
    created: int
    skipped: int
    billing_period: date


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    child_id: uuid.UUID
    billing_period: date
    due_date: date
    original_amount: Decimal
    discount_amount: Decimal
    adjusted_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str


# --- Payment ---


class PaymentRecordRequest(BaseModel):
    child_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    paid_at: datetime
    reference: str | None = Field(default=None, max_length=255)
    receipt_file_id: uuid.UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)


class PaymentAllocationOut(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal


class PaymentResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    child_id: uuid.UUID
    amount: Decimal
    payment_method: str
    paid_at: datetime
    status: str
    allocations: list[PaymentAllocationOut]
    unallocated_amount: Decimal


# --- Adjustment ---


class AdjustmentCreateRequest(BaseModel):
    adjustment_type: AdjustmentType
    amount: Decimal = Field(gt=0)
    reason: str | None = Field(default=None, max_length=1000)


# --- Expense ---


class ExpenseCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_system: bool
    is_active: bool
    is_variable: bool


class ExpenseCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    is_variable: bool = False


class ExpenseCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_variable: bool | None = None
    is_active: bool | None = None


class ExpenseRecordRequest(BaseModel):
    branch_id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    expense_date: date
    vendor: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    receipt_file_id: uuid.UUID | None = None
    is_recurring: bool = False


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal
    expense_date: date
    vendor: str | None
    description: str | None
    status: str
    is_recurring: bool


# --- Dashboard ---


class BranchFinanceSummary(BaseModel):
    branch_id: uuid.UUID
    accrual_revenue: Decimal  # invoice bo'yicha hisoblangan (adjusted)
    cash_collected: Decimal  # real tushgan pul
    outstanding: Decimal  # qarzdorlik
    expenses: Decimal
    net_cash: Decimal  # cash_collected - expenses


class DebtAgingBucket(BaseModel):
    """Qarzdorlik "yoshi" bo'yicha bitta guruh (dashboard aging widget)."""

    label: str  # not_due | aging_1_30 | aging_31_60 | aging_60_plus
    total: Decimal


class GroupRevenueRow(BaseModel):
    group_id: uuid.UUID
    total: Decimal


class CategoryExpenseRow(BaseModel):
    category_id: uuid.UUID
    category_name: str
    total: Decimal
    is_variable: bool


class BreakEvenSummary(BaseModel):
    """Zararsizlik (break-even) hisob-kitobi — mockup'ning beModel() formulasi.

    fixed = is_variable=false kategoriyalar yig'indisi; variable = is_variable=true.
    contribution_margin = bola boshiga to'lov - bola boshiga o'zgaruvchan xarajat.
    """

    active_children: int
    fixed_costs: Decimal
    variable_costs: Decimal
    fee_per_child: Decimal
    variable_cost_per_child: Decimal
    contribution_margin: Decimal
    contribution_margin_ratio: Decimal
    breakeven_revenue: Decimal
    breakeven_children: int


class FinanceDashboardResponse(BaseModel):
    period_start: date
    period_end: date
    accrual_revenue: Decimal
    cash_collected: Decimal
    outstanding: Decimal
    expenses: Decimal
    net_cash: Decimal
    branches: list[BranchFinanceSummary]
    aging: list[DebtAgingBucket]
    revenue_by_group: list[GroupRevenueRow]
    expenses_by_category: list[CategoryExpenseRow]
    # Faol bola yo'q yoki marjinal daromad <= 0 bo'lsa hisoblab bo'lmaydi (None).
    break_even: BreakEvenSummary | None


class MonthlyFinancePoint(BaseModel):
    """Bir oyning moliyaviy xulosasi (tendensiya grafigi uchun)."""

    period_start: date
    period_end: date
    accrual_revenue: Decimal
    cash_collected: Decimal
    expenses: Decimal
    net_cash: Decimal


class MonthlyFinanceResponse(BaseModel):
    """Bir necha oylik tendensiya — bitta so'rovda.

    Ilgari frontend har bir oy uchun `/analytics/dashboard` ni alohida
    chaqirardi: 6 oylik grafik uchun 6 ta to'liq dashboard hisobi.
    """

    months: list[MonthlyFinancePoint]
