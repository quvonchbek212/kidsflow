"""2-bosqich asosiy oqimi uchun integratsiya testlari.

Setup → manager → bola → vasiy → guruh → enrollment → tarbiyachi → davomat →
Telegram bog'lash.
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
MANAGER_PHONE = "+998907654321"
MANAGER_PASSWORD = "manager-parol-123"


async def _manager_context(client: AsyncClient) -> tuple[str, str, str]:
    """Setup + manager. (owner_access, manager_access, branch_id)."""
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner_access = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner_access,
        role="MANAGER",
        phone=MANAGER_PHONE,
        password=MANAGER_PASSWORD,
        branch_id=branch_id,
    )
    manager_access = (await login(client, MANAGER_PHONE, MANAGER_PASSWORD))[
        "access_token"
    ]
    return owner_access, manager_access, branch_id


async def _create_child(client: AsyncClient, manager_access: str) -> str:
    resp = await client.post(
        "/api/v1/children",
        headers=auth_header(manager_access),
        json={
            "full_name": "Ali Valiyev",
            "birth_date": "2021-05-10",
            "gender": "MALE",
            "medical_notes": "Allergiya: yo'q",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_group(
    client: AsyncClient, manager_access: str, branch_id: str
) -> str:
    resp = await client.post(
        "/api/v1/groups",
        headers=auth_header(manager_access),
        json={"branch_id": branch_id, "name": "Quyoncha", "capacity": 15},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_manager_creates_child_with_medical_notes(client: AsyncClient) -> None:
    _owner, manager_access, _branch = await _manager_context(client)
    child_id = await _create_child(client, manager_access)

    resp = await client.get(
        f"/api/v1/children/{child_id}", headers=auth_header(manager_access)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Ali Valiyev"
    # Manager tibbiy izohni ochiq ko'radi.
    assert body["medical_notes"] == "Allergiya: yo'q"


async def test_add_guardian_returns_parent(client: AsyncClient) -> None:
    _owner, manager_access, _branch = await _manager_context(client)
    child_id = await _create_child(client, manager_access)

    resp = await client.post(
        f"/api/v1/children/{child_id}/guardians",
        headers=auth_header(manager_access),
        json={
            "full_name": "Vali Aliyev",
            "phone": "+998935556677",
            "relationship_type": "FATHER",
            "is_primary": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["relationship_type"] == "FATHER"

    # Bola javobida vasiy ko'rinadi.
    detail = await client.get(
        f"/api/v1/children/{child_id}", headers=auth_header(manager_access)
    )
    guardians = detail.json()["guardians"]
    assert len(guardians) == 1
    assert guardians[0]["full_name"] == "Vali Aliyev"


async def test_enroll_child_and_one_active_rule(client: AsyncClient) -> None:
    _owner, manager_access, branch_id = await _manager_context(client)
    child_id = await _create_child(client, manager_access)
    group_id = await _create_group(client, manager_access, branch_id)

    enroll = await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(manager_access),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    assert enroll.status_code == 201, enroll.text

    # Ikkinchi ACTIVE enrollment — 409 (bir bolada bitta faol enrollment).
    second = await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(manager_access),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-10-01",
            "status": "ACTIVE",
        },
    )
    assert second.status_code == 409


async def test_teacher_marks_attendance(client: AsyncClient) -> None:
    owner_access, manager_access, branch_id = await _manager_context(client)
    child_id = await _create_child(client, manager_access)
    group_id = await _create_group(client, manager_access, branch_id)

    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(manager_access),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )

    teacher_id = await create_staff(
        client,
        owner_access,
        role="TEACHER",
        phone="+998931112200",
        password="teacher-parol-123",
        branch_id=branch_id,
    )
    # Tarbiyachini guruhga biriktiramiz.
    assign = await client.post(
        f"/api/v1/groups/{group_id}/teachers",
        headers=auth_header(manager_access),
        json={"teacher_user_id": teacher_id, "is_primary": True},
    )
    assert assign.status_code == 201, assign.text

    teacher_access = (await login(client, "+998931112200", "teacher-parol-123"))[
        "access_token"
    ]
    mark = await client.post(
        "/api/v1/attendance",
        headers=auth_header(teacher_access),
        json={
            "child_id": child_id,
            "attendance_date": "2026-09-02",
            "status": "PRESENT",
        },
    )
    assert mark.status_code == 201, mark.text
    assert mark.json()["status"] == "PRESENT"


async def test_telegram_invitation_and_link_flow(client: AsyncClient) -> None:
    _owner, manager_access, _branch = await _manager_context(client)
    child_id = await _create_child(client, manager_access)

    guardian = await client.post(
        f"/api/v1/children/{child_id}/guardians",
        headers=auth_header(manager_access),
        json={
            "full_name": "Ona Aliyeva",
            "phone": "+998935550011",
            "relationship_type": "MOTHER",
        },
    )
    parent_user_id = guardian.json()["guardian_user_id"]

    # Manager taklif kodini yaratadi.
    inv = await client.post(
        "/api/v1/telegram/invitations",
        headers=auth_header(manager_access),
        json={"user_id": parent_user_id},
    )
    assert inv.status_code == 200, inv.text
    code = inv.json()["code"]

    # Bot kod orqali hisobni bog'laydi.
    link = await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={"code": code, "telegram_user_id": 555001, "telegram_chat_id": 555001},
    )
    assert link.status_code == 200, link.text
    assert link.json()["linked"] is True

    # Kodni qayta ishlatib bo'lmaydi (bir martalik).
    reuse = await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={"code": code, "telegram_user_id": 555001},
    )
    assert reuse.status_code == 404


async def test_telegram_link_requires_bot_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/telegram/link",
        json={"code": "x", "telegram_user_id": 1},
    )
    # Bot token yo'q — 401/403 (header majburiy).
    assert resp.status_code in (401, 403, 422)
