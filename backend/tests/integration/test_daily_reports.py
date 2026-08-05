"""Kunlik hisobot va outbox→worker→bildirishnoma oqimi (4.4, 9-bo'lim)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    FakeTelegramSender,
    auth_header,
    bot_header,
    complete_setup,
    create_staff,
    login,
    run_outbox,
)

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _scenario(client: AsyncClient) -> dict:
    """Teacher guruhga biriktirilgan, bola enroll qilingan, parent Telegram'da."""
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

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola Bir", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": branch_id, "name": "Guruh A", "capacity": 10},
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

    teacher_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000003",
        password="teacher-123",
        branch_id=branch_id,
    )
    await client.post(
        f"/api/v1/groups/{group_id}/teachers",
        headers=auth_header(manager),
        json={"teacher_user_id": teacher_id},
    )
    teacher = (await login(client, "+998900000003", "teacher-123"))["access_token"]

    # Parent — bildirishnoma olish uchun Telegram chat bog'lanadi.
    parent_user_id = (
        await client.post(
            f"/api/v1/children/{child_id}/guardians",
            headers=auth_header(manager),
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
            headers=auth_header(manager),
            json={"user_id": parent_user_id},
        )
    ).json()["code"]
    await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={
            "code": code,
            "telegram_user_id": 990099,
            "telegram_chat_id": 990099,
        },
    )
    parent = (
        await client.post(
            "/api/v1/telegram/session",
            headers=bot_header(),
            json={"telegram_user_id": 990099},
        )
    ).json()["access_token"]

    return {
        "manager": manager,
        "teacher": teacher,
        "parent": parent,
        "child_id": child_id,
    }


async def _create_report(
    client: AsyncClient, teacher: str, child_id: str, report_date: str
) -> str:
    resp = await client.post(
        "/api/v1/daily-reports",
        headers=auth_header(teacher),
        json={
            "child_id": child_id,
            "report_date": report_date,
            "meal_status": "ATE_WELL",
            "mood": "HAPPY",
            "activities_text": "Rasm chizdi, o'ynadi.",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_report_create_and_publish(client: AsyncClient) -> None:
    s = await _scenario(client)
    report_id = await _create_report(client, s["teacher"], s["child_id"], "2026-09-02")

    pub = await client.post(
        f"/api/v1/daily-reports/{report_id}/publish",
        headers=auth_header(s["teacher"]),
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["is_published"] is True


async def test_publish_creates_outbox_and_worker_notifies(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    report_id = await _create_report(client, s["teacher"], s["child_id"], "2026-09-03")
    await client.post(
        f"/api/v1/daily-reports/{report_id}/publish",
        headers=auth_header(s["teacher"]),
    )

    # Worker outbox'ni qayta ishlaydi → bildirishnoma → Telegram (soxta yuboruvchi).
    sender = FakeTelegramSender(succeed=True)
    processed, dispatched = await run_outbox(session_factory, sender)

    assert processed == 1  # bitta DAILY_REPORT_PUBLISHED hodisasi
    assert dispatched == 1  # bitta bildirishnoma yuborildi
    assert len(sender.sent) == 1
    chat_id, text = sender.sent[0]
    assert chat_id == 990099
    assert "hisobot" in text.lower()


async def test_parent_sees_only_published_reports(client: AsyncClient) -> None:
    s = await _scenario(client)

    # Published hisobot.
    published = await _create_report(client, s["teacher"], s["child_id"], "2026-09-04")
    await client.post(
        f"/api/v1/daily-reports/{published}/publish",
        headers=auth_header(s["teacher"]),
    )
    # Draft (e'lon qilinmagan) hisobot.
    await _create_report(client, s["teacher"], s["child_id"], "2026-09-05")

    resp = await client.get(
        f"/api/v1/children/{s['child_id']}/daily-reports",
        headers=auth_header(s["parent"]),
    )
    assert resp.status_code == 200
    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["id"] == published
    assert all(r["is_published"] for r in reports)


async def test_teacher_sees_draft_but_parent_cannot(client: AsyncClient) -> None:
    s = await _scenario(client)
    draft = await _create_report(client, s["teacher"], s["child_id"], "2026-09-06")

    # Teacher qoralamani ko'radi.
    teacher_view = await client.get(
        f"/api/v1/daily-reports/{draft}", headers=auth_header(s["teacher"])
    )
    assert teacher_view.status_code == 200

    # Parent e'lon qilinmagan hisobotni ko'ra olmaydi.
    parent_view = await client.get(
        f"/api/v1/daily-reports/{draft}", headers=auth_header(s["parent"])
    )
    assert parent_view.status_code == 403
