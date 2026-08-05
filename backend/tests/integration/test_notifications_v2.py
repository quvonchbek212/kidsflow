"""7-bosqich B: yangi bildirishnoma turlari, toggle va ommaviy xabar testlari."""

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
    """Manager, guruh, bola (enroll qilingan) va Telegram'da vasiy."""
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000101",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000101", "mgr-123-456"))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola Ikki", "birth_date": "2021-02-02"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": branch_id, "name": "Guruh B", "capacity": 10},
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

    parent_user_id = (
        await client.post(
            f"/api/v1/children/{child_id}/guardians",
            headers=auth_header(manager),
            json={
                "full_name": "Ona Ikki",
                "phone": "+998900000109",
                "relationship_type": "MOTHER",
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
            "telegram_user_id": 990199,
            "telegram_chat_id": 990199,
        },
    )

    return {
        "owner": owner,
        "manager": manager,
        "branch_id": branch_id,
        "group_id": group_id,
        "child_id": child_id,
    }


async def test_child_checked_in_notifies_guardian(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/attendance",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "attendance_date": "2026-09-10",
            "status": "PRESENT",
        },
    )
    assert resp.status_code in (200, 201), resp.text

    sender = FakeTelegramSender(succeed=True)
    processed, dispatched = await run_outbox(session_factory, sender)
    assert processed == 1
    assert dispatched == 1
    chat_id, text = sender.sent[0]
    assert chat_id == 990199
    assert "keldi" in text.lower()


async def test_child_sick_notifies_guardian(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/attendance",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "attendance_date": "2026-09-11",
            "status": "SICK",
        },
    )
    assert resp.status_code in (200, 201), resp.text

    sender = FakeTelegramSender(succeed=True)
    _, dispatched = await run_outbox(session_factory, sender)
    assert dispatched == 1
    _, text = sender.sent[0]
    assert "kasal" in text.lower()


async def test_disabled_notification_type_is_silently_skipped(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    toggle = await client.patch(
        "/api/v1/settings",
        headers=auth_header(s["owner"]),
        json={"notification_toggles": {"CHILD_SICK": False}},
    )
    assert toggle.status_code == 200, toggle.text

    resp = await client.post(
        "/api/v1/attendance",
        headers=auth_header(s["manager"]),
        json={
            "child_id": s["child_id"],
            "attendance_date": "2026-09-12",
            "status": "SICK",
        },
    )
    assert resp.status_code in (200, 201), resp.text

    sender = FakeTelegramSender(succeed=True)
    processed, dispatched = await run_outbox(session_factory, sender)
    assert processed == 1  # hodisa PROCESSED bo'ladi
    assert dispatched == 0  # ammo Notification yaratilmagan — hech narsa yuborilmadi
    assert sender.sent == []


async def test_broadcast_reaches_connected_guardians(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/messages/broadcast",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "audience": "all",
            "text": "Ertaga bayram tadbiri bo'ladi.",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["queued_count"] == 1

    sender = FakeTelegramSender(succeed=True)
    _, dispatched = await run_outbox(session_factory, sender)
    assert dispatched == 1
    chat_id, text = sender.sent[0]
    assert chat_id == 990199
    assert "bayram" in text.lower()


async def test_broadcast_to_group_requires_group_id(client: AsyncClient) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/messages/broadcast",
        headers=auth_header(s["manager"]),
        json={"branch_id": s["branch_id"], "audience": "group", "text": "Salom"},
    )
    assert resp.status_code == 403


async def test_broadcast_to_group_targets_only_group_members(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/messages/broadcast",
        headers=auth_header(s["manager"]),
        json={
            "branch_id": s["branch_id"],
            "audience": "group",
            "group_id": s["group_id"],
            "text": "Guruh xabari",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["queued_count"] == 1


async def test_messaging_stats(client: AsyncClient) -> None:
    s = await _scenario(client)
    resp = await client.get(
        "/api/v1/messages/stats",
        headers=auth_header(s["manager"]),
        params={"branch_id": s["branch_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["connected_families"] == 1
    assert body["sent_this_month"] == 0
