"""Moliyaviy DB so'rovlari: tarif, invoice, to'lov, tuzatma, xarajat, analitika."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.enums import (
    EnrollmentStatus,
    ExpenseStatus,
    InvoiceStatus,
    PaymentStatus,
)
from app.models.finance import (
    Expense,
    ExpenseCategory,
    Invoice,
    InvoiceAdjustment,
    PaymentAllocation,
    PaymentTransaction,
)
from app.utils.money import ZERO, money

# Qarzdorlik holatlari (hali to'liq to'lanmagan).
OUTSTANDING_STATUSES = (
    InvoiceStatus.OPEN.value,
    InvoiceStatus.PARTIALLY_PAID.value,
    InvoiceStatus.OVERDUE.value,
)
# Real pul sifatida hisoblanadigan to'lov holatlari.
CASH_STATUSES = (PaymentStatus.RECORDED.value, PaymentStatus.CONFIRMED.value)


def _to_money(value: object) -> Decimal:
    if value is None:
        return ZERO
    return money(Decimal(str(value)))


class InvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, invoice: Invoice) -> None:
        self._session.add(invoice)

    async def get_by_id(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self._session.get(Invoice, invoice_id)

    async def child_ids_billed_for(
        self, child_ids: Sequence[uuid.UUID], billing_period: date
    ) -> set[uuid.UUID]:
        """Shu oy uchun (har qanday holatda) hisobi bor bolalar."""
        if not child_ids:
            return set()
        stmt = select(Invoice.child_id).where(
            Invoice.child_id.in_(child_ids),
            Invoice.billing_period == billing_period,
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def get_for_child_period(
        self, child_id: uuid.UUID, billing_period: date
    ) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(
                Invoice.child_id == child_id,
                Invoice.billing_period == billing_period,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_outstanding_for_child(self, child_id: uuid.UUID) -> list[Invoice]:
        """Bolaning to'lanmagan invoice'lari, eng eski (due_date) birinchi."""
        stmt = (
            select(Invoice)
            .where(
                Invoice.child_id == child_id,
                Invoice.status.in_(OUTSTANDING_STATUSES),
            )
            .order_by(Invoice.due_date, Invoice.billing_period)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_outstanding_for_branch(self, branch_id: uuid.UUID) -> list[Invoice]:
        """Filialning barcha (davrga bog'liq bo'lmagan) to'lanmagan invoice'lari.

        Xabar yuborish schedulerida (to'lov eslatmasi / qarz ogohlantirish)
        ishlatiladi (7-bosqich B).
        """
        stmt = (
            select(Invoice)
            .where(
                Invoice.branch_id == branch_id,
                Invoice.status.in_(OUTSTANDING_STATUSES),
            )
            .order_by(Invoice.due_date)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_for_child(self, child_id: uuid.UUID) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.child_id == child_id)
            .order_by(Invoice.billing_period.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_branch_period(
        self, branch_id: uuid.UUID, billing_period: date
    ) -> list[Invoice]:
        """Filialning bir oy uchun barcha invoice'lari (Oylik to'lovlar bo'limi)."""
        stmt = (
            select(Invoice)
            .where(
                Invoice.branch_id == branch_id,
                Invoice.billing_period == billing_period,
            )
            .order_by(Invoice.due_date)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def adjustments_for(self, invoice_id: uuid.UUID) -> list[tuple[str, Decimal]]:
        stmt = select(
            InvoiceAdjustment.adjustment_type, InvoiceAdjustment.amount
        ).where(InvoiceAdjustment.invoice_id == invoice_id)
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], _to_money(row[1])) for row in rows]

    async def paid_for(self, invoice_id: uuid.UUID) -> Decimal:
        """Bekor qilinmagan to'lovlardan invoice'ga taqsimlangan summa."""
        stmt = (
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .join(
                PaymentTransaction,
                PaymentTransaction.id == PaymentAllocation.payment_transaction_id,
            )
            .where(
                PaymentAllocation.invoice_id == invoice_id,
                PaymentTransaction.status != PaymentStatus.REVERSED.value,
            )
        )
        return _to_money((await self._session.execute(stmt)).scalar_one())

    def add_adjustment(self, adjustment: InvoiceAdjustment) -> None:
        self._session.add(adjustment)


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, payment: PaymentTransaction) -> None:
        self._session.add(payment)

    def add_allocation(self, allocation: PaymentAllocation) -> None:
        self._session.add(allocation)

    async def get_by_id(self, payment_id: uuid.UUID) -> PaymentTransaction | None:
        return await self._session.get(PaymentTransaction, payment_id)

    async def get_by_idempotency_key(self, key: str) -> PaymentTransaction | None:
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.idempotency_key == key)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_child(
        self, child_id: uuid.UUID, limit: int = 20
    ) -> list[PaymentTransaction]:
        stmt = (
            select(PaymentTransaction)
            .where(PaymentTransaction.child_id == child_id)
            .order_by(PaymentTransaction.paid_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def allocations_for(self, payment_id: uuid.UUID) -> list[PaymentAllocation]:
        stmt = select(PaymentAllocation).where(
            PaymentAllocation.payment_transaction_id == payment_id
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def unallocated_for_child(
        self, child_id: uuid.UUID
    ) -> list[tuple[PaymentTransaction, Decimal]]:
        """Bolaning hali hech bir hisobga to'liq yozilmagan to'lovlari.

        Masalan, ota-ona oy uchun hisob yaratilishidan oldin pul olib kelgan.
        Har bir to'lov va uning bo'sh qoldig'i, eng eskisi birinchi. Bitta
        so'rovda — har to'lov uchun taqsimotni alohida so'ramaslik uchun.
        """
        allocated = func.coalesce(func.sum(PaymentAllocation.amount), 0)
        stmt = (
            select(PaymentTransaction, allocated)
            .outerjoin(
                PaymentAllocation,
                PaymentAllocation.payment_transaction_id == PaymentTransaction.id,
            )
            .where(
                PaymentTransaction.child_id == child_id,
                PaymentTransaction.status.in_(CASH_STATUSES),
            )
            .group_by(PaymentTransaction.id)
            .order_by(PaymentTransaction.paid_at, PaymentTransaction.created_at)
        )
        result: list[tuple[PaymentTransaction, Decimal]] = []
        for payment, allocated_sum in (await self._session.execute(stmt)).all():
            free = _to_money(payment.amount) - _to_money(allocated_sum)
            if free > ZERO:
                result.append((payment, free))
        return result


class ExpenseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, expense: Expense) -> None:
        self._session.add(expense)

    def add_category(self, category: ExpenseCategory) -> None:
        self._session.add(category)

    async def get_by_id(self, expense_id: uuid.UUID) -> Expense | None:
        return await self._session.get(Expense, expense_id)

    async def get_category(self, category_id: uuid.UUID) -> ExpenseCategory | None:
        return await self._session.get(ExpenseCategory, category_id)

    async def list_categories(self) -> list[ExpenseCategory]:
        stmt = select(ExpenseCategory).order_by(ExpenseCategory.name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def category_name_exists(self, name: str) -> bool:
        stmt = select(ExpenseCategory.id).where(ExpenseCategory.name == name).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def list_by_branch(
        self,
        branch_id: uuid.UUID,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[Expense]:
        """Filial xarajatlari, ixtiyoriy davr bo'yicha (Xarajatlar bo'limi)."""
        conditions = [Expense.branch_id == branch_id]
        if period_start is not None:
            conditions.append(Expense.expense_date >= period_start)
        if period_end is not None:
            conditions.append(Expense.expense_date <= period_end)
        stmt = select(Expense).where(*conditions).order_by(Expense.expense_date.desc())
        return list((await self._session.execute(stmt)).scalars().all())


class AnalyticsRepository:
    """Dashboard uchun agregat so'rovlar (4.7-bo'lim)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def accrual_revenue_by_branch(
        self,
        branch_ids: Sequence[uuid.UUID],
        period_start: date,
        period_end: date,
    ) -> dict[uuid.UUID, Decimal]:
        stmt = (
            select(
                Invoice.branch_id, func.coalesce(func.sum(Invoice.adjusted_amount), 0)
            )
            .where(
                Invoice.branch_id.in_(branch_ids),
                Invoice.billing_period >= period_start,
                Invoice.billing_period <= period_end,
                Invoice.status != InvoiceStatus.CANCELLED.value,
            )
            .group_by(Invoice.branch_id)
        )
        return {
            r[0]: _to_money(r[1]) for r in (await self._session.execute(stmt)).all()
        }

    async def cash_collected_by_branch(
        self,
        branch_ids: Sequence[uuid.UUID],
        period_start: date,
        period_end: date,
    ) -> dict[uuid.UUID, Decimal]:
        stmt = (
            select(
                PaymentTransaction.branch_id,
                func.coalesce(func.sum(PaymentTransaction.amount), 0),
            )
            .where(
                PaymentTransaction.branch_id.in_(branch_ids),
                PaymentTransaction.status.in_(CASH_STATUSES),
                func.date(PaymentTransaction.paid_at) >= period_start,
                func.date(PaymentTransaction.paid_at) <= period_end,
            )
            .group_by(PaymentTransaction.branch_id)
        )
        return {
            r[0]: _to_money(r[1]) for r in (await self._session.execute(stmt)).all()
        }

    async def outstanding_by_branch(
        self, branch_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        stmt = (
            select(
                Invoice.branch_id,
                func.coalesce(func.sum(Invoice.outstanding_amount), 0),
            )
            .where(
                Invoice.branch_id.in_(branch_ids),
                Invoice.status.in_(OUTSTANDING_STATUSES),
            )
            .group_by(Invoice.branch_id)
        )
        return {
            r[0]: _to_money(r[1]) for r in (await self._session.execute(stmt)).all()
        }

    async def expenses_by_branch(
        self,
        branch_ids: Sequence[uuid.UUID],
        period_start: date,
        period_end: date,
    ) -> dict[uuid.UUID, Decimal]:
        stmt = (
            select(Expense.branch_id, func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.branch_id.in_(branch_ids),
                Expense.status == ExpenseStatus.RECORDED.value,
                Expense.expense_date >= period_start,
                Expense.expense_date <= period_end,
            )
            .group_by(Expense.branch_id)
        )
        return {
            r[0]: _to_money(r[1]) for r in (await self._session.execute(stmt)).all()
        }

    async def debt_aging(
        self, branch_ids: Sequence[uuid.UUID], as_of: date
    ) -> list[tuple[str, Decimal]]:
        """Qarzdorlikni to'lov muddatiga nisbatan 4 ta bucket'ga ajratadi.

        Kunlar farqi Python tomonda hisoblanadi (SQLite/PostgreSQL orasida
        sana arifmetikasi farqli bo'lgani uchun — dialektga bog'liq bo'lmaslik
        uchun qatorlar o'qib olinadi, keyin guruhlanadi).
        """
        stmt = select(Invoice.due_date, Invoice.outstanding_amount).where(
            Invoice.branch_id.in_(branch_ids),
            Invoice.status.in_(OUTSTANDING_STATUSES),
        )
        rows = (await self._session.execute(stmt)).all()

        buckets = {
            "not_due": ZERO,
            "aging_1_30": ZERO,
            "aging_31_60": ZERO,
            "aging_60_plus": ZERO,
        }
        for due_date, outstanding in rows:
            days_late = (as_of - due_date).days
            amount = _to_money(outstanding)
            if days_late <= 0:
                buckets["not_due"] += amount
            elif days_late <= 30:
                buckets["aging_1_30"] += amount
            elif days_late <= 60:
                buckets["aging_31_60"] += amount
            else:
                buckets["aging_60_plus"] += amount
        return [(label, money(total)) for label, total in buckets.items()]

    async def revenue_by_group(
        self,
        branch_ids: Sequence[uuid.UUID],
        period_start: date,
        period_end: date,
    ) -> dict[uuid.UUID, Decimal]:
        """Guruh bo'yicha accrual daromad (Invoice → Enrollment orqali)."""
        stmt = (
            select(
                Enrollment.group_id,
                func.coalesce(func.sum(Invoice.adjusted_amount), 0),
            )
            .join(Enrollment, Enrollment.id == Invoice.enrollment_id)
            .where(
                Invoice.branch_id.in_(branch_ids),
                Invoice.billing_period >= period_start,
                Invoice.billing_period <= period_end,
                Invoice.status != InvoiceStatus.CANCELLED.value,
            )
            .group_by(Enrollment.group_id)
        )
        return {
            r[0]: _to_money(r[1]) for r in (await self._session.execute(stmt)).all()
        }

    async def expenses_by_category(
        self,
        branch_ids: Sequence[uuid.UUID],
        period_start: date,
        period_end: date,
    ) -> list[tuple[uuid.UUID, str, bool, Decimal]]:
        """Kategoriya bo'yicha xarajat yig'indisi (donut/break-even uchun)."""
        stmt = (
            select(
                ExpenseCategory.id,
                ExpenseCategory.name,
                ExpenseCategory.is_variable,
                func.coalesce(func.sum(Expense.amount), 0),
            )
            .join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
            .where(
                Expense.branch_id.in_(branch_ids),
                Expense.status == ExpenseStatus.RECORDED.value,
                Expense.expense_date >= period_start,
                Expense.expense_date <= period_end,
            )
            .group_by(
                ExpenseCategory.id, ExpenseCategory.name, ExpenseCategory.is_variable
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [(r[0], r[1], r[2], _to_money(r[3])) for r in rows]

    async def active_children_count(self, branch_ids: Sequence[uuid.UUID]) -> int:
        """Berilgan filiallardagi faol enrollmentga ega bolalar soni (distinct)."""
        stmt = select(func.count(func.distinct(Enrollment.child_id))).where(
            Enrollment.branch_id.in_(branch_ids),
            Enrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        return int((await self._session.execute(stmt)).scalar_one())
