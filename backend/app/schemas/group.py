"""Guruh va guruh tarbiyachisi sxemalari."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class GroupCreateRequest(BaseModel):
    branch_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    min_age_months: int | None = Field(default=None, ge=0)
    max_age_months: int | None = Field(default=None, ge=0)
    capacity: int = Field(default=20, gt=0)
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    room_number: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _check_age_range(self) -> GroupCreateRequest:
        if (
            self.min_age_months is not None
            and self.max_age_months is not None
            and self.min_age_months > self.max_age_months
        ):
            raise ValueError(
                "min_age_months max_age_months dan katta bo'lmasligi kerak."
            )
        return self


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    min_age_months: int | None = Field(default=None, ge=0)
    max_age_months: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    room_number: str | None = Field(default=None, max_length=50)


class TeacherSummary(BaseModel):
    teacher_user_id: uuid.UUID
    is_primary: bool


class GroupResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    name: str
    min_age_months: int | None
    max_age_months: int | None
    capacity: int
    is_active: bool
    monthly_fee: Decimal | None
    room_number: str | None
    teachers: list[TeacherSummary]


class GroupTeacherAssignRequest(BaseModel):
    teacher_user_id: uuid.UUID
    is_primary: bool = False


class GroupTeacherResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    teacher_user_id: uuid.UUID
    is_primary: bool
