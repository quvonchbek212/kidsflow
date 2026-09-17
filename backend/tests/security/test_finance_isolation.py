"""Moliya filial izolyatsiyasi (16-bo'lim 14-qoida)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _two_branch_scenario(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_a = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Filial B"},
        )
    ).json()["id"]

    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000001",
        password="mgr-a-123",
        branch_id=branch_a,
    )
    mgr_a = (await login(client, "+998900000001", "mgr-a-123"))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000002",
        password="mgr-b-123",
        branch_id=branch_b,
    )
    mgr_b = (await login(client, "+998900000002", "mgr-b-123"))["access_token"]

    # branch_a da bola, guruh, enrollment, tarif.
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(mgr_a),
            json={"full_name": "Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(mgr_a),
            json={"branch_id": branch_a, "name": "G", "capacity": 10},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(mgr_a),
        json={
            "branch_id": branch_a,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    return {
        "branch_a": branch_a,
        "mgr_a": mgr_a,
        "mgr_b": mgr_b,
        "child_id": child_id,
    }


async def test_manager_cannot_generate_invoices_in_other_branch(
    client: AsyncClient,
) -> None:
    s = await _two_branch_scenario(client)
    resp = await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(s["mgr_b"]),
        json={"branch_id": s["branch_a"], "billing_period": "2026-09-01"},
    )
    assert resp.status_code == 403


async def test_manager_cannot_record_payment_for_other_branch_child(
    client: AsyncClient,
) -> None:
    s = await _two_branch_scenario(client)
    # branch_a bolasi uchun to'lov — branch_b manageri kirita olmaydi.
    resp = await client.post(
        "/api/v1/payments",
        headers=auth_header(s["mgr_b"]),
        json={
            "child_id": s["child_id"],
            "amount": 100000,
            "payment_method": "CASH",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    assert resp.status_code == 403


async def test_manager_cannot_record_expense_in_other_branch(
    client: AsyncClient,
) -> None:
    s = await _two_branch_scenario(client)
    category_id = (
        await client.get("/api/v1/expense-categories", headers=auth_header(s["mgr_a"]))
    ).json()[0]["id"]
    resp = await client.post(
        "/api/v1/expenses",
        headers=auth_header(s["mgr_b"]),
        json={
            "branch_id": s["branch_a"],
            "category_id": category_id,
            "amount": 100000,
            "expense_date": "2026-09-03",
        },
    )
    assert resp.status_code == 403
