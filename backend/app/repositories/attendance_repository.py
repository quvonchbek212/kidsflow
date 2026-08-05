"""Davomat uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus


class AttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, attendance: Attendance) -> None:
        self._session.add(attendance)

    async def get_for_child_date(
        self, child_id: uuid.UUID, attendance_date: date
    ) -> Attendance | None:
        stmt = (
            select(Attendance)
            .where(
                Attendance.child_id == child_id,
                Attendance.attendance_date == attendance_date,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_child(
        self, child_id: uuid.UUID, limit: int = 100
    ) -> list[Attendance]:
        stmt = (
            select(Attendance)
            .where(Attendance.child_id == child_id)
            .order_by(Attendance.attendance_date.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def map_for_children_date(
        self, child_ids: Sequence[uuid.UUID], attendance_date: date
    ) -> dict[uuid.UUID, Attendance]:
        """Bola ID → davomat yozuvi (guruh rosteri uchun, 4.3-bo'lim)."""
        if not child_ids:
            return {}
        stmt = select(Attendance).where(
            Attendance.child_id.in_(child_ids),
            Attendance.attendance_date == attendance_date,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {a.child_id: a for a in rows}

    async def counts_by_date(
        self,
        child_ids: Sequence[uuid.UUID],
        start_date: date,
        end_date: date,
    ) -> dict[date, int]:
        """Har bir kun uchun "keldi" (PRESENT/LATE) deb belgilangan bolalar soni.

        Trend grafikasi uchun (4.3-bo'lim kengaytmasi).
        """
        if not child_ids:
            return {}
        stmt = (
            select(Attendance.attendance_date, func.count())
            .where(
                Attendance.child_id.in_(child_ids),
                Attendance.attendance_date >= start_date,
                Attendance.attendance_date <= end_date,
                Attendance.status.in_(
                    (AttendanceStatus.PRESENT.value, AttendanceStatus.LATE.value)
                ),
            )
            .group_by(Attendance.attendance_date)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}
