"""Kunlik avtomatik bildirishnoma ishlari (7-bosqich B: xabar yuborish).

Alohida scheduling kutubxonasi (masalan APScheduler) ishlatilmaydi — worker
allaqachon har necha soniyada bir siklda ishlaydi (`app/workers/main.py`);
shu yerda faqat "bugun allaqachon bajarilganmi" tekshiruvi
(`DailyJobRepository.try_claim`) orqali har bir ish kuniga bir marta ishga
tushirilishi ta'minlanadi. Har bir ish faqat OutboxEvent navbatga qo'yadi —
haqiqiy bildirishnoma yaratish/yuborish `OutboxProcessor`da (mavjud, ishonchli
retry mexanizmi bilan).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.messaging import OutboxEvent
from app.repositories.branch_repository import BranchRepository
from app.repositories.child_repository import ChildRepository
from app.repositories.finance_repository import InvoiceRepository
from app.repositories.messaging_repository import DailyJobRepository, OutboxRepository
from app.utils.timezone import today_local

# Outbox hodisa turlari — `OutboxProcessor._handle_event` shularni taniydi.
PAYMENT_REMINDER = "PAYMENT_REMINDER"
DEBT_WARNING = "DEBT_WARNING"
BIRTHDAY_GREETING = "BIRTHDAY_GREETING"

_JOB_NAME = "daily_notifications"
_DEBT_WARNING_DAYS_LATE = 15
_PAYMENT_REMINDER_DAYS = (1, 10)


async def run_daily(session: AsyncSession, today: date | None = None) -> int:
    """Bugun uchun kunlik bildirishnoma ishlarini bajaradi (bir marta).

    Qaytaradi: navbatga qo'yilgan OutboxEvent'lar soni (test/kuzatuv uchun).
    Bugun allaqachon bajarilgan bo'lsa — 0 qaytaradi, hech narsa qilmaydi.
    """
    today = today or today_local()
    jobs = DailyJobRepository(session)
    if not await jobs.try_claim(_JOB_NAME, today):
        return 0

    outbox = OutboxRepository(session)
    branches = BranchRepository(session)
    invoices = InvoiceRepository(session)
    children = ChildRepository(session)

    queued = 0

    branch_list = await branches.list_all()
    for branch in branch_list:
        outstanding = await invoices.list_outstanding_for_branch(branch.id)

        if today.day in _PAYMENT_REMINDER_DAYS:
            seen_children: set = set()
            for invoice in outstanding:
                if invoice.child_id in seen_children:
                    continue
                seen_children.add(invoice.child_id)
                outbox.add(
                    OutboxEvent(
                        event_type=PAYMENT_REMINDER,
                        payload={
                            "child_id": str(invoice.child_id),
                            "branch_id": str(branch.id),
                            "amount": str(invoice.outstanding_amount),
                        },
                    )
                )
                queued += 1

        debt_cutoff = today - timedelta(days=_DEBT_WARNING_DAYS_LATE)
        seen_debt_children: set = set()
        for invoice in outstanding:
            if invoice.due_date > debt_cutoff or invoice.child_id in seen_debt_children:
                continue
            seen_debt_children.add(invoice.child_id)
            outbox.add(
                OutboxEvent(
                    event_type=DEBT_WARNING,
                    payload={
                        "child_id": str(invoice.child_id),
                        "branch_id": str(branch.id),
                        "amount": str(invoice.outstanding_amount),
                        "days_late": (today - invoice.due_date).days,
                    },
                )
            )
            queued += 1

    all_children = await children.list_all()
    for child in all_children:
        if not child.is_active:
            continue
        if child.birth_date.month == today.month and child.birth_date.day == today.day:
            outbox.add(
                OutboxEvent(
                    event_type=BIRTHDAY_GREETING,
                    payload={"child_id": str(child.id)},
                )
            )
            queued += 1

    await session.flush()
    return queued
