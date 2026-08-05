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
