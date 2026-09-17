"""Enrollment sxemalari."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import DiscountType, EnrollmentStatus


class EnrollmentCreateRequest(BaseModel):
    branch_id: uuid.UUID
    group_id: uuid.UUID
    start_date: date
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    notes: str | None = Field(default=None, max_length=1000)
    discount_type: DiscountType | None = None
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)


class EnrollmentUpdateRequest(BaseModel):
    status: EnrollmentStatus | None = None
    # Faqat navbatdagi (PLANNED) enrollment uchun: qabul qilinganda asl
    # "kutilayotgan sana" haqiqiy qabul sanasiga almashtiriladi.
    start_date: date | None = None
    end_date: date | None = None
    group_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)
    discount_type: DiscountType | None = None
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)


class EnrollmentResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    branch_id: uuid.UUID
    group_id: uuid.UUID
    start_date: date
    end_date: date | None
    status: str
    notes: str | None
    discount_type: str | None
    discount_percent: Decimal | None


class ChildTransferRequest(BaseModel):
    """Bolani boshqa guruhga ko'chirish (guruh o'zgartirish tarixi bilan)."""

    new_group_id: uuid.UUID
    effective_date: date
    reason: str | None = Field(default=None, max_length=1000)
    # Berilmasa eski enrollment'dagi chegirma meros qilib olinadi.
    discount_type: DiscountType | None = None
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)
