"""Agregat endpointlar: `/attendance/branch-summary` va `/analytics/monthly`.

Bosh sahifa ilgari har bir guruh uchun roster va trend'ni, har bir oy uchun
esa to'liq dashboard'ni alohida chaqirardi — 10 guruhli bog'chada bu 27 ta
HTTP so'rov edi. Bu endpointlar o'sha ma'lumotni bitta so'rovda beradi.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login
from app.utils.timezone import today_local

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _world(client: AsyncClient) -> dict:
    """Ikkita guruh, har birida bittadan bola (ACTIVE enrollment)."""
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    today = today_local().isoformat()

    groups: dict[str, str] = {}
    children: dict[str, str] = {}
    for name, child_name in (("A-guruh", "Ali"), ("B-guruh", "Bobur")):
        group_id = (
            await client.post(
                "/api/v1/groups",
                headers=auth_header(owner),
                json={"branch_id": branch_id, "name": name, "capacity": 15},
            )
        ).json()["id"]
        child_id = (
            await client.post(
                "/api/v1/children",
                headers=auth_header(owner),
                json={"full_name": child_name, "birth_date": "2021-05-10"},
            )
        ).json()["id"]
        enroll = await client.post(
            f"/api/v1/children/{child_id}/enrollments",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "group_id": group_id,
                "start_date": "2026-01-01",
                "status": "ACTIVE",
            },
        )
        assert enroll.status_code == 201, enroll.text
        groups[name] = group_id
        children[child_name] = child_id

    return {
        "owner": owner,
        "branch_id": branch_id,
        "groups": groups,
        "children": children,
        "today": today,
    }


async def test_branch_summary_covers_every_group(client: AsyncClient) -> None:
    w = await _world(client)

    resp = await client.get(
        "/api/v1/attendance/branch-summary",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_id"], "date": w["today"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert {g["group_name"] for g in body["groups"]} == {"A-guruh", "B-guruh"}
    assert body["totals"]["total"] == 2
    # Hech kim belgilanmagan — hammasi "unmarked".
    assert body["totals"]["unmarked"] == 2
    assert body["totals"]["present"] == 0


async def test_branch_summary_reflects_marked_attendance(
    client: AsyncClient,
) -> None:
    w = await _world(client)
    ali = w["children"]["Ali"]

    mark = await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(w["owner"]),
        json={
            "group_id": w["groups"]["A-guruh"],
            "attendance_date": w["today"],
            "entries": [{"child_id": ali, "status": "PRESENT"}],
        },
    )
    assert mark.status_code in (200, 201), mark.text

    body = (
        await client.get(
            "/api/v1/attendance/branch-summary",
            headers=auth_header(w["owner"]),
            params={"branch_id": w["branch_id"], "date": w["today"]},
        )
    ).json()

    assert body["totals"]["present"] == 1
    assert body["totals"]["unmarked"] == 1
    a_group = next(g for g in body["groups"] if g["group_name"] == "A-guruh")
    assert a_group["rows"][0]["status"] == "PRESENT"


async def test_branch_summary_trend_length_matches_request(
    client: AsyncClient,
) -> None:
    w = await _world(client)
    body = (
        await client.get(
            "/api/v1/attendance/branch-summary",
            headers=auth_header(w["owner"]),
            params={
                "branch_id": w["branch_id"],
                "date": w["today"],
                "trend_days": 5,
            },
        )
    ).json()
    assert len(body["trend"]) == 5
    assert all(p["total_count"] == 2 for p in body["trend"])


async def test_branch_summary_rejects_foreign_branch(client: AsyncClient) -> None:
    w = await _world(client)
    other = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(w["owner"]),
            json={"name": "Ikkinchi filial", "capacity": 20},
        )
    ).json()["id"]

    await create_staff(
        client,
        w["owner"],
        role="MANAGER",
        phone="+998907654321",
        password="manager-parol-123",
        branch_id=w["branch_id"],
    )
    manager = (await login(client, "+998907654321", "manager-parol-123"))[
        "access_token"
    ]

    resp = await client.get(
        "/api/v1/attendance/branch-summary",
        headers=auth_header(manager),
        params={"branch_id": other, "date": w["today"]},
    )
    assert resp.status_code == 403


async def test_monthly_returns_requested_number_of_months(
    client: AsyncClient,
) -> None:
    w = await _world(client)
    resp = await client.get(
        "/api/v1/analytics/monthly",
        headers=auth_header(w["owner"]),
        params={"months": 6, "branch_id": w["branch_id"]},
    )
    assert resp.status_code == 200, resp.text
    months = resp.json()["months"]
    assert len(months) == 6
    # Oxirgisi joriy oy bo'lishi kerak, ro'yxat esa o'sish tartibida.
    assert months[-1]["period_start"].startswith(today_local().strftime("%Y-%m"))
    starts = [m["period_start"] for m in months]
    assert starts == sorted(starts)


async def test_monthly_totals_match_recorded_expense(client: AsyncClient) -> None:
    """Agregat raqamlari dashboard bilan bir xil manbadan kelishi kerak."""
    w = await _world(client)
    category_id = (
        await client.get(
            "/api/v1/expense-categories", headers=auth_header(w["owner"])
        )
    ).json()[0]["id"]
    expense = await client.post(
        "/api/v1/expenses",
        headers=auth_header(w["owner"]),
        json={
            "branch_id": w["branch_id"],
            "category_id": category_id,
            "amount": 250000,
            "expense_date": w["today"],
        },
    )
    assert expense.status_code == 201, expense.text

    months = (
        await client.get(
            "/api/v1/analytics/monthly",
            headers=auth_header(w["owner"]),
            params={"months": 1, "branch_id": w["branch_id"]},
        )
    ).json()["months"]
    assert Decimal(str(months[0]["expenses"])) == Decimal("250000")


async def test_monthly_rejects_foreign_branch(client: AsyncClient) -> None:
    w = await _world(client)
    other = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(w["owner"]),
            json={"name": "Ikkinchi filial", "capacity": 20},
        )
    ).json()["id"]
    await create_staff(
        client,
        w["owner"],
        role="MANAGER",
        phone="+998907654321",
        password="manager-parol-123",
        branch_id=w["branch_id"],
    )
    manager = (await login(client, "+998907654321", "manager-parol-123"))[
        "access_token"
    ]

    resp = await client.get(
        "/api/v1/analytics/monthly",
        headers=auth_header(manager),
        params={"months": 3, "branch_id": other},
    )
    assert resp.status_code == 403
