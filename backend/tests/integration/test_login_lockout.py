"""Hisob darajasidagi login qulfi.

IP bo'yicha rate limit bir nechta IP dan sekin taqsimlangan parol taxmin
qilishni to'xtata olmaydi (hujumchi har so'rovda yangi proksi ishlatishi
mumkin). Sanoq foydalanuvchi bo'yicha ham yuritiladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.config import get_settings
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _attempt(client: AsyncClient, password: str) -> int:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": password},
    )
    return resp.status_code


async def test_account_locks_after_repeated_failures(client: AsyncClient) -> None:
    await complete_setup(client)
    limit = get_settings().login_max_failed_attempts

    for _ in range(limit):
        assert await _attempt(client, "notogri-parol") == 401

    # Limitdan keyin TO'G'RI parol ham o'tmaydi — qulf shu bilan ma'noli.
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": OWNER_PASSWORD},
    )
    assert resp.status_code == 401
    assert "bloklangan" in resp.json()["detail"].lower()


async def test_successful_login_resets_the_counter(client: AsyncClient) -> None:
    """Sanoq ketma-ket xatolarni sanaydi, umrbod jamlamaydi."""
    await complete_setup(client)
    limit = get_settings().login_max_failed_attempts

    for _ in range(limit - 1):
        assert await _attempt(client, "notogri-parol") == 401

    # To'g'ri parol — sanoq nolga tushadi.
    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    assert tokens["access_token"]

    # Yana limitdan bitta kam xato — hali qulflanmasligi kerak.
    for _ in range(limit - 1):
        assert await _attempt(client, "notogri-parol") == 401
    ok = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    assert ok["access_token"]


async def test_lock_expires_by_itself(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Qulf muddati o'tgach alohida tozalash vazifasisiz tarqaydi."""
    from app.models.user import User

    await complete_setup(client)
    limit = get_settings().login_max_failed_attempts
    for _ in range(limit):
        await _attempt(client, "notogri-parol")

    assert await _attempt(client, OWNER_PASSWORD) == 401

    # Qulf muddatini o'tmishga suramiz — vaqt kutib o'tirmaslik uchun.
    user = (
        await db_session.execute(select(User).where(User.phone == OWNER_PHONE))
    ).scalar_one()
    user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    assert tokens["access_token"]


async def test_unknown_login_does_not_reveal_account_existence(
    client: AsyncClient,
) -> None:
    """Mavjud bo'lmagan login ham xuddi shu xabarni beradi.

    Aks holda javob matni bo'yicha qaysi raqam ro'yxatda borligini aniqlash
    mumkin bo'lardi.
    """
    await complete_setup(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"login": "+998900000000", "password": "nimadir-parol"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Login yoki parol noto'g'ri."
