"""Ota-ona ↔ xodim yozishmalari va filial kesimidagi bildirishnoma kalitlari.

Botdagi "Savol yozish" oqimi shu endpointlar ustida quriladi: ota-ona
`/telegram/session` orqali o'z tokenini oladi va `/messages/from-parent` ga
yozadi; xodim esa veb-saytdan javob beradi va javob Telegramga ketadi.
"""

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
    """Filial, manager, bola, Telegram'ga ulangan ota-ona va uning tokeni."""
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000301",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000301", "mgr-123-456"))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola Savol", "birth_date": "2021-04-04"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": branch_id, "name": "Guruh S", "capacity": 10},
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
                "full_name": "Ona Savol",
                "phone": "+998900000309",
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
        json={"code": code, "telegram_user_id": 771177, "telegram_chat_id": 771177},
    )
    parent_token = (
        await client.post(
            "/api/v1/telegram/session",
            headers=bot_header(),
            json={"telegram_user_id": 771177},
        )
    ).json()["access_token"]

    return {
        "owner": owner,
        "manager": manager,
        "branch_id": branch_id,
        "child_id": child_id,
        "parent_user_id": parent_user_id,
        "parent_token": parent_token,
    }


async def test_parent_question_appears_in_staff_threads(client: AsyncClient) -> None:
    s = await _scenario(client)

    sent = await client.post(
        "/api/v1/messages/from-parent",
        headers=auth_header(s["parent_token"]),
        json={"text": "Ertaga bog'cha ishlaydimi?"},
    )
    assert sent.status_code == 201, sent.text

    threads = await client.get(
        f"/api/v1/messages/threads?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert threads.status_code == 200, threads.text
    body = threads.json()
    assert len(body) == 1
    assert body[0]["guardian_user_id"] == s["parent_user_id"]
    assert body[0]["last_message_text"] == "Ertaga bog'cha ishlaydimi?"
    assert body[0]["unread_count"] == 1
    assert "Bola Savol" in body[0]["children"]


async def test_unread_count_clears_when_thread_opened(client: AsyncClient) -> None:
    s = await _scenario(client)
    await client.post(
        "/api/v1/messages/from-parent",
        headers=auth_header(s["parent_token"]),
        json={"text": "Savol"},
    )

    before = await client.get(
        f"/api/v1/messages/unread-count?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert before.json()["unread_count"] == 1

    opened = await client.get(
        f"/api/v1/messages/threads/{s['parent_user_id']}?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert opened.status_code == 200, opened.text
    assert [m["direction"] for m in opened.json()] == ["IN"]

    after = await client.get(
        f"/api/v1/messages/unread-count?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert after.json()["unread_count"] == 0


async def test_staff_reply_reaches_parent_telegram(
    client: AsyncClient, session_factory
) -> None:
    s = await _scenario(client)
    await client.post(
        "/api/v1/messages/from-parent",
        headers=auth_header(s["parent_token"]),
        json={"text": "Savol"},
    )

    reply = await client.post(
        f"/api/v1/messages/threads/{s['parent_user_id']}/reply"
        f"?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
        json={"text": "Ha, ishlaymiz."},
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["direction"] == "OUT"

    # Javob yozishmada ham, Telegram navbatida ham bo'lishi kerak.
    thread = await client.get(
        f"/api/v1/messages/threads/{s['parent_user_id']}?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert [m["direction"] for m in thread.json()] == ["IN", "OUT"]

    sender = FakeTelegramSender(succeed=True)
    await run_outbox(session_factory, sender)
    assert any("Ha, ishlaymiz." in text for _, text in sender.sent)


async def test_other_branch_manager_cannot_read_thread(client: AsyncClient) -> None:
    """Yozishma filialga bog'langan — boshqa filial menejeri ko'ra olmaydi."""
    s = await _scenario(client)
    await client.post(
        "/api/v1/messages/from-parent",
        headers=auth_header(s["parent_token"]),
        json={"text": "Savol"},
    )

    other_branch = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(s["owner"]),
            json={"name": "Filial B"},
        )
    ).json()["id"]
    await create_staff(
        client,
        s["owner"],
        role="MANAGER",
        phone="+998900000302",
        password="mgr-999-888",
        branch_id=other_branch,
    )
    other_manager = (await login(client, "+998900000302", "mgr-999-888"))[
        "access_token"
    ]

    denied = await client.get(
        f"/api/v1/messages/threads?branch_id={s['branch_id']}",
        headers=auth_header(other_manager),
    )
    assert denied.status_code == 403, denied.text


async def test_notification_toggles_are_per_branch(client: AsyncClient) -> None:
    """Bir filialda o'chirilgan tur boshqa filialda yoqiq qoladi."""
    s = await _scenario(client)
    other_branch = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(s["owner"]),
            json={"name": "Filial C"},
        )
    ).json()["id"]

    off = await client.patch(
        f"/api/v1/messages/settings?branch_id={s['branch_id']}",
        headers=auth_header(s["owner"]),
        json={"toggles": {"CHILD_SICK": False}},
    )
    assert off.status_code == 200, off.text
    assert off.json()["toggles"]["CHILD_SICK"] is False

    other = await client.get(
        f"/api/v1/messages/settings?branch_id={other_branch}",
        headers=auth_header(s["owner"]),
    )
    assert other.status_code == 200, other.text
    # Ikkinchi filialda kalit umuman yo'q — ya'ni yoqiq (standart).
    assert other.json()["toggles"].get("CHILD_SICK") is None


async def test_reminder_days_are_configurable_per_branch(client: AsyncClient) -> None:
    s = await _scenario(client)
    updated = await client.patch(
        f"/api/v1/messages/settings?branch_id={s['branch_id']}",
        headers=auth_header(s["owner"]),
        json={"payment_reminder_days_before": 3, "debt_warning_days_late": 20},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["payment_reminder_days_before"] == 3
    assert updated.json()["debt_warning_days_late"] == 20

    # Standart qiymatlar sozlanmagan filialda saqlanadi.
    fresh = await client.get(
        f"/api/v1/messages/settings?branch_id={s['branch_id']}",
        headers=auth_header(s["manager"]),
    )
    assert fresh.json()["payment_reminder_days_before"] == 3
