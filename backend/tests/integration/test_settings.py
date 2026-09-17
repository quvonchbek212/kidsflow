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


async def test_settings_hides_admin_fields_from_teacher(client: AsyncClient) -> None:
    """Tarbiyachiga sozlamalarning ma'muriy qismi ko'rinmaydi.

    Endpoint hammaga ochiq — yon paneldagi bog'cha nomi va sana/pul formati
    shundan olinadi. Lekin yuridik nom, manzil, telefon, hisob-faktura kuni va
    bildirishnoma sozlamalari faqat OWNER/MANAGER uchun.
    """
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    await client.patch(
        "/api/v1/settings",
        headers=auth_header(owner),
        json={
            "legal_name": "Maxfiy MCHJ",
            "address": "Maxfiy manzil",
            "phone": "+998900000000",
            "auto_invoice_day": 7,
        },
    )

    await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000077",
        password="teacher-parol-123",
        branch_id=setup["branch_id"],
    )
    teacher = (await login(client, "+998900000077", "teacher-parol-123"))[
        "access_token"
    ]

    as_owner = (await client.get("/api/v1/settings", headers=auth_header(owner))).json()
    assert as_owner["legal_name"] == "Maxfiy MCHJ"
    assert as_owner["auto_invoice_day"] == 7

    as_teacher_resp = await client.get("/api/v1/settings", headers=auth_header(teacher))
    assert as_teacher_resp.status_code == 200
    as_teacher = as_teacher_resp.json()
    # Ko'rsatish uchun kerak bo'lganlari qoladi.
    assert as_teacher["name"] == as_owner["name"]
    assert as_teacher["currency"] == as_owner["currency"]
    # Ma'muriy maydonlar berilmaydi.
    assert as_teacher["legal_name"] is None
    assert as_teacher["address"] is None
    assert as_teacher["phone"] is None
    assert as_teacher["auto_invoice_day"] is None
    assert as_teacher["notification_toggles"] == {}
