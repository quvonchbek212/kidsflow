"""Payroll (oylik hisoblash va to'lash) integratsiya testlari (7-bosqich B)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


def _dec(value: object) -> Decimal:
    return Decimal(str(value))


async def _scenario(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    staff_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000050",
        password="teacher-parol-1",
        branch_id=branch_id,
    )
    await client.patch(
        f"/api/v1/users/{staff_id}",
        headers=auth_header(owner),
        json={"monthly_salary": "4000000"},
    )
    return {"owner": owner, "branch_id": branch_id, "staff_id": staff_id}


async def test_calculate_and_pay_creates_linked_expense(client: AsyncClient) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "period": "2026-09-05",
            "bonus": "200000",
            "deduction": "50000",
            "advance_deducted": "0",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert _dec(body["base_salary"]) == _dec("4000000")
    assert _dec(body["net_pay"]) == _dec("4150000")  # 4,000,000 + 200,000 - 50,000
    assert body["period"] == "2026-09-01"
    assert body["expense_id"] is not None

    expenses = await client.get(
        "/api/v1/expenses",
        headers=auth_header(s["owner"]),
        params={"branch_id": s["branch_id"]},
    )
    matching = [e for e in expenses.json() if e["id"] == body["expense_id"]]
    assert len(matching) == 1
    assert _dec(matching[0]["amount"]) == _dec("4150000")


async def test_duplicate_period_rejected(client: AsyncClient) -> None:
    s = await _scenario(client)
    body = {
        "branch_id": s["branch_id"],
        "user_id": s["staff_id"],
        "period": "2026-09-05",
        "paid_at": "2026-09-05T10:00:00Z",
    }
    first = await client.post(
        "/api/v1/payroll/runs", headers=auth_header(s["owner"]), json=body
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/payroll/runs", headers=auth_header(s["owner"]), json=body
    )
    assert second.status_code == 409


async def test_reverse_unblocks_period_and_reverses_expense(
    client: AsyncClient,
) -> None:
    s = await _scenario(client)
    body = {
        "branch_id": s["branch_id"],
        "user_id": s["staff_id"],
        "period": "2026-09-05",
        "paid_at": "2026-09-05T10:00:00Z",
    }
    run = (
        await client.post(
            "/api/v1/payroll/runs", headers=auth_header(s["owner"]), json=body
        )
    ).json()

    rev = await client.post(
        f"/api/v1/payroll/runs/{run['id']}/reverse", headers=auth_header(s["owner"])
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "REVERSED"

    expense = await client.get(
        "/api/v1/expenses",
        headers=auth_header(s["owner"]),
        params={"branch_id": s["branch_id"]},
    )
    matching = [e for e in expense.json() if e["id"] == run["expense_id"]]
    assert matching[0]["status"] == "REVERSED"

    # Bekor qilingandan keyin xuddi shu davr uchun qayta hisoblash mumkin.
    redo = await client.post(
        "/api/v1/payroll/runs", headers=auth_header(s["owner"]), json=body
    )
    assert redo.status_code == 201, redo.text


async def test_list_runs_for_user(client: AsyncClient) -> None:
    s = await _scenario(client)
    await client.post(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "period": "2026-09-05",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    resp = await client.get(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        params={"user_id": s["staff_id"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def _advance(client: AsyncClient, s: dict, amount: str, paid_at: str):
    return await client.post(
        "/api/v1/payroll/advances",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "amount": amount,
            "paid_at": paid_at,
        },
    )


async def test_advance_is_recorded_and_deducted_automatically(
    client: AsyncClient,
) -> None:
    """Oy o'rtasidagi avans yoziladi va oylik hisobida o'zi ushlanadi."""
    s = await _scenario(client)
    first = await _advance(client, s, "1000000", "2026-09-15T09:00:00Z")
    assert first.status_code == 201, first.text
    assert first.json()["period"] == "2026-09-01"
    second = await _advance(client, s, "500000", "2026-09-20T09:00:00Z")
    assert second.status_code == 201, second.text

    listed = await client.get(
        "/api/v1/payroll/advances",
        headers=auth_header(s["owner"]),
        params={"branch_id": s["branch_id"], "period": "2026-09-01"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    # Avans xarajat sifatida darhol ko'rinadi.
    expenses = (
        await client.get(
            "/api/v1/expenses",
            headers=auth_header(s["owner"]),
            params={"branch_id": s["branch_id"]},
        )
    ).json()
    assert first.json()["expense_id"] in {e["id"] for e in expenses}

    # Qo'lda "0" yuborilsa ham yozilgan avanslar ushlanadi.
    run = await client.post(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "period": "2026-09-01",
            "advance_deducted": "0",
            "paid_at": "2026-09-30T10:00:00Z",
        },
    )
    assert run.status_code == 201, run.text
    assert _dec(run.json()["advance_deducted"]) == _dec("1500000")
    assert _dec(run.json()["net_pay"]) == _dec("2500000")  # 4 000 000 − 1 500 000

    # Oylik hisoblangan oyga yangi avans berilmaydi, eskisi bekor qilinmaydi.
    late = await _advance(client, s, "100000", "2026-09-30T12:00:00Z")
    assert late.status_code == 409, late.text
    blocked = await client.post(
        f"/api/v1/payroll/advances/{first.json()['id']}/reverse",
        headers=auth_header(s["owner"]),
    )
    assert blocked.status_code == 409, blocked.text

    # Oylik bekor qilingach avansni ham bekor qilish mumkin.
    await client.post(
        f"/api/v1/payroll/runs/{run.json()['id']}/reverse",
        headers=auth_header(s["owner"]),
    )
    reversed_ = await client.post(
        f"/api/v1/payroll/advances/{first.json()['id']}/reverse",
        headers=auth_header(s["owner"]),
    )
    assert reversed_.status_code == 200, reversed_.text
    assert reversed_.json()["status"] == "REVERSED"

    redo = await client.post(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "period": "2026-09-01",
            "paid_at": "2026-09-30T10:00:00Z",
        },
    )
    assert redo.status_code == 201, redo.text
    assert _dec(redo.json()["advance_deducted"]) == _dec("500000")


async def test_advances_cannot_exceed_salary(client: AsyncClient) -> None:
    s = await _scenario(client)
    ok = await _advance(client, s, "3000000", "2026-09-10T09:00:00Z")
    assert ok.status_code == 201, ok.text
    too_much = await _advance(client, s, "1500000", "2026-09-15T09:00:00Z")
    assert too_much.status_code == 409, too_much.text


async def test_teacher_cannot_give_advance(client: AsyncClient) -> None:
    s = await _scenario(client)
    teacher = (await login(client, "+998900000050", "teacher-parol-1"))["access_token"]
    resp = await client.post(
        "/api/v1/payroll/advances",
        headers=auth_header(teacher),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "amount": "100000",
            "paid_at": "2026-09-10T09:00:00Z",
        },
    )
    assert resp.status_code == 403, resp.text
