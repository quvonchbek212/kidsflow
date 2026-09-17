"""Boshqaruvchi xodimga yangi parol o'rnatishi (`PATCH /users/{id}/password`).

Nega bu kerak: bog'chada ko'p tarbiyachining emaili yo'q, `/forgot-password`
esa emailga tayanadi. Parolni unutgan xodim uchun o'zi tiklash yo'li yopiq —
shuning uchun uni boshqaruvchi qayta o'rnatadi.

Chegaralar shu yerda tekshiriladi: menejer faqat o'z filialidagi xodimga
tegadi, bog'cha egasining hisobiga hech kim tegolmaydi, tarbiyachi esa bu
amalni umuman bajara olmaydi.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"
OLD_PASSWORD = "eski-parol-123"
NEW_PASSWORD = "yangi-parol-456"


async def _owner(client: AsyncClient) -> tuple[str, str]:
    setup = await complete_setup(client)
    token = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    return token, setup["branch_id"]


async def test_owner_sets_staff_password(client: AsyncClient) -> None:
    """Egasi parol o'rnatadi — xodim yangi parol bilan kiradi, eskisi ishlamaydi."""
    owner, branch_id = await _owner(client)
    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000031",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )

    resp = await client.patch(
        f"/api/v1/users/{teacher_id}/password",
        headers=auth_header(owner),
        json={"new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200, resp.text

    fresh = await client.post(
        "/api/v1/auth/login",
        json={"login": "+998900000031", "password": NEW_PASSWORD},
    )
    assert fresh.status_code == 200

    stale = await client.post(
        "/api/v1/auth/login",
        json={"login": "+998900000031", "password": OLD_PASSWORD},
    )
    assert stale.status_code == 401


async def test_password_change_closes_old_sessions(client: AsyncClient) -> None:
    """Parol almashgach eski refresh token ishlamay qoladi.

    Access token 15 daqiqada tugaydi, refresh esa 30 kun yashaydi — shuning
    uchun sessiyani yopmasa, o'g'irlangan qurilma bir oygacha ishlab turardi.
    """
    owner, branch_id = await _owner(client)
    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000032",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )
    tokens = await login(client, "+998900000032", OLD_PASSWORD)

    await client.patch(
        f"/api/v1/users/{teacher_id}/password",
        headers=auth_header(owner),
        json={"new_password": NEW_PASSWORD},
    )

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 401


async def test_password_change_clears_lockout(client: AsyncClient) -> None:
    """Bloklangan hisob parol o'rnatilgach yana ishlaydi.

    Parolni unutgan xodim odatda bir necha marta xato urinib, hisobini
    qulflab qo'ygan bo'ladi — yangi parol berish ayni shu holatni yechishi kerak.
    """
    owner, branch_id = await _owner(client)
    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000033",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"login": "+998900000033", "password": "butunlay-boshqa"},
        )
    locked = await client.post(
        "/api/v1/auth/login",
        json={"login": "+998900000033", "password": OLD_PASSWORD},
    )
    assert locked.status_code == 401

    await client.patch(
        f"/api/v1/users/{teacher_id}/password",
        headers=auth_header(owner),
        json={"new_password": NEW_PASSWORD},
    )

    unlocked = await client.post(
        "/api/v1/auth/login",
        json={"login": "+998900000033", "password": NEW_PASSWORD},
    )
    assert unlocked.status_code == 200, unlocked.text


async def test_manager_scope_for_password(client: AsyncClient) -> None:
    """Menejer o'z filialidagi xodimga parol beradi, begonasiga yo'q."""
    owner, branch_a = await _owner(client)
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Ikkinchi filial", "capacity": 20},
        )
    ).json()["id"]

    own_teacher = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000034",
        password=OLD_PASSWORD,
        branch_id=branch_a,
    )
    foreign_teacher = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000035",
        password=OLD_PASSWORD,
        branch_id=branch_b,
    )
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000036",
        password=OLD_PASSWORD,
        branch_id=branch_a,
    )
    manager = (await login(client, "+998900000036", OLD_PASSWORD))["access_token"]

    allowed = await client.patch(
        f"/api/v1/users/{own_teacher}/password",
        headers=auth_header(manager),
        json={"new_password": NEW_PASSWORD},
    )
    assert allowed.status_code == 200, allowed.text

    denied = await client.patch(
        f"/api/v1/users/{foreign_teacher}/password",
        headers=auth_header(manager),
        json={"new_password": NEW_PASSWORD},
    )
    assert denied.status_code == 403


async def test_manager_cannot_reset_owner_password(client: AsyncClient) -> None:
    """Menejer egasining parolini almashtira olmaydi.

    Aks holda u bog'cha egasini o'z hisobidan chiqarib, tizimni butunlay
    egallab olardi.
    """
    owner, branch_id = await _owner(client)
    owner_id = (await client.get("/api/v1/auth/me", headers=auth_header(owner))).json()[
        "id"
    ]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000037",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000037", OLD_PASSWORD))["access_token"]

    resp = await client.patch(
        f"/api/v1/users/{owner_id}/password",
        headers=auth_header(manager),
        json={"new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 403


async def test_teacher_cannot_set_passwords(client: AsyncClient) -> None:
    """Tarbiyachi bu amalni umuman bajara olmaydi."""
    owner, branch_id = await _owner(client)
    victim = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000038",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )
    await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000039",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )
    teacher = (await login(client, "+998900000039", OLD_PASSWORD))["access_token"]

    resp = await client.patch(
        f"/api/v1/users/{victim}/password",
        headers=auth_header(teacher),
        json={"new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 403


async def test_short_password_rejected(client: AsyncClient) -> None:
    """Juda qisqa parol qabul qilinmaydi (yaratishdagi qoida bilan bir xil)."""
    owner, branch_id = await _owner(client)
    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000040",
        password=OLD_PASSWORD,
        branch_id=branch_id,
    )

    resp = await client.patch(
        f"/api/v1/users/{teacher_id}/password",
        headers=auth_header(owner),
        json={"new_password": "qisqa"},
    )
    assert resp.status_code == 422


async def test_manager_can_change_staff_username(client: AsyncClient) -> None:
    """Menejer/egasi xodimning loginini almashtira oladi.

    Xodim loginini unutsa yoki u xato yozilgan bo'lsa, uni tuzatish kerak.
    Ilgari login o'zgarmas edi va yagona yo'l yangi hisob ochish bo'lardi.
    """
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    staff_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000055",
        password="teacher-parol-123",
        branch_id=setup["branch_id"],
    )

    resp = await client.patch(
        f"/api/v1/users/{staff_id}",
        headers=auth_header(owner),
        json={"username": "yangi.login"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == "yangi.login"

    # Yangi login bilan kirish ishlaydi.
    tokens = await login(client, "yangi.login", "teacher-parol-123")
    assert tokens["access_token"]


async def test_username_must_stay_unique(client: AsyncClient) -> None:
    """Band bo'lgan loginni boshqa xodimga berib bo'lmaydi."""
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000056",
        password="teacher-parol-123",
        branch_id=setup["branch_id"],
        username="birinchi.login",
    )
    second_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000057",
        password="teacher-parol-123",
        branch_id=setup["branch_id"],
        username="ikkinchi.login",
    )

    resp = await client.patch(
        f"/api/v1/users/{second_id}",
        headers=auth_header(owner),
        json={"username": "birinchi.login"},
    )
    assert resp.status_code == 409, resp.text
