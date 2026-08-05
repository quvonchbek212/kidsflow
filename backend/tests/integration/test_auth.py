"""Login, refresh va me oqimi uchun integratsiya testlari (11-bo'lim)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import FakeEmailSender, auth_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_USERNAME = "egasi"
OWNER_PHONE = "+998901112233"
OWNER_EMAIL = "egasi@example.com"
OWNER_PASSWORD = "owner-parol-123"


async def test_login_success_returns_tokens(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0


async def test_login_wrong_password_rejected(client: AsyncClient) -> None:
    await complete_setup(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": "noto'g'ri"},
    )
    assert response.status_code == 401


async def test_me_returns_owner_role(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    response = await client.get(
        "/api/v1/auth/me", headers=auth_header(tokens["access_token"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == OWNER_PHONE
    assert body["roles"][0]["role"] == "OWNER"


async def test_me_requires_token(client: AsyncClient) -> None:
    await complete_setup(client)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_rotation_invalidates_old_token(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    old_refresh = tokens["refresh_token"]

    # Birinchi refresh muvaffaqiyatli.
    first = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert first.status_code == 200

    # Eski refresh token endi ishlamaydi (rotation).
    second = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert second.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await complete_setup(client)
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)

    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_resp.status_code == 204

    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401


async def test_login_with_username_success(client: AsyncClient) -> None:
    await complete_setup(client, owner_username=OWNER_USERNAME)
    tokens = await login(client, OWNER_USERNAME, OWNER_PASSWORD)
    assert tokens["access_token"]


async def test_me_returns_username(client: AsyncClient) -> None:
    await complete_setup(client, owner_username=OWNER_USERNAME)
    tokens = await login(client, OWNER_USERNAME, OWNER_PASSWORD)
    response = await client.get(
        "/api/v1/auth/me", headers=auth_header(tokens["access_token"])
    )
    assert response.json()["username"] == OWNER_USERNAME


async def test_forgot_password_sends_reset_email(
    client: AsyncClient, monkeypatch
) -> None:
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_email=OWNER_EMAIL)

    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": OWNER_EMAIL}
    )
    assert response.status_code == 204
    assert len(fake.sent) == 1
    to, subject, body = fake.sent[0]
    assert to == OWNER_EMAIL
    assert "reset-password?token=" in body


async def test_forgot_password_unknown_email_is_silent(
    client: AsyncClient, monkeypatch
) -> None:
    """Xavfsizlik: mavjud bo'lmagan email uchun ham 204 qaytadi, xat yuborilmaydi."""
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_email=OWNER_EMAIL)

    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "noone@example.com"}
    )
    assert response.status_code == 204
    assert fake.sent == []


async def test_reset_password_with_token_changes_password(
    client: AsyncClient, monkeypatch
) -> None:
    fake = FakeEmailSender()
    monkeypatch.setattr(
        "app.services.auth_service.get_default_email_sender", lambda: fake
    )
    await complete_setup(client, owner_username=OWNER_USERNAME, owner_email=OWNER_EMAIL)
    await client.post("/api/v1/auth/forgot-password", json={"email": OWNER_EMAIL})

    body = fake.sent[0][2]
    token = body.split("token=")[1].split()[0].strip()

    new_password = "yangi-parol-456"
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_resp.status_code == 204

    # Eski parol endi ishlamaydi.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_USERNAME, "password": OWNER_PASSWORD},
    )
    assert old_login.status_code == 401

    # Yangi parol ishlaydi.
    new_login = await login(client, OWNER_USERNAME, new_password)
    assert new_login["access_token"]

    # Token bir martalik — qayta ishlatib bo'lmaydi.
    reuse = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "yana-boshqa-789"},
    )
    assert reuse.status_code == 401
