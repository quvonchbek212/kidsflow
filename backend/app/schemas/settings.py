"""Bog'cha sozlamalari sxemalari (7-bosqich B).

Payme/Click/2FA uchun ATAYLAB hech qanday maydon yo'q — loyiha qarori.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class KindergartenSettingsResponse(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None
    address: str | None
    phone: str | None
    timezone: str
    default_language: str
    currency: str
    hours_text: str | None
    auto_invoice_day: int | None
    notification_toggles: dict[str, bool]


class SettingsUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    hours_text: str | None = Field(default=None, max_length=255)
    auto_invoice_day: int | None = Field(default=None, ge=1, le=28)
    # Faqat berilgan kalitlar yangilanadi (qisman merge) — masalan
    # {"CHILD_SICK": false} boshqa turlarga tegmaydi.
    notification_toggles: dict[str, bool] | None = None
