"""Guruh davomat rosteri integratsiya testlari."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _scenario(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    child1 = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Bola Bir", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    child2 = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Bola Ikki", "birth_date": "2021-02-02"},
        )
    ).json()["id"]

    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(owner),
            json={"branch_id": branch_id, "name": "Guruh A", "capacity": 10},
        )
    ).json()["id"]

    for child_id in (child1, child2):
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

    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000030",
        password="teacher-123",
        branch_id=branch_id,
    )
    await client.post(
        f"/api/v1/groups/{group_id}/teachers",
        headers=auth_header(owner),
        json={"teacher_user_id": teacher_id},
    )
    teacher = (await login(client, "+998900000030", "teacher-123"))["access_token"]

    return {
        "owner": owner,
        "teacher": teacher,
        "group_id": group_id,
        "child1": child1,
        "child2": child2,
    }


async def test_roster_shows_unmarked_and_marked(client: AsyncClient) -> None:
    s = await _scenario(client)

    await client.post(
        "/api/v1/attendance",
        headers=auth_header(s["teacher"]),
        json={
            "child_id": s["child1"],
            "attendance_date": "2026-09-02",
            "status": "PRESENT",
        },
    )

    resp = await client.get(
        "/api/v1/attendance/roster",
        headers=auth_header(s["teacher"]),
        params={"group_id": s["group_id"], "date": "2026-09-02"},
    )
    assert resp.status_code == 200
    rows = {r["child_id"]: r for r in resp.json()}
    assert len(rows) == 2
    assert rows[s["child1"]]["status"] == "PRESENT"
    assert rows[s["child2"]]["status"] is None


async def test_roster_forbidden_for_unrelated_teacher(client: AsyncClient) -> None:
    s = await _scenario(client)

    # Boshqa filialdagi, shu guruhga biriktirilmagan tarbiyachi.
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(s["owner"]),
            json={"name": "Filial B"},
        )
    ).json()["id"]
    await create_staff(
        client,
        s["owner"],
        role="TEACHER",
        phone="+998900000032",
        password="teacher-888",
        branch_id=branch_b,
    )
    unrelated_teacher = (await login(client, "+998900000032", "teacher-888"))[
        "access_token"
    ]

    resp = await client.get(
        "/api/v1/attendance/roster",
        headers=auth_header(unrelated_teacher),
        params={"group_id": s["group_id"], "date": "2026-09-02"},
    )
    assert resp.status_code == 403
