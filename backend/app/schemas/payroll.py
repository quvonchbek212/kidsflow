"""Payroll (oylik hisoblash) sxemalari."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayrollRunCreateRequest(BaseModel):
    branch_id: uuid.UUID
    user_id: uuid.UUID
    period: date
    # Berilmasa xodimning `monthly_salary`si ishlatiladi.
    base_salary: Decimal | None = Field(default=None, ge=0)
    bonus: Decimal = Field(default=Decimal("0"), ge=0)
    deduction: Decimal = Field(default=Decimal("0"), ge=0)
    # Shu oy uchun avans yozuvlari bo'lsa, ularning yig'indisi avtomatik
    # ushlanadi va bu maydon e'tiborga olinmaydi. Yozuv yo'q bo'lsagina
    # qo'lda kiritilgan qiymat ishlatiladi (eski oqim bilan moslik).
    advance_deducted: Decimal | None = Field(default=None, ge=0)
    paid_at: datetime


class PayrollRunResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    user_id: uuid.UUID
    period: date
    base_salary: Decimal
    bonus: Decimal
    deduction: Decimal
    advance_deducted: Decimal
    net_pay: Decimal
    status: str
    expense_id: uuid.UUID | None
    paid_at: datetime


class SalaryAdvanceCreateRequest(BaseModel):
    branch_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    paid_at: datetime
    note: str | None = Field(default=None, max_length=255)


class SalaryAdvanceResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    user_id: uuid.UUID
    period: date
    amount: Decimal
    note: str | None
    status: str
    expense_id: uuid.UUID | None
    paid_at: datetime
