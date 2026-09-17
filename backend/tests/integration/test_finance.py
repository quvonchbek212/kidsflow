"""Moliya oqimi integratsiya testlari (4.5, 4.7, 5.5, 5.6-bo'lim)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.utils.timezone import today_local
from httpx import AsyncClient

from tests.conftest import (
    FakeTelegramSender,
    auth_header,
    bot_header,
    complete_setup,
    create_staff,
    login,
    run_outbox,
)

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


def _dec(value: object) -> Decimal:
    return Decimal(str(value))


async def _scenario(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000001",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000001", "mgr-123-456"))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola Bir", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": branch_id, "name": "Guruh A", "capacity": 10},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(manager),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    # Tarif guruhda. Bola tarifsiz guruhga yozilgani uchun ro'yxatga olishda
    # hisob yaratilmaydi — testlar uni `_generate_invoice` bilan aniq oyga yaratadi.
    fee = await client.patch(
        f"/api/v1/groups/{group_id}",
        headers=auth_header(manager),
        json={"monthly_fee": 500000},
    )
    assert fee.status_code == 200, fee.text

    # Parent — to'lov bildirishnomasi uchun.
    parent_user_id = (
        await client.post(
            f"/api/v1/children/{child_id}/guardians",
            headers=auth_header(manager),
            json={
                "full_name": "Ota",
                "phone": "+998900000009",
                "relationship_type": "FATHER",
            },
        )
    ).json()["guardian_user_id"]
    code = (
        await client.post(
            "/api/v1/telegram/invitations",
            headers=auth_header(manager),
            json={"user_id": parent_user_id},
        )
    ).json()["code"]
    await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={"code": code, "telegram_user_id": 880088, "telegram_chat_id": 880088},
    )

    return {
        "manager": manager,
        "child_id": child_id,
        "branch_id": branch_id,
    }


async def _generate_invoice(client: AsyncClient, s: dict) -> dict:
    gen = await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "billing_period": "2026-09-15",
        },
    )
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] == 1
    invoices = (
        await client.get(
            f"/api/v1/children/{s['child_id']}/invoices",
            headers=auth_header(s["manager"]),
        )
    ).json()
    assert len(invoices) == 1
    return invoices[0]


async def test_generate_invoice(client: AsyncClient) -> None:
    s = await _scenario(client)
    invoice = await _generate_invoice(client, s)
    assert _dec(invoice["original_amount"]) == _dec("500000")
    assert _dec(invoice["outstanding_amount"]) == _dec("500000")
    assert invoice["status"] == "OPEN"
    assert invoice["billing_period"] == "2026-09-01"  # birinchi kunga normallashgan


async def test_partial_then_full_payment(client: AsyncClient) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)

    pay1 = await client.post(
        "/api/v1/payments",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "amount": 200000,
            "payment_method": "CASH",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    assert pay1.status_code == 201, pay1.text
    assert len(pay1.json()["allocations"]) == 1

    invoice = (
        await client.get(
            f"/api/v1/children/{s['child_id']}/invoices",
            headers=auth_header(s["manager"]),
        )
    ).json()[0]
    assert invoice["status"] == "PARTIALLY_PAID"
    assert _dec(invoice["outstanding_amount"]) == _dec("300000")

    # Qolgan qismini to'laymiz.
    await client.post(
        "/api/v1/payments",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "amount": 300000,
            "payment_method": "CARD",
            "paid_at": "2026-09-10T10:00:00Z",
        },
    )
    invoice = (
        await client.get(
            f"/api/v1/children/{s['child_id']}/invoices",
            headers=auth_header(s["manager"]),
        )
    ).json()[0]
    assert invoice["status"] == "PAID"
    assert _dec(invoice["outstanding_amount"]) == _dec("0")


async def test_payment_idempotency(client: AsyncClient) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)

    body = {
        "child_id": s["child_id"],
        "amount": 100000,
        "payment_method": "CASH",
        "paid_at": "2026-09-05T10:00:00Z",
        "idempotency_key": "unique-key-123",
    }
    first = await client.post(
        "/api/v1/payments", headers=auth_header(s["manager"]), json=body
    )
    second = await client.post(
        "/api/v1/payments", headers=auth_header(s["manager"]), json=body
    )
    assert first.json()["id"] == second.json()["id"]

    # Faqat bitta to'lov hisoblangan — outstanding 400000.
    invoice = (
        await client.get(
            f"/api/v1/children/{s['child_id']}/invoices",
            headers=auth_header(s["manager"]),
        )
    ).json()[0]
    assert _dec(invoice["outstanding_amount"]) == _dec("400000")


async def test_payment_reversal_restores_debt(client: AsyncClient) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)

    payment_id = (
        await client.post(
            "/api/v1/payments",
            headers=auth_header(s["manager"]),
            json={
                "child_id": s["child_id"],
                "amount": 500000,
                "payment_method": "CASH",
                "paid_at": "2026-09-05T10:00:00Z",
            },
        )
    ).json()["id"]

    rev = await client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        headers=auth_header(s["manager"]),
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVERSED"

    invoice = (
        await client.get(
            f"/api/v1/children/{s['child_id']}/invoices",
            headers=auth_header(s["manager"]),
        )
    ).json()[0]
    # Reversaldan keyin qarz qaytadi.
    assert _dec(invoice["outstanding_amount"]) == _dec("500000")
    assert invoice["status"] == "OPEN"


async def test_invoice_discount_adjustment(client: AsyncClient) -> None:
    s = await _scenario(client)
    invoice = await _generate_invoice(client, s)

    adjusted = await client.post(
        f"/api/v1/invoices/{invoice['id']}/adjustments",
        headers=auth_header(s["manager"]),
        json={"adjustment_type": "DISCOUNT", "amount": 100000, "reason": "Aka-uka"},
    )
    assert adjusted.status_code == 200
    body = adjusted.json()
    assert _dec(body["adjusted_amount"]) == _dec("400000")
    assert _dec(body["outstanding_amount"]) == _dec("400000")


async def test_expense_record_and_reverse(client: AsyncClient) -> None:
    s = await _scenario(client)
    category_id = (
        await client.get(
            "/api/v1/expense-categories", headers=auth_header(s["manager"])
        )
    ).json()[0]["id"]

    expense_id = (
        await client.post(
            "/api/v1/expenses",
            headers=auth_header(s["manager"]),
            json={
                "branch_id": s["branch_id"],
                "category_id": category_id,
                "amount": 750000,
                "expense_date": "2026-09-03",
                "vendor": "Oziq-ovqat ta'minotchi",
            },
        )
    ).json()
    assert expense_id["status"] == "RECORDED"

    rev = await client.post(
        f"/api/v1/expenses/{expense_id['id']}/reverse",
        headers=auth_header(s["manager"]),
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVERSED"


async def test_dashboard_separates_accrual_and_cash(client: AsyncClient) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)
    await client.post(
        "/api/v1/payments",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "amount": 200000,
            "payment_method": "CASH",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    category_id = (
        await client.get(
            "/api/v1/expense-categories", headers=auth_header(s["manager"])
        )
    ).json()[0]["id"]
    await client.post(
        "/api/v1/expenses",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "category_id": category_id,
            "amount": 50000,
            "expense_date": "2026-09-03",
        },
    )

    dash = await client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_header(s["manager"]),
        params={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert dash.status_code == 200
    body = dash.json()
    assert _dec(body["accrual_revenue"]) == _dec("500000")  # invoice bo'yicha
    assert _dec(body["cash_collected"]) == _dec("200000")  # real tushgan
    assert _dec(body["outstanding"]) == _dec("300000")  # qarzdorlik
    assert _dec(body["expenses"]) == _dec("50000")
    assert _dec(body["net_cash"]) == _dec("150000")  # 200000 - 50000


async def test_payment_notifies_parent_via_outbox(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)
    await client.post(
        "/api/v1/payments",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "amount": 500000,
            "payment_method": "CASH",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )

    sender = FakeTelegramSender(succeed=True)
    processed, dispatched = await run_outbox(session_factory, sender)
    assert processed == 1
    assert dispatched == 1
    chat_id, text = sender.sent[0]
    assert chat_id == 880088
    assert "to'lov" in text.lower()


async def test_list_branch_invoices_for_period(client: AsyncClient) -> None:
    s = await _scenario(client)
    await _generate_invoice(client, s)

    resp = await client.get(
        "/api/v1/invoices",
        headers=auth_header(s["manager"]),
        params={"branch_id": s["branch_id"], "billing_period": "2026-09-15"},
    )
    assert resp.status_code == 200
    invoices = resp.json()
    assert len(invoices) == 1
    assert invoices[0]["child_id"] == s["child_id"]


async def test_list_branch_expenses_filtered_by_period(client: AsyncClient) -> None:
    s = await _scenario(client)
    category_id = (
        await client.get(
            "/api/v1/expense-categories", headers=auth_header(s["manager"])
        )
    ).json()[0]["id"]
    await client.post(
        "/api/v1/expenses",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "category_id": category_id,
            "amount": 60000,
            "expense_date": "2026-09-10",
        },
    )
    await client.post(
        "/api/v1/expenses",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "category_id": category_id,
            "amount": 70000,
            "expense_date": "2026-10-10",
        },
    )

    resp = await client.get(
        "/api/v1/expenses",
        headers=auth_header(s["manager"]),
        params={
            "branch_id": s["branch_id"],
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
        },
    )
    assert resp.status_code == 200
    expenses = resp.json()
    assert len(expenses) == 1
    assert expenses[0]["expense_date"] == "2026-09-10"


async def test_generate_invoice_uses_group_monthly_fee(client: AsyncClient) -> None:
    """Invoice guruhning oylik tarifidan hisoblanadi.

    Ilovada tarif guruh formasida ("Oylik tarif") kiritiladi — bu yo'l
    ishlamasa invoice doim 0 ta yaratilardi va to'lovlar bo'limi butunlay
    ishlamasdi.

    Invoice endi bola faol bo'lgan zahoti avtomatik yaratiladi, shuning uchun
    keyingi qo'lda generatsiya uni ikkilantirmasligi ham tekshiriladi.
    """
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Tarifli Bola", "birth_date": "2021-05-05"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "name": "Quyoshcha",
                "capacity": 10,
                "monthly_fee": 1200000,
            },
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": today_local().replace(day=1).isoformat(),
            "status": "ACTIVE",
        },
    )

    gen = await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(owner),
        json={"branch_id": branch_id, "billing_period": today_local().isoformat()},
    )
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] == 0
    assert gen.json()["skipped"] == 1

    invoices = (
        await client.get(
            f"/api/v1/children/{child_id}/invoices",
            headers=auth_header(owner),
        )
    ).json()
    assert len(invoices) == 1
    assert _dec(invoices[0]["original_amount"]) == _dec("1200000")
    assert _dec(invoices[0]["outstanding_amount"]) == _dec("1200000")


async def test_generate_invoice_skips_group_without_fee(client: AsyncClient) -> None:
    """Tarif hech qayerda ko'rsatilmagan bo'lsa invoice yaratilmaydi."""
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Tarifsiz Bola", "birth_date": "2021-05-05"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(owner),
            json={"branch_id": branch_id, "name": "Tarifsiz", "capacity": 10},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )

    gen = await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(owner),
        json={"branch_id": branch_id, "billing_period": "2026-09-15"},
    )
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] == 0
    assert gen.json()["skipped"] == 1
