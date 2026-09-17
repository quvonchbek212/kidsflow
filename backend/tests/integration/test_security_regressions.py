"""Xavfsizlik auditida topilgan zaifliklar qaytib kelmasligi uchun testlar.

Har bir test avval ZAIFLIK MAVJUDLIGINI isbotlagan hujum ssenariysini takrorlaydi
va endi u rad etilishini tekshiradi.
"""

from __future__ import annotations

import pytest
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy import select

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


async def _two_branches(client: AsyncClient) -> dict:
    """A va B filial, A filial menejeri, B filialda bola (tibbiy izoh bilan)."""
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    branch_a = setup["branch_id"]
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "B filial", "capacity": 30},
        )
    ).json()["id"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000701",
        password="manager-a-parol",
        branch_id=branch_a,
    )
    manager_a = (await login(client, "+998900000701", "manager-a-parol"))[
        "access_token"
    ]
    group_a = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(owner),
            json={"branch_id": branch_a, "name": "A guruh", "capacity": 10},
        )
    ).json()["id"]
    group_b = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(owner),
            json={"branch_id": branch_b, "name": "B guruh", "capacity": 10},
        )
    ).json()["id"]
    child_b = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={
                "full_name": "B filial bolasi",
                "birth_date": "2021-02-02",
                "medical_notes": "Yong'oqqa allergiya",
            },
        )
    ).json()["id"]
    enroll = await client.post(
        f"/api/v1/children/{child_b}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_b,
            "group_id": group_b,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    assert enroll.status_code == 201, enroll.text
    return {
        "owner": owner,
        "manager_a": manager_a,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "group_a": group_a,
        "child_b": child_b,
    }


# --- OWNER huquqini egallash zanjiri ------------------------------------------


async def test_staff_phone_cannot_be_attached_as_guardian(client: AsyncClient) -> None:
    s = await _two_branches(client)
    resp = await client.post(
        f"/api/v1/children/{s['child_b']}/guardians",
        headers=auth_header(s["owner"]),
        json={
            "full_name": "Soxta vasiy",
            "phone": OWNER_PHONE,
            "relationship_type": "OTHER",
        },
    )
    assert resp.status_code == 409, resp.text


async def test_invitation_is_refused_for_staff_account(client: AsyncClient) -> None:
    s = await _two_branches(client)
    owner_id = (
        await client.get("/api/v1/auth/me", headers=auth_header(s["owner"]))
    ).json()["id"]
    resp = await client.post(
        "/api/v1/telegram/invitations",
        headers=auth_header(s["owner"]),
        json={"user_id": owner_id},
    )
    assert resp.status_code == 409, resp.text


async def test_telegram_session_is_refused_for_staff_account(
    client: AsyncClient, session_factory
) -> None:
    await _two_branches(client)
    # Avvalgi zaiflik orqali egasining hisobiga Telegram bog'lanib qolgan holat.
    async with session_factory() as session:
        owner = (
            await session.execute(select(User).where(User.phone == OWNER_PHONE))
        ).scalar_one()
        owner.telegram_user_id = 555000111
        await session.commit()

    resp = await client.post(
        "/api/v1/telegram/session",
        headers=bot_header(),
        json={"telegram_user_id": 555000111},
    )
    assert resp.status_code == 401, resp.text


async def test_manager_cannot_invite_parent_of_other_branch(
    client: AsyncClient,
) -> None:
    s = await _two_branches(client)
    guardian = await client.post(
        f"/api/v1/children/{s['child_b']}/guardians",
        headers=auth_header(s["owner"]),
        json={
            "full_name": "B ota-ona",
            "phone": "+998900000799",
            "relationship_type": "MOTHER",
        },
    )
    assert guardian.status_code == 201, guardian.text

    resp = await client.post(
        "/api/v1/telegram/invitations",
        headers=auth_header(s["manager_a"]),
        json={"user_id": guardian.json()["guardian_user_id"]},
    )
    assert resp.status_code == 403, resp.text


# --- Filiallararo bola ma'lumotlari -------------------------------------------


async def test_manager_cannot_read_or_edit_other_branch_child(
    client: AsyncClient,
) -> None:
    s = await _two_branches(client)
    headers = auth_header(s["manager_a"])

    listed = await client.get("/api/v1/children", headers=headers)
    assert listed.status_code == 200
    assert s["child_b"] not in {c["id"] for c in listed.json()}

    detail = await client.get(f"/api/v1/children/{s['child_b']}", headers=headers)
    assert detail.status_code == 403

    patched = await client.patch(
        f"/api/v1/children/{s['child_b']}",
        headers=headers,
        json={"is_active": False},
    )
    assert patched.status_code == 403

    guardian = await client.post(
        f"/api/v1/children/{s['child_b']}/guardians",
        headers=headers,
        json={
            "full_name": "Kimdir",
            "phone": "+998900000798",
            "relationship_type": "OTHER",
        },
    )
    assert guardian.status_code == 403

    invoices = await client.get(
        f"/api/v1/children/{s['child_b']}/invoices", headers=headers
    )
    assert invoices.status_code == 403


async def test_manager_parent_list_is_limited_to_own_branches(
    client: AsyncClient,
) -> None:
    s = await _two_branches(client)
    await client.post(
        f"/api/v1/children/{s['child_b']}/guardians",
        headers=auth_header(s["owner"]),
        json={
            "full_name": "B filial ota-onasi",
            "phone": "+998900000797",
            "relationship_type": "FATHER",
        },
    )
    resp = await client.get(
        "/api/v1/children/parents", headers=auth_header(s["manager_a"])
    )
    assert resp.status_code == 200
    assert "B filial ota-onasi" not in {p["full_name"] for p in resp.json()}


async def test_manager_still_manages_own_new_child(client: AsyncClient) -> None:
    """Oddiy oqim buzilmagan: yangi bola → vasiy → o'z filialiga yozish."""
    s = await _two_branches(client)
    headers = auth_header(s["manager_a"])
    child = await client.post(
        "/api/v1/children",
        headers=headers,
        json={"full_name": "Yangi bola", "birth_date": "2022-03-03"},
    )
    assert child.status_code == 201, child.text
    child_id = child.json()["id"]

    enroll = await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=headers,
        json={
            "branch_id": s["branch_a"],
            "group_id": s["group_a"],
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    assert enroll.status_code == 201, enroll.text

    guardian = await client.post(
        f"/api/v1/children/{child_id}/guardians",
        headers=headers,
        json={
            "full_name": "Yangi ota-ona",
            "phone": "+998900000796",
            "relationship_type": "MOTHER",
        },
    )
    assert guardian.status_code == 201, guardian.text

    invite = await client.post(
        "/api/v1/telegram/invitations",
        headers=headers,
        json={"user_id": guardian.json()["guardian_user_id"]},
    )
    assert invite.status_code == 200, invite.text

    detail = await client.get(f"/api/v1/children/{child_id}", headers=headers)
    assert detail.status_code == 200


# --- Oylik va avans ------------------------------------------------------------


async def test_manager_cannot_touch_other_branch_payroll(client: AsyncClient) -> None:
    s = await _two_branches(client)
    teacher_b = await create_staff(
        client,
        s["owner"],
        role="TEACHER",
        phone="+998900000702",
        password="teacher-b-parol",
        branch_id=s["branch_b"],
    )
    await client.patch(
        f"/api/v1/users/{teacher_b}",
        headers=auth_header(s["owner"]),
        json={"monthly_salary": "3000000"},
    )
    headers = auth_header(s["manager_a"])

    runs = await client.get(
        "/api/v1/payroll/runs", headers=headers, params={"user_id": teacher_b}
    )
    assert runs.status_code == 403
    advances = await client.get(
        "/api/v1/payroll/advances", headers=headers, params={"user_id": teacher_b}
    )
    assert advances.status_code == 403

    foreign_run = await client.post(
        "/api/v1/payroll/runs",
        headers=headers,
        json={
            "branch_id": s["branch_a"],
            "user_id": teacher_b,
            "period": "2026-10-01",
            "paid_at": "2026-10-30T10:00:00Z",
        },
    )
    assert foreign_run.status_code == 409, foreign_run.text
    foreign_advance = await client.post(
        "/api/v1/payroll/advances",
        headers=headers,
        json={
            "branch_id": s["branch_a"],
            "user_id": teacher_b,
            "amount": "100000",
            "paid_at": "2026-10-10T10:00:00Z",
        },
    )
    assert foreign_advance.status_code == 409, foreign_advance.text
