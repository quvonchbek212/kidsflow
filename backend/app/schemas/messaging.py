"""Ommaviy xabar yuborish sxemalari (7-bosqich B)."""

from __future__ import annotations

import uuid
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
