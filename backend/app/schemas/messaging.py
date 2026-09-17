"""Xabar yuborish sxemalari: ommaviy xabar, filial sozlamalari
va ota-ona ↔ xodim yozishmalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BroadcastCreateRequest(BaseModel):
    branch_id: uuid.UUID
    audience: Literal["all", "group", "debtors"]
    # Faqat audience="group" bo'lganda talab qilinadi.
    group_id: uuid.UUID | None = None
    text: str = Field(min_length=1, max_length=2000)


class BroadcastResultResponse(BaseModel):
    queued_count: int


class MessagingStatsResponse(BaseModel):
    connected_families: int
    sent_this_month: int


# --- Filial kesimidagi bildirishnoma sozlamalari ---


class BranchNotificationSettingsResponse(BaseModel):
    branch_id: uuid.UUID
    toggles: dict[str, bool]
    payment_reminder_days_before: int
    debt_warning_days_late: int
    invoice_due_day: int


class BranchNotificationSettingsUpdateRequest(BaseModel):
    """Faqat berilgan maydonlar yangilanadi.

    `toggles` — qisman yangilanadi (mavjud kalitlar ustiga yoziladi), shunda
    frontend bitta kalitni almashtirish uchun butun to'plamni yubormaydi.
    """

    toggles: dict[str, bool] | None = None
    payment_reminder_days_before: int | None = Field(default=None, ge=0, le=60)
    debt_warning_days_late: int | None = Field(default=None, ge=1, le=180)
    # 28 dan katta bo'lsa fevralda sana mavjud bo'lmay qolardi.
    invoice_due_day: int | None = Field(default=None, ge=1, le=28)


# --- Ota-ona ↔ xodim yozishmalari ---


class ParentMessageResponse(BaseModel):
    id: uuid.UUID
    direction: Literal["IN", "OUT"]
    text: str
    created_at: datetime
    read_at: datetime | None
    staff_name: str | None


class MessageThreadSummary(BaseModel):
    guardian_user_id: uuid.UUID
    guardian_name: str
    guardian_phone: str | None
    children: list[str]
    last_message_at: datetime
    last_message_text: str
    unread_count: int


class ParentMessageCreateRequest(BaseModel):
    """Ota-ona botdan yuboradigan savol (ota-ona tokeni bilan)."""

    text: str = Field(min_length=1, max_length=2000)


class StaffReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class UnreadCountResponse(BaseModel):
    unread_count: int
