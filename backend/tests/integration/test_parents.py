"""Ota-onalar ro'yxati integratsiya testlari."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, bot_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def test_list_parents_shows_children_and_telegram_status(
    client: AsyncClient,
) -> None:
    await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Bola Bir", "birth_date": "2021-01-01"},
        )
    ).json()["id"]

    guardian = await client.post(
        f"/api/v1/children/{child_id}/guardians",
        headers=auth_header(owner),
        json={
            "full_name": "Ota Bir",
            "phone": "+998900000020",
            "relationship_type": "FATHER",
        },
    )
    assert guardian.status_code == 201, guardian.text

    # Bog'lanmagan holatda ko'ramiz.
    resp = await client.get("/api/v1/children/parents", headers=auth_header(owner))
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["full_name"] == "Ota Bir"
    assert rows[0]["children_names"] == ["Bola Bir"]
    assert rows[0]["telegram_linked"] is False

    # Telegram bog'langach True bo'lishi kerak.
    code = (
        await client.post(
            "/api/v1/telegram/invitations",
            headers=auth_header(owner),
            json={"user_id": rows[0]["id"]},
        )
    ).json()["code"]
    await client.post(
        "/api/v1/telegram/link",
        headers=bot_header(),
        json={"code": code, "telegram_user_id": 111222},
    )

    resp2 = await client.get("/api/v1/children/parents", headers=auth_header(owner))
    assert resp2.json()[0]["telegram_linked"] is True
