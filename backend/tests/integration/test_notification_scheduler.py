"""Kunlik avtomatik bildirishnoma ishlari testlari (7-bosqich B).

`notification_scheduler.run_daily` to'g'ridan-to'g'ri sessiya ustida
chaqiriladi — bu sinovlarning "bugun" ga bog'liqligini nazorat qilish uchun
Invoice/Child qatorlari to'g'ridan-to'g'ri (HTTP orqali emas) `date.today()`ga
nisbatan quriladi.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.models.child import Child
from app.models.enums import InvoiceStatus, OutboxStatus
from app.models.finance import Invoice
from app.models.messaging import OutboxEvent
from app.services import notification_scheduler
from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _branch_and_child(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000201",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000201", "mgr-123-456"))["access_token"]
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola Uch", "birth_date": "2021-03-03"},
        )
    ).json()["id"]
    return {"branch_id": branch_id, "child_id": child_id, "manager": manager}


async def _add_outstanding_invoice(
    session_factory, branch_id: str, child_id: str, due_date: date
) -> None:
    async with session_factory() as session:
        invoice = Invoice(
            branch_id=uuid.UUID(branch_id),
            child_id=uuid.UUID(child_id),
            billing_period=due_date.replace(day=1),
            due_date=due_date,
            original_amount=Decimal("500000"),
            discount_amount=Decimal("0"),
            adjusted_amount=Decimal("500000"),
            paid_amount=Decimal("0"),
            outstanding_amount=Decimal("500000"),
            status=InvoiceStatus.OPEN.value,
        )
        session.add(invoice)
        await session.commit()


async def _outbox_event_types(session_factory) -> list[str]:
    async with session_factory() as session:
        stmt = select(OutboxEvent.event_type).where(
            OutboxEvent.status == OutboxStatus.PENDING.value
        )
        return list((await session.execute(stmt)).scalars().all())


async def test_debt_warning_queued_for_overdue_invoice(
    client: AsyncClient, session_factory
) -> None:
    s = await _branch_and_child(client)
    overdue_due_date = date.today() - timedelta(days=20)
    await _add_outstanding_invoice(
        session_factory, s["branch_id"], s["child_id"], overdue_due_date
    )

    async with session_factory() as session:
        queued = await notification_scheduler.run_daily(session)
        await session.commit()

    assert queued >= 1
    assert "DEBT_WARNING" in await _outbox_event_types(session_factory)


async def test_birthday_greeting_queued_for_child_born_today(
    client: AsyncClient, session_factory
) -> None:
    s = await _branch_and_child(client)
    today = date.today()
    async with session_factory() as session:
        child = await session.get(Child, uuid.UUID(s["child_id"]))
        assert child is not None
        child.birth_date = today.replace(year=today.year - 5)
        await session.commit()

    async with session_factory() as session:
        queued = await notification_scheduler.run_daily(session)
        await session.commit()

    assert queued >= 1
    assert "BIRTHDAY_GREETING" in await _outbox_event_types(session_factory)


async def test_run_daily_is_claimed_once_per_day(
    client: AsyncClient, session_factory
) -> None:
    s = await _branch_and_child(client)
    overdue_due_date = date.today() - timedelta(days=20)
    await _add_outstanding_invoice(
        session_factory, s["branch_id"], s["child_id"], overdue_due_date
    )

    async with session_factory() as session:
        first = await notification_scheduler.run_daily(session)
        await session.commit()
    assert first >= 1

    async with session_factory() as session:
        second = await notification_scheduler.run_daily(session)
        await session.commit()
    assert second == 0
