"""Davomat sxemalari."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AttendanceStatus


class AttendanceMarkRequest(BaseModel):
    child_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check_times(self) -> AttendanceMarkRequest:
        if (
            self.check_in_at is not None
            and self.check_out_at is not None
            and self.check_out_at < self.check_in_at
        ):
            raise ValueError("Ketgan vaqt kelgan vaqtdan oldin bo'lmasligi kerak.")
        return self


class AttendanceResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID
    child_id: uuid.UUID
    attendance_date: date
    status: str
    check_in_at: datetime | None
    check_out_at: datetime | None
    note: str | None
    marked_by: uuid.UUID | None


class AttendanceRosterRow(BaseModel):
    """Guruh rosteridagi bir bola — davomat belgilanmagan bo'lsa status None."""

    child_id: uuid.UUID
    child_name: str
    status: str | None
    check_in_at: datetime | None
    check_out_at: datetime | None


class AttendanceBulkEntry(BaseModel):
    child_id: uuid.UUID
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=1000)


class AttendanceBulkMarkRequest(BaseModel):
    """Bir guruh, bir kun uchun bir nechta bolani birdaniga belgilash."""

    group_id: uuid.UUID
    attendance_date: date
    entries: list[AttendanceBulkEntry] = Field(min_length=1)


class AttendanceTrendPoint(BaseModel):
    attendance_date: date
    present_count: int
    total_count: int


class AttendanceTrendResponse(BaseModel):
    group_id: uuid.UUID
    points: list[AttendanceTrendPoint]
