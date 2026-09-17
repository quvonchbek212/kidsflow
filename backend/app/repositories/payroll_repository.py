"""Payroll (oylik hisoblash) uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PayrollStatus
from app.models.payroll import PayrollRun, SalaryAdvance


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


class SalaryAdvanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, advance: SalaryAdvance) -> None:
        self._session.add(advance)

    async def get_by_id(self, advance_id: uuid.UUID) -> SalaryAdvance | None:
        return await self._session.get(SalaryAdvance, advance_id)

    async def total_for_user_period(self, user_id: uuid.UUID, period: date) -> Decimal:
        """Shu oy uchun berilgan (bekor qilinmagan) avanslar yig'indisi."""
        stmt = select(func.coalesce(func.sum(SalaryAdvance.amount), 0)).where(
            SalaryAdvance.user_id == user_id,
            SalaryAdvance.period == period,
            SalaryAdvance.status == PayrollStatus.RECORDED.value,
        )
        return Decimal((await self._session.execute(stmt)).scalar_one())

    async def list_for_user(self, user_id: uuid.UUID) -> list[SalaryAdvance]:
        stmt = (
            select(SalaryAdvance)
            .where(SalaryAdvance.user_id == user_id)
            .order_by(SalaryAdvance.paid_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_branch(
        self, branch_id: uuid.UUID, period: date | None = None
    ) -> list[SalaryAdvance]:
        conditions = [SalaryAdvance.branch_id == branch_id]
        if period is not None:
            conditions.append(SalaryAdvance.period == period)
        stmt = (
            select(SalaryAdvance)
            .where(*conditions)
            .order_by(SalaryAdvance.paid_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())
