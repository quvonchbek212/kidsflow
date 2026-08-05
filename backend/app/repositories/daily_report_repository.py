"""Kunlik hisobotlar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_report import DailyReport, DailyReportFile


class DailyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, report: DailyReport) -> None:
        self._session.add(report)

    def add_file_link(self, link: DailyReportFile) -> None:
        self._session.add(link)

    async def get_by_id(self, report_id: uuid.UUID) -> DailyReport | None:
        return await self._session.get(DailyReport, report_id)

    async def get_loaded(self, report_id: uuid.UUID) -> DailyReport | None:
        stmt = (
            select(DailyReport)
            .where(DailyReport.id == report_id)
            .options(selectinload(DailyReport.files))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_for_child_date(
        self, child_id: uuid.UUID, report_date: date
    ) -> DailyReport | None:
        stmt = (
            select(DailyReport)
            .where(
                DailyReport.child_id == child_id,
                DailyReport.report_date == report_date,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_children_date(
        self, child_ids: Sequence[uuid.UUID], report_date: date
    ) -> list[DailyReport]:
        """Bir guruh bolalarining shu sanadagi hisobotlari (roster uchun).

        Har bir bola uchun alohida so'rov o'rniga bitta so'rov — guruhda 20 bola
        bo'lsa ham bitta murojaat yetadi.
        """
        if not child_ids:
            return []
        stmt = (
            select(DailyReport)
            .where(
                DailyReport.child_id.in_(child_ids),
                DailyReport.report_date == report_date,
            )
            .options(selectinload(DailyReport.files))
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_child(
        self, child_id: uuid.UUID, limit: int = 100
    ) -> list[DailyReport]:
        stmt = (
            select(DailyReport)
            .where(DailyReport.child_id == child_id)
            .order_by(DailyReport.report_date.desc())
            .options(selectinload(DailyReport.files))
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def clear_file_links(self, report_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(DailyReportFile).where(DailyReportFile.daily_report_id == report_id)
        )

    async def child_ids_for_file(self, file_id: uuid.UUID) -> list[uuid.UUID]:
        """Shu faylga bog'langan hisobotlarning bola ID'lari (fayl kirish nazorati)."""
        stmt = (
            select(DailyReport.child_id)
            .join(
                DailyReportFile,
                DailyReportFile.daily_report_id == DailyReport.id,
            )
            .where(DailyReportFile.file_id == file_id)
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())
