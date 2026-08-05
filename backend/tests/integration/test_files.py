"""Fayl yuklash/yuklab olish va kirish nazorati (11-bo'lim)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TINY_PNG,
    auth_header,
    bot_header,
    complete_setup,
    create_staff,
    login,
)

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _link_parent(
    client: AsyncClient,
    manager: str,
    child_id: str,
    *,
    phone: str,
    tg_id: int,
) -> str:
    parent_user_id = (
        await client.post(
            f"/api/v1/children/{child_id}/guardians",
            headers=auth_header(manager),
            json={"full_name": "Ota", "phone": phone, "relationship_type": "FATHER"},
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
        json={"code": code, "telegram_user_id": tg_id, "telegram_chat_id": tg_id},
    )
    return (
        await client.post(
            "/api/v1/telegram/session",
            headers=bot_header(),
            json={"telegram_user_id": tg_id},
        )
    ).json()["access_token"]


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

    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000003",
        password="teacher-123",
        branch_id=branch_id,
    )

    async def _enroll_child(name: str) -> tuple[str, str]:
        child_id = (
            await client.post(
                "/api/v1/children",
                headers=auth_header(manager),
                json={"full_name": name, "birth_date": "2021-01-01"},
            )
        ).json()["id"]
        group_id = (
            await client.post(
                "/api/v1/groups",
                headers=auth_header(manager),
                json={"branch_id": branch_id, "name": f"Guruh {name}", "capacity": 10},
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
        await client.post(
            f"/api/v1/groups/{group_id}/teachers",
            headers=auth_header(manager),
            json={"teacher_user_id": teacher_id},
        )
        return child_id, group_id

    child1, _ = await _enroll_child("Bir")
    child2, _ = await _enroll_child("Ikki")
    teacher = (await login(client, "+998900000003", "teacher-123"))["access_token"]

    parent1 = await _link_parent(
        client, manager, child1, phone="+998900000009", tg_id=111111
    )
    parent2 = await _link_parent(
        client, manager, child2, phone="+998900000010", tg_id=222222
    )
    return {
        "manager": manager,
        "teacher": teacher,
        "parent1": parent1,
        "parent2": parent2,
        "child1": child1,
    }


async def test_upload_and_download_by_uploader(client: AsyncClient) -> None:
    s = await _scenario(client)
    up = await client.post(
        "/api/v1/files",
        headers=auth_header(s["teacher"]),
        files={"upload": ("photo.png", TINY_PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    file_id = up.json()["id"]

    down = await client.get(
        f"/api/v1/files/{file_id}", headers=auth_header(s["teacher"])
    )
    assert down.status_code == 200
    assert down.content == TINY_PNG


async def test_upload_invalid_type_rejected(client: AsyncClient) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/files",
        headers=auth_header(s["teacher"]),
        files={"upload": ("virus.exe", b"MZfake", "application/x-msdownload")},
    )
    assert resp.status_code == 400


async def test_parent_can_download_file_on_own_child_report(
    client: AsyncClient,
) -> None:
    s = await _scenario(client)
    file_id = (
        await client.post(
            "/api/v1/files",
            headers=auth_header(s["teacher"]),
            files={"upload": ("photo.png", TINY_PNG, "image/png")},
        )
    ).json()["id"]

    report_id = (
        await client.post(
            "/api/v1/daily-reports",
            headers=auth_header(s["teacher"]),
            json={
                "child_id": s["child1"],
                "report_date": "2026-09-02",
                "activities_text": "O'ynadi",
                "file_ids": [file_id],
            },
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/daily-reports/{report_id}/publish",
        headers=auth_header(s["teacher"]),
    )

    # child1 vasiysi faylni yuklab oladi.
    own = await client.get(
        f"/api/v1/files/{file_id}", headers=auth_header(s["parent1"])
    )
    assert own.status_code == 200

    # Boshqa bola vasiysi (parent2) — kira olmaydi.
    other = await client.get(
        f"/api/v1/files/{file_id}", headers=auth_header(s["parent2"])
    )
    assert other.status_code == 403


async def test_download_requires_auth(client: AsyncClient) -> None:
    s = await _scenario(client)
    file_id = (
        await client.post(
            "/api/v1/files",
            headers=auth_header(s["teacher"]),
            files={"upload": ("photo.png", TINY_PNG, "image/png")},
        )
    ).json()["id"]

    resp = await client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 401
