"""Moliyaviy ko'rsatkichlarni oddiy tilda sharhlash (10.3-bo'lim).

AI SQL orqali hisoblangan tayyor raqamlarni tushuntiradi. Yangi raqam yoki sabab
o'ylab topmaydi.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.models.enums import AIFeature
from app.services.ai.engine import AIEngine
from app.services.ai.provider import AIProvider
from app.services.analytics_service import AnalyticsService

_SYSTEM = (
    "Sen moliyaviy tahlilchi yordamchisisan. Faqat berilgan raqamlarni oddiy "
    "o'zbek tilida tushuntir. Yangi raqam yoki xarajat sababini o'ylab topma. "
    "Ma'lumot bo'lmasa, taxmin qilma. Qisqa, 3-5 jumla yoz."
)


class FinanceNarratorService:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._analytics = AnalyticsService(session)
        self._engine = AIEngine(session, provider)

    async def narrate(
        self,
        current_user: CurrentUser,
        period_start: date,
        period_end: date,
    ) -> str:
        # Raqamlar SQL orqali hisoblanadi — AI ularni faqat sharhlaydi.
        dashboard = await self._analytics.dashboard(
            current_user, period_start, period_end
        )
        facts = (
            f"Davr: {period_start} — {period_end}\n"
            f"- Hisoblangan daromad (accrual): {dashboard.accrual_revenue} so'm\n"
            f"- Real tushgan pul (cash): {dashboard.cash_collected} so'm\n"
            f"- Qarzdorlik: {dashboard.outstanding} so'm\n"
            f"- Xarajatlar: {dashboard.expenses} so'm\n"
            f"- Sof naqd natija: {dashboard.net_cash} so'm"
        )
        return await self._engine.run_text(
            AIFeature.FINANCE_NARRATIVE.value,
            _SYSTEM,
            "Quyidagi moliyaviy ko'rsatkichlarni tushuntir:\n" + facts,
            current_user.id,
        )
