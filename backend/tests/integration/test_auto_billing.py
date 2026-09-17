"""Avtomatik oylik hisob-faktura testlari.

Hisob-fakturalar endi qo'lda yaratilmaydi: bola faol bo'lganda darhol, qolgan
hollarda kunlik worker (`auto_billing.run_daily`) yaratadi. Oldindan to'langan
pul yangi hisobga o'zi yoziladi.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from app.services import auto_billing
from app.utils.timezone import today_local
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


def _dec(value: object) -> Decimal:
    return Decimal(str(value))


def _next_month(day: date) -> date:
    return (day.replace(day=1) + timedelta(days=32)).replace(day=1)


async def _setup(client: AsyncClient, monthly_fee: int | None) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    group = {"branch_id": branch_id, "name": "Guruh A", "capacity": 10}
    if monthly_fee is not None:
        group["monthly_fee"] = monthly_fee
    group_id = (
        await client.post("/api/v1/groups", headers=auth_header(owner), json=group)
    ).json()["id"]
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Bola Avto", "birth_date": "2021-05-05"},
        )
    ).json()["id"]
    return {
        "branch_id": branch_id,
        "owner": owner,
        "group_id": group_id,
        "child_id": child_id,
    }


async def _enroll(client: AsyncClient, s: dict, start: date) -> None:
    resp = await client.post(
        f"/api/v1/children/{s['child_id']}/enrollments",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "start_date": start.isoformat(),
            "status": "ACTIVE",
        },
    )
    assert resp.status_code in (200, 201), resp.text


async def _invoices(client: AsyncClient, s: dict) -> list[dict]:
    resp = await client.get(
        f"/api/v1/children/{s['child_id']}/invoices", headers=auth_header(s["owner"])
    )
    assert resp.status_code == 200, resp.text
    return sorted(resp.json(), key=lambda inv: inv["billing_period"])


async def _set_fee(client: AsyncClient, s: dict, fee: int) -> None:
    resp = await client.patch(
        f"/api/v1/groups/{s['group_id']}",
        headers=auth_header(s["owner"]),
        json={"monthly_fee": fee},
    )
    assert resp.status_code == 200, resp.text


async def _run_daily(session_factory, today: date) -> int:
    async with session_factory() as session:
        created = await auto_billing.run_daily(session, today)
        await session.commit()
        return created


async def test_enrollment_bills_current_month_immediately(
    client: AsyncClient,
) -> None:
    s = await _setup(client, monthly_fee=900_000)
    today = today_local()
    await _enroll(client, s, today.replace(day=1))

    invoices = await _invoices(client, s)
    assert len(invoices) == 1
    invoice = invoices[0]
    assert invoice["billing_period"] == today.replace(day=1).isoformat()
    assert _dec(invoice["outstanding_amount"]) == Decimal("900000")
    # Muddat — oyning 10-sanasi, lekin bugundan oldin emas.
    expected_due = max(today.replace(day=10), today)
    assert invoice["due_date"] == expected_due.isoformat()


async def test_daily_job_bills_active_children_once(
    client: AsyncClient, session_factory
) -> None:
    # Tarifsiz guruh — ro'yxatga olishda hisob yaratilmaydi.
    s = await _setup(client, monthly_fee=None)
    today = today_local()
    await _enroll(client, s, today.replace(day=1))
    assert await _invoices(client, s) == []

    await _set_fee(client, s, 600_000)
    assert await _run_daily(session_factory, today) == 1
    # Shu kuni ikkinchi marta ishga tushsa hech narsa qilmaydi.
    assert await _run_daily(session_factory, today) == 0

    invoices = await _invoices(client, s)
    assert len(invoices) == 1
    assert _dec(invoices[0]["adjusted_amount"]) == Decimal("600000")


async def test_prepayment_is_applied_to_new_invoices(
    client: AsyncClient, session_factory
) -> None:
    s = await _setup(client, monthly_fee=None)
    today = today_local()
    await _enroll(client, s, today.replace(day=1))

    # Hisob hali yo'q — ota-ona oldindan 700 000 to'ladi.
    paid = await client.post(
        "/api/v1/payments",
        headers=auth_header(s["owner"]),
        json={
            "child_id": s["child_id"],
            "amount": "700000",
            "payment_method": "CASH",
            "paid_at": datetime.now(UTC).isoformat(),
        },
    )
    assert paid.status_code in (200, 201), paid.text

    await _set_fee(client, s, 500_000)
    assert await _run_daily(session_factory, today) == 1
    first = (await _invoices(client, s))[0]
    assert first["status"] == "PAID"
    assert _dec(first["outstanding_amount"]) == Decimal("0")

    # Qolgan 200 000 keyingi oy hisobiga o'tadi.
    assert await _run_daily(session_factory, _next_month(today)) == 1
    second = (await _invoices(client, s))[1]
    assert _dec(second["paid_amount"]) == Decimal("200000")
    assert _dec(second["outstanding_amount"]) == Decimal("300000")
    assert second["status"] == "PARTIALLY_PAID"


async def test_waitlisted_child_is_billed_only_after_admission(
    client: AsyncClient, session_factory
) -> None:
    """Navbatdagi (PLANNED) bola hisoblanmaydi; qabul qilingach hisob ochiladi
    va kutilayotgan sana haqiqiy qabul sanasiga almashadi."""
    s = await _setup(client, monthly_fee=750_000)
    today = today_local()
    created = await client.post(
        f"/api/v1/children/{s['child_id']}/enrollments",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "start_date": (today - timedelta(days=40)).isoformat(),
            "status": "PLANNED",
        },
    )
    assert created.status_code == 201, created.text
    enrollment_id = created.json()["id"]

    child = await client.get(
        f"/api/v1/children/{s['child_id']}", headers=auth_header(s["owner"])
    )
    assert child.json()["status"] == "waiting"
    assert child.json()["enrollment"]["id"] == enrollment_id
    assert child.json()["enrollment"]["group_id"] == s["group_id"]

    assert await _invoices(client, s) == []
    assert await _run_daily(session_factory, today) == 0

    admitted = await client.patch(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=auth_header(s["owner"]),
        json={"status": "ACTIVE", "start_date": today.isoformat()},
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["start_date"] == today.isoformat()

    invoices = await _invoices(client, s)
    assert len(invoices) == 1
    assert _dec(invoices[0]["adjusted_amount"]) == Decimal("750000")

    # Faol bo'lgach boshlanish sanasi o'zgarmaydi — u hisob tarixiga bog'langan.
    moved = await client.patch(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=auth_header(s["owner"]),
        json={"start_date": (today - timedelta(days=5)).isoformat()},
    )
    assert moved.status_code == 409, moved.text


async def test_future_enrollment_is_not_billed_this_month(
    client: AsyncClient, session_factory
) -> None:
    s = await _setup(client, monthly_fee=800_000)
    today = today_local()
    await _enroll(client, s, _next_month(today))

    assert await _invoices(client, s) == []
    assert await _run_daily(session_factory, today) == 0

    # Keyingi oy kelganda hisob yaratiladi.
    assert await _run_daily(session_factory, _next_month(today)) == 1
    invoices = await _invoices(client, s)
    assert invoices[0]["billing_period"] == _next_month(today).isoformat()


async def test_invoice_due_day_comes_from_branch_settings(
    client: AsyncClient,
) -> None:
    s = await _setup(client, monthly_fee=700_000)
    resp = await client.patch(
        f"/api/v1/messages/settings?branch_id={s['branch_id']}",
        headers=auth_header(s["owner"]),
        json={"invoice_due_day": 25},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["invoice_due_day"] == 25

    bad = await client.patch(
        f"/api/v1/messages/settings?branch_id={s['branch_id']}",
        headers=auth_header(s["owner"]),
        json={"invoice_due_day": 31},
    )
    assert bad.status_code == 422

    today = today_local()
    await _enroll(client, s, today.replace(day=1))
    invoice = (await _invoices(client, s))[0]
    assert invoice["due_date"] == max(today.replace(day=25), today).isoformat()


async def test_deactivated_child_is_not_billed_anymore(
    client: AsyncClient, session_factory
) -> None:
    """Faolsizlantirilgan bola guruhdan chiqadi va keyingi oydan hisoblanmaydi."""
    s = await _setup(client, monthly_fee=900_000)
    today = today_local()
    await _enroll(client, s, today.replace(day=1))
    assert len(await _invoices(client, s)) == 1

    resp = await client.patch(
        f"/api/v1/children/{s['child_id']}",
        headers=auth_header(s["owner"]),
        json={"is_active": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "left"
    assert resp.json()["enrollment"]["status"] == "COMPLETED"

    # Joriy oy hisobi o'zgarmaydi, keyingi oy uchun yangisi yaratilmaydi.
    assert await _run_daily(session_factory, _next_month(today)) == 0
    assert len(await _invoices(client, s)) == 1


async def test_re_enrolling_deactivated_child_reactivates_it(
    client: AsyncClient,
) -> None:
    s = await _setup(client, monthly_fee=None)
    today = today_local()
    await _enroll(client, s, today.replace(day=1))
    await client.patch(
        f"/api/v1/children/{s['child_id']}",
        headers=auth_header(s["owner"]),
        json={"is_active": False},
    )

    # Bitta so'rov: guruhga qayta yozish bolani ham faollashtiradi.
    await _enroll(client, s, today)
    child = await client.get(
        f"/api/v1/children/{s['child_id']}", headers=auth_header(s["owner"])
    )
    assert child.json()["is_active"] is True
    assert child.json()["status"] == "active"
    assert child.json()["enrollment"]["start_date"] == today.isoformat()
