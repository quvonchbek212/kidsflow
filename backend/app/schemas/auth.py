"""Autentifikatsiya sxemalari (login, refresh, logout, me)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.phone import normalize_phone


class LoginRequest(BaseModel):
    # Login (username asosiy; telefon/email ham qo'llab-quvvatlanadi).
    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    # Hisobga bog'langan email (tiklash havolasi shu manzilga yuboriladi).
    email: str = Field(min_length=1, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token amal qilish muddati (soniya)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RoleGrantOut(BaseModel):
    role: str
    branch_id: uuid.UUID | None


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    username: str | None
    phone: str | None
    email: str | None
    preferred_language: str
    roles: list[RoleGrantOut]


class ProfileUpdateRequest(BaseModel):
    """Foydalanuvchi o'z profilini tahrirlashi (har qanday rol).

    Ataylab faqat shu uch maydon: rol, email, maosh va faollik holati o'zini
    o'zi o'zgartira olmaydi — ular OWNER huquqida qoladi.
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    preferred_language: Literal["uz", "ru", "en"] | None = None

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)
