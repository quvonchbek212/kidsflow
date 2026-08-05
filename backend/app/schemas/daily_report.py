"""Kunlik hisobot sxemalari (4.4-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import MealStatus, Mood


class DailyReportCreateRequest(BaseModel):
    child_id: uuid.UUID
    report_date: date
    meal_status: MealStatus | None = None
    nap_minutes: int | None = Field(default=None, ge=0, le=1440)
    mood: Mood | None = None
    activities_text: str | None = Field(default=None, max_length=4000)
    teacher_note: str | None = Field(default=None, max_length=2000)
    final_summary: str | None = Field(default=None, max_length=4000)
    file_ids: list[uuid.UUID] = Field(default_factory=list)


class DailyReportUpdateRequest(BaseModel):
    meal_status: MealStatus | None = None
    nap_minutes: int | None = Field(default=None, ge=0, le=1440)
    mood: Mood | None = None
    activities_text: str | None = Field(default=None, max_length=4000)
    teacher_note: str | None = Field(default=None, max_length=2000)
    final_summary: str | None = Field(default=None, max_length=4000)
    file_ids: list[uuid.UUID] | None = None


class DailyReportFileSummary(BaseModel):
    file_id: uuid.UUID
    original_name: str
    content_type: str


class DailyReportResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    child_id: uuid.UUID
    report_date: date
    meal_status: str | None
    nap_minutes: int | None
    mood: str | None
    activities_text: str | None
    teacher_note: str | None
    final_summary: str | None
    is_published: bool
    published_at: datetime | None
    files: list[DailyReportFileSummary]


class DailyReportRosterRow(BaseModel):
    """Guruhdagi bola va uning shu kundagi hisoboti (hali yozilmagan bo'lsa None)."""

    child_id: uuid.UUID
    child_name: str
    report: DailyReportResponse | None
