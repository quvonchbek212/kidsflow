"""Bola va vasiy sxemalari."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import Gender, GuardianRelationship
from app.utils.phone import normalize_phone
from app.utils.timezone import today_local
from app.utils.validators import normalize_email


class ChildCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    birth_date: date
    gender: Gender | None = None
    medical_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("birth_date")
    @classmethod
    def _birth_not_future(cls, value: date) -> date:
        if value > today_local():
            raise ValueError("Tug'ilgan sana kelajakda bo'lishi mumkin emas.")
        return value


class ChildUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    birth_date: date | None = None
    gender: Gender | None = None
    medical_notes: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class GuardianSummary(BaseModel):
    guardian_user_id: uuid.UUID
    full_name: str
    relationship_type: str
    is_primary: bool
    can_pick_up: bool
    receives_notifications: bool


class ChildResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    birth_date: date
    gender: str | None
    # Faqat vakolatli rollarga (OWNER/MANAGER) to'ldiriladi.
    medical_notes: str | None
    is_active: bool
    # Enrollment holatidan hisoblanadi (ustun emas): PLANNED→waiting,
    # ACTIVE→active, boshqa barcha holat (yoki enrollment yo'q)→left.
    status: str
    guardians: list[GuardianSummary]


class GuardianCreateRequest(BaseModel):
    """Bolaga vasiy biriktirish. Mavjud bo'lmasa yangi PARENT foydalanuvchi yaratiladi."""

    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    relationship_type: GuardianRelationship
    is_primary: bool = False
    can_pick_up: bool = True
    receives_notifications: bool = True

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str | None) -> str | None:
        return normalize_email(value)

    @model_validator(mode="after")
    def _require_contact(self) -> GuardianCreateRequest:
        if not self.phone and not self.email:
            raise ValueError("Vasiy uchun telefon yoki email ko'rsatilishi shart.")
        return self


class GuardianCreateResponse(BaseModel):
    guardian_user_id: uuid.UUID
    child_id: uuid.UUID
    relationship_type: str


class ImportPreviewRow(BaseModel):
    """Excel/CSV import: bitta qatorning tekshiruv natijasi (7-bosqich B)."""

    row_number: int
    full_name: str | None
    birth_date: str | None
    guardian_name: str | None
    guardian_phone: str | None
    errors: list[str]
    valid: bool


class ImportResultResponse(BaseModel):
    dry_run: bool
    total_rows: int
    valid_rows: int
    imported: int
    rows: list[ImportPreviewRow]
