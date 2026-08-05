"""2-bosqich izolyatsiya testlari (16-bo'lim 14-qoida).

- PARENT faqat o'z bolasini ko'radi.
- TEACHER faqat o'z guruhidagi bolalarni ko'radi.
- MANAGER boshqa filialda amal bajara olmaydi.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    auth_header,
    bot_header,
    complete_setup,
    create_staff,
    login,
)

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _scenario(client: AsyncClient) -> dict:
    """To'liq ssenariy: ikki filial, manager, teacher, parent, ikkita bola."""
    setup = await complete_setup(client)
    branch_a = setup["branch_id"]
    owner_access = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    # Ikkinchi filial.
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner_access),
            json={"name": "Ikkinchi filial"},
        )
    ).json()["id"]

    # Har filialga manager.
    await create_staff(
        client,
        owner_access,
        role="MANAGER",
        phone="+998900000001",
        password="mgr-a-123",
        branch_id=branch_a,
    )
    mgr_a = (await login(client, "+998900000001", "mgr-a-123"))["access_token"]
    await create_staff(
        client,
        owner_access,
        role="MANAGER",
        phone="+998900000002",
        password="mgr-b-123",
        branch_id=branch_b,
    )
    mgr_b = (await login(client, "+998900000002", "mgr-b-123"))["access_token"]

    # branch_a da bola1, guruh, enrollment.
    child1 = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(mgr_a),
            json={"full_name": "Bola Bir", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_a = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(mgr_a),
            json={"branch_id": branch_a, "name": "Guruh A", "capacity": 10},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child1}/enrollments",
        headers=auth_header(mgr_a),
        json={
            "branch_id": branch_a,
            "group_id": group_a,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )

    # Aloqasi yo'q bola2 (enrollmentsiz).
    child2 = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(mgr_a),
            json={"full_name": "Bola Ikki", "birth_date": "2021-02-02"},
        )
    ).json()["id"]

    # Teacher — group_a ga biriktirilgan.
    teacher_id = await create_staff(
        client,
        owner_access,
        role="TEACHER",
        phone="+998900000003",
        password="teacher-123",
        branch_id=branch_a,
    )
    await client.post(
        f"/api/v1/groups/{group_a}/teachers",
        headers=auth_header(mgr_a),
        json={"teacher_user_id": teacher_id},
    )
    teacher_access = (await login(client, "+998900000003", "teacher-123"))[
        "access_token"
    ]

    # Parent — child1 vasiysi, Telegram orqali bog'lanadi.
    parent_user_id = (
        await client.post(
            f"/api/v1/children/{child1}/guardians",
            headers=auth_header(mgr_a),
            json={
                "full_name": "Ota Bir",
                "phone": "+998900000009",
                "relationship_type": "FATHER",
            },
        )
    ).json()["guardian_user_id"]
    code = (
        await client.post(
            "/api/v1/telegram/invitations",
            headers=auth_header(mgr_a),
            json={"user_id": parent_user_id},
        )
    ).json()["code"]
    await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={"code": code, "telegram_user_id": 770077},
    )
    parent_access = (
        await client.post(
            "/api/v1/telegram/session",
            headers=bot_header(),
            json={"telegram_user_id": 770077},
        )
    ).json()["access_token"]

    return {
        "branch_a": branch_a,
        "branch_b": branch_b,
        "mgr_a": mgr_a,
        "mgr_b": mgr_b,
        "child1": child1,
        "child2": child2,
        "group_a": group_a,
        "teacher_access": teacher_access,
        "parent_access": parent_access,
    }


async def test_parent_sees_only_own_child(client: AsyncClient) -> None:
    s = await _scenario(client)

    resp = await client.get("/api/v1/children", headers=auth_header(s["parent_access"]))
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()}
    assert ids == {s["child1"]}


async def test_parent_cannot_read_other_child(client: AsyncClient) -> None:
    s = await _scenario(client)

    own = await client.get(
        f"/api/v1/children/{s['child1']}", headers=auth_header(s["parent_access"])
    )
    assert own.status_code == 200

    other = await client.get(
        f"/api/v1/children/{s['child2']}", headers=auth_header(s["parent_access"])
    )
    assert other.status_code == 403


async def test_parent_cannot_see_medical_notes(client: AsyncClient) -> None:
    s = await _scenario(client)

    resp = await client.get(
        f"/api/v1/children/{s['child1']}", headers=auth_header(s["parent_access"])
    )
    # Tibbiy izoh faqat OWNER/MANAGER uchun ochiladi.
    assert resp.json()["medical_notes"] is None


async def test_teacher_sees_only_group_children(client: AsyncClient) -> None:
    s = await _scenario(client)

    resp = await client.get(
        "/api/v1/children", headers=auth_header(s["teacher_access"])
    )
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()}
    # child1 guruhda, child2 enrollmentsiz — teacher faqat child1 ni ko'radi.
    assert ids == {s["child1"]}


async def test_manager_cannot_create_group_in_other_branch(
    client: AsyncClient,
) -> None:
    s = await _scenario(client)

    # branch_b manageri branch_a da guruh yarata olmaydi.
    resp = await client.post(
        "/api/v1/groups",
        headers=auth_header(s["mgr_b"]),
        json={"branch_id": s["branch_a"], "name": "Ruxsatsiz", "capacity": 5},
    )
    assert resp.status_code == 403


async def test_manager_cannot_enroll_into_other_branch(client: AsyncClient) -> None:
    s = await _scenario(client)

    resp = await client.post(
        f"/api/v1/children/{s['child2']}/enrollments",
        headers=auth_header(s["mgr_b"]),
        json={
            "branch_id": s["branch_a"],
            "group_id": s["group_a"],
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    assert resp.status_code == 403
