"""Foydalanuvchi (xodim) sxemalari."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import BRANCHLESS_ROLES, EmploymentType, Role, StaffPosition
from app.utils.phone import normalize_phone
from app.utils.validators import normalize_email, normalize_username


class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    # Login uchun ishlatiladigan ism/taxallus (masalan "Quvonchbek").
    username: str = Field(min_length=3, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    role: Role
    # Kadrlar bo'limida guruhlash uchun yorliq. Berilmasa `role` nomidan olinadi.
    position: StaffPosition | None = None
    branch_id: uuid.UUID | None = None
    preferred_language: str = "uz"
    monthly_salary: Decimal | None = Field(default=None, ge=0)
    birth_date: date | None = None
    passport_number: str | None = Field(default=None, max_length=20)
    hire_date: date | None = None
    employment_type: EmploymentType | None = None

    @field_validator("username")
    @classmethod
    def _norm_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str | None) -> str | None:
        return normalize_email(value)

    @model_validator(mode="after")
    def _check_contact_and_branch(self) -> StaffCreateRequest:
        # Kamida bitta aloqa (telefon yoki email) bo'lishi kerak.
        if not self.phone and not self.email:
            raise ValueError("Telefon yoki email ko'rsatilishi shart.")
        # Filial talab qilinadigan rollar uchun branch_id majburiy (5.2-bo'lim).
        if self.role not in BRANCHLESS_ROLES and self.branch_id is None:
            raise ValueError(f"{self.role} roli uchun branch_id majburiy.")
        if self.role in BRANCHLESS_ROLES and self.branch_id is not None:
            raise ValueError(f"{self.role} roli filialga bog'lanmaydi.")
        return self


class RoleGrantOut(BaseModel):
    role: str
    branch_id: uuid.UUID | None


class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    username: str | None
    phone: str | None
    email: str | None
    is_active: bool
    position: str | None
    monthly_salary: Decimal | None
    birth_date: date | None
    passport_number: str | None
    hire_date: date | None
    employment_type: str | None
    roles: list[RoleGrantOut]


class SalaryUpdateRequest(BaseModel):
    monthly_salary: Decimal = Field(ge=0)


class StaffUpdateRequest(BaseModel):
    """Xodim profilini tahrirlash (OWNER). Berilgan maydonlar yangilanadi."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    position: StaffPosition | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0)
    birth_date: date | None = None
    passport_number: str | None = Field(default=None, max_length=20)
    hire_date: date | None = None
    employment_type: EmploymentType | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str | None) -> str | None:
        return normalize_email(value)


class PayrollStaffRow(BaseModel):
    id: uuid.UUID
    full_name: str
    position: str | None
    role: str
    monthly_salary: Decimal


class PayrollSummaryResponse(BaseModel):
    total_fund: Decimal
    staff: list[PayrollStaffRow]


class ParentRow(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    email: str | None
    telegram_linked: bool
    children_names: list[str]
