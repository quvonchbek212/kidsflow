"""Bog'cha sozlamalari integratsiya testlari (7-bosqich B)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def test_get_settings_after_setup(client: AsyncClient) -> None:
    await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    resp = await client.get("/api/v1/settings", headers=auth_header(owner))
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Test bog'cha"
    assert body["hours_text"] is None
    assert body["notification_toggles"] == {}


async def test_owner_can_update_settings(client: AsyncClient) -> None:
    await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    resp = await client.patch(
        "/api/v1/settings",
        headers=auth_header(owner),
        json={
            "address": "Toshkent sh., Yunusobod",
            "hours_text": "07:30 - 18:30",
            "auto_invoice_day": 5,
            "notification_toggles": {"CHILD_SICK": False},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["address"] == "Toshkent sh., Yunusobod"
    assert body["hours_text"] == "07:30 - 18:30"
    assert body["auto_invoice_day"] == 5
    assert body["notification_toggles"] == {"CHILD_SICK": False}

    # Qisman merge — boshqa kalitni qo'shsak, avvalgisi saqlanadi.
    resp2 = await client.patch(
        "/api/v1/settings",
        headers=auth_header(owner),
        json={"notification_toggles": {"DEBT_WARNING": False}},
    )
    assert resp2.json()["notification_toggles"] == {
        "CHILD_SICK": False,
        "DEBT_WARNING": False,
    }


async def test_manager_cannot_update_settings(client: AsyncClient) -> None:
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000060",
        password="manager-parol-1",
        branch_id=setup["branch_id"],
    )
    manager = (await login(client, "+998900000060", "manager-parol-1"))["access_token"]
    resp = await client.patch(
        "/api/v1/settings",
        headers=auth_header(manager),
        json={"address": "Boshqa"},
    )
    assert resp.status_code == 403
