"""Oylik hisob-fakturalarni avtomatik yaratish.

Ilgari menejer har oy "Hisob-faktura yaratish" tugmasini bosishi kerak edi.
Unutilsa qarz ko'rinmas, Telegram eslatmalari ketmas va olingan to'lov hech
qaysi hisobga yozilmay qolardi. Endi worker buni o'zi qiladi.

Ish kuniga bir marta (`daily_job_runs` orqali) joriy oy uchun har filialdagi
faol bolalarga hisob yaratiladi. Har kuni ishlagani (faqat 1-sanada emas)
ataylab: yaratish idempotent, shuning uchun server 1-sanada o'chiq bo'lsa
ham keyingi ishga tushishda oy to'ldiriladi.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.branch_repository import BranchRepository
from app.repositories.messaging_repository import (
    BranchNotificationSettingsRepository,
    DailyJobRepository,
)
from app.services.billing_service import DEFAULT_INVOICE_DUE_DAY, BillingService
from app.utils.timezone import today_local

logger = logging.getLogger(__name__)

_JOB_NAME = "monthly_invoices"


async def run_daily(session: AsyncSession, today: date | None = None) -> int:
    """Joriy oy hisob-fakturalarini yaratadi (kuniga bir marta).

    Qaytaradi: yaratilgan hisob-fakturalar soni. Bugun allaqachon bajarilgan
    bo'lsa hech narsa qilmaydi va 0 qaytaradi.
    """
    today = today or today_local()
    jobs = DailyJobRepository(session)
    if not await jobs.try_claim(_JOB_NAME, today):
        return 0

    branch_list = await BranchRepository(session).list_all()
    settings_by_branch = await BranchNotificationSettingsRepository(
        session
    ).list_by_branches([branch.id for branch in branch_list])

    billing = BillingService(session)
    period = today.replace(day=1)
    total = 0
    for branch in branch_list:
        config = settings_by_branch.get(branch.id)
        due_day = config.invoice_due_day if config else DEFAULT_INVOICE_DUE_DAY
        created, _ = await billing.generate_for_branch(
            branch.id, period, due_day, not_before=today
        )
        total += created

    if total:
        logger.info(
            "Oylik hisob-fakturalar avtomatik yaratildi",
            extra={"created": total, "period": period.isoformat()},
        )
    return total
