"""Payroll (oylik hisoblash) uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PayrollStatus
from app.models.payroll import PayrollRun


class PayrollRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, run: PayrollRun) -> None:
        self._session.add(run)

    async def get_by_id(self, run_id: uuid.UUID) -> PayrollRun | None:
        return await self._session.get(PayrollRun, run_id)

    async def get_active_for_user_period(
        self, user_id: uuid.UUID, period: date
    ) -> PayrollRun | None:
        stmt = (
            select(PayrollRun)
            .where(
                PayrollRun.user_id == user_id,
                PayrollRun.period == period,
                PayrollRun.status == PayrollStatus.RECORDED.value,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[PayrollRun]:
        stmt = (
            select(PayrollRun)
            .where(PayrollRun.user_id == user_id)
            .order_by(PayrollRun.period.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_branch(
        self, branch_id: uuid.UUID, period: date | None = None
    ) -> list[PayrollRun]:
        conditions = [PayrollRun.branch_id == branch_id]
        if period is not None:
            conditions.append(PayrollRun.period == period)
        stmt = select(PayrollRun).where(*conditions).order_by(PayrollRun.period.desc())
        return list((await self._session.execute(stmt)).scalars().all())
