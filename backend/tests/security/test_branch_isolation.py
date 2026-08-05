"""Filial izolyatsiyasi xavfsizlik testlari.

Har bir branch-scoped endpoint boshqa filial ID'si bilan sinovdan o'tkaziladi
(16-bo'lim, 14-qoida). Menejer o'ziga biriktirilmagan filialga kira olmasligi kerak.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"
MANAGER_PHONE = "+998907654321"
MANAGER_PASSWORD = "manager-parol-123"


async def _owner_token(client: AsyncClient) -> tuple[str, str]:
    """Setup qiladi, branch B yaratadi va OWNER access token bilan branch A/B ni qaytaradi."""
    setup = await complete_setup(client)
    branch_a = setup["branch_id"]

    owner_tokens = await login(client, OWNER_PHONE, OWNER_PASSWORD)
    owner_access = owner_tokens["access_token"]

    branch_b_resp = await client.post(
        "/api/v1/branches",
        headers=auth_header(owner_access),
        json={"name": "Ikkinchi filial", "capacity": 30},
    )
    assert branch_b_resp.status_code == 201
    branch_b = branch_b_resp.json()["id"]

    return owner_access, branch_a, branch_b


async def _create_manager_for_branch(
    client: AsyncClient, owner_access: str, branch_id: str
) -> str:
    """OWNER filial A uchun menejer yaratadi va uning access tokenini qaytaradi."""
    resp = await client.post(
        "/api/v1/users",
        headers=auth_header(owner_access),
        json={
            "full_name": "Menejer",
            "username": f"menejer_{branch_id[:8]}",
            "phone": MANAGER_PHONE,
            "password": MANAGER_PASSWORD,
            "role": "MANAGER",
            "branch_id": branch_id,
        },
    )
    assert resp.status_code == 201, resp.text
    manager_tokens = await login(client, MANAGER_PHONE, MANAGER_PASSWORD)
    return manager_tokens["access_token"]


async def test_manager_sees_only_assigned_branch(client: AsyncClient) -> None:
    owner_access, branch_a, _branch_b = await _owner_token(client)
    manager_access = await _create_manager_for_branch(client, owner_access, branch_a)

    resp = await client.get("/api/v1/branches", headers=auth_header(manager_access))
    assert resp.status_code == 200
    branch_ids = {b["id"] for b in resp.json()}
    assert branch_ids == {branch_a}


async def test_manager_cannot_read_other_branch(client: AsyncClient) -> None:
    owner_access, branch_a, branch_b = await _owner_token(client)
    manager_access = await _create_manager_for_branch(client, owner_access, branch_a)

    # O'z filiali — ruxsat bor.
    own = await client.get(
        f"/api/v1/branches/{branch_a}", headers=auth_header(manager_access)
    )
    assert own.status_code == 200

    # Boshqa filial ID'si — 403.
    other = await client.get(
        f"/api/v1/branches/{branch_b}", headers=auth_header(manager_access)
    )
    assert other.status_code == 403


async def test_manager_cannot_create_branch(client: AsyncClient) -> None:
    owner_access, branch_a, _ = await _owner_token(client)
    manager_access = await _create_manager_for_branch(client, owner_access, branch_a)

    resp = await client.post(
        "/api/v1/branches",
        headers=auth_header(manager_access),
        json={"name": "Ruxsatsiz filial"},
    )
    assert resp.status_code == 403


async def test_owner_sees_all_branches(client: AsyncClient) -> None:
    owner_access, branch_a, branch_b = await _owner_token(client)

    resp = await client.get("/api/v1/branches", headers=auth_header(owner_access))
    assert resp.status_code == 200
    branch_ids = {b["id"] for b in resp.json()}
    assert {branch_a, branch_b} <= branch_ids


async def test_garbage_token_rejected(client: AsyncClient) -> None:
    await complete_setup(client)
    resp = await client.get("/api/v1/branches", headers=auth_header("buzuq-token"))
    assert resp.status_code == 401
