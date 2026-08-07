"""Moliyaviy dashboard — SQL agregatlari orqali (4.7-bo'lim).

Ikki tushuncha aniq ajratiladi:
- accrual_revenue — invoice orqali hisoblangan summa;
- cash_collected — real kelib tushgan pul.

AI hisob-kitob qilmaydi; barcha raqamlar shu SQL formulalari orqali (4.7-bo'lim).
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import Role
from app.repositories.branch_repository import BranchRepository
from app.repositories.finance_repository import AnalyticsRepository
from app.schemas.finance import (
    BranchFinanceSummary,
    BreakEvenSummary,
    CategoryExpenseRow,
    DebtAgingBucket,
    FinanceDashboardResponse,
    GroupRevenueRow,
)
from app.utils.money import ZERO, money


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._analytics = AnalyticsRepository(session)
        self._branches = BranchRepository(session)

    async def dashboard(
        self,
        current_user: CurrentUser,
        period_start: date,
        period_end: date,
        branch_id: uuid.UUID | None = None,
    ) -> FinanceDashboardResponse:
        branch_ids = await self._visible_branch_ids(current_user)
        # Filial ko'rsatilsa hisob faqat shu filial bo'yicha yig'iladi. Aks holda
        # ko'p filialli bog'chada barcha raqamlar jimgina qo'shilib ketardi.
        if branch_id is not None:
            if branch_id not in branch_ids:
                raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")
            branch_ids = [branch_id]

        if not branch_ids:
            return FinanceDashboardResponse(
                period_start=period_start,
                period_end=period_end,
                accrual_revenue=ZERO,
                cash_collected=ZERO,
                outstanding=ZERO,
                expenses=ZERO,
                net_cash=ZERO,
                branches=[],
                aging=[],
                revenue_by_group=[],
                expenses_by_category=[],
                break_even=None,
            )

        accrual = await self._analytics.accrual_revenue_by_branch(
            branch_ids, period_start, period_end
        )
        cash = await self._analytics.cash_collected_by_branch(
            branch_ids, period_start, period_end
        )
        outstanding = await self._analytics.outstanding_by_branch(branch_ids)
        expenses = await self._analytics.expenses_by_branch(
            branch_ids, period_start, period_end
        )

        branch_summaries: list[BranchFinanceSummary] = []
        for branch_id in branch_ids:
            b_cash = cash.get(branch_id, ZERO)
            b_exp = expenses.get(branch_id, ZERO)
            branch_summaries.append(
                BranchFinanceSummary(
                    branch_id=branch_id,
                    accrual_revenue=accrual.get(branch_id, ZERO),
                    cash_collected=b_cash,
                    outstanding=outstanding.get(branch_id, ZERO),
                    expenses=b_exp,
                    net_cash=money(b_cash - b_exp),
                )
            )

        total_cash = money(sum((s.cash_collected for s in branch_summaries), ZERO))
        total_exp = money(sum((s.expenses for s in branch_summaries), ZERO))
        total_accrual = money(sum((s.accrual_revenue for s in branch_summaries), ZERO))

        aging_rows = await self._analytics.debt_aging(branch_ids, date.today())
        aging = [
            DebtAgingBucket(label=label, total=total) for label, total in aging_rows
        ]

        revenue_by_group = await self._analytics.revenue_by_group(
            branch_ids, period_start, period_end
        )
        revenue_rows = [
            GroupRevenueRow(group_id=group_id, total=total)
            for group_id, total in revenue_by_group.items()
        ]

        category_rows = await self._analytics.expenses_by_category(
            branch_ids, period_start, period_end
        )
        expenses_by_category = [
            CategoryExpenseRow(
                category_id=cid, category_name=name, is_variable=is_var, total=total
            )
            for cid, name, is_var, total in category_rows
        ]

        active_children = await self._analytics.active_children_count(branch_ids)
        break_even = self._compute_break_even(
            active_children, total_accrual, category_rows
        )

        return FinanceDashboardResponse(
            period_start=period_start,
            period_end=period_end,
            accrual_revenue=total_accrual,
            cash_collected=total_cash,
            outstanding=money(sum((s.outstanding for s in branch_summaries), ZERO)),
            expenses=total_exp,
            net_cash=money(total_cash - total_exp),
            branches=branch_summaries,
            aging=aging,
            revenue_by_group=revenue_rows,
            expenses_by_category=expenses_by_category,
            break_even=break_even,
        )

    @staticmethod
    def _compute_break_even(
        active_children: int,
        accrual_revenue: Decimal,
        category_rows: list[tuple[uuid.UUID, str, bool, Decimal]],
    ) -> BreakEvenSummary | None:
        """Mockup'ning `beModel()` formulasi bilan bir xil hisob-kitob (server tomonda).

        Faol bola bo'lmasa yoki marjinal daromad musbat bo'lmasa hisoblab
        bo'lmaydi — bunda None qaytariladi (frontend blokni yashiradi).
        """
        if active_children <= 0 or accrual_revenue <= ZERO:
            return None

        fixed_costs = money(sum((row[3] for row in category_rows if not row[2]), ZERO))
        variable_costs = money(sum((row[3] for row in category_rows if row[2]), ZERO))

        fee_per_child = money(accrual_revenue / active_children)
        variable_per_child = money(variable_costs / active_children)
        contribution_margin = money(fee_per_child - variable_per_child)
        if contribution_margin <= ZERO:
            return None

        contribution_ratio = contribution_margin / fee_per_child
        breakeven_revenue = money(fixed_costs / contribution_ratio)
        breakeven_children = math.ceil(fixed_costs / contribution_margin)

        return BreakEvenSummary(
            active_children=active_children,
            fixed_costs=fixed_costs,
            variable_costs=variable_costs,
            fee_per_child=fee_per_child,
            variable_cost_per_child=variable_per_child,
            contribution_margin=contribution_margin,
            contribution_margin_ratio=contribution_ratio,
            breakeven_revenue=breakeven_revenue,
            breakeven_children=breakeven_children,
        )

    async def _visible_branch_ids(self, current_user: CurrentUser) -> list[uuid.UUID]:
        if current_user.is_owner:
            return [b.id for b in await self._branches.list_all()]
        return list(current_user.branches_for(Role.MANAGER))
