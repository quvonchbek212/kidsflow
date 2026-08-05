"""Dastlabki sozlash (/setup) sxemalari (4.1-bo'lim)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.phone import normalize_phone
from app.utils.validators import normalize_email, normalize_username


class SetupKindergarten(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)


class SetupBranch(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    capacity: int | None = Field(default=None, gt=0)

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)


class SetupOwner(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    # Login uchun ishlatiladigan ism/taxallus (masalan "Quvonchbek").
    username: str = Field(min_length=3, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)

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


class SetupRequest(BaseModel):
    kindergarten: SetupKindergarten
    branch: SetupBranch
    owner: SetupOwner
    timezone: str = "Asia/Tashkent"
    default_language: Literal["uz", "ru", "en"] = "uz"
    currency: str = "UZS"


class SetupResponse(BaseModel):
    settings_id: uuid.UUID
    branch_id: uuid.UUID
    owner_id: uuid.UUID
