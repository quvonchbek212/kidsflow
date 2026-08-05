"""Setup oqimi uchun integratsiya testlari (4.1-bo'lim)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_SETUP_TOKEN, complete_setup

pytestmark = pytest.mark.asyncio


async def test_setup_creates_owner_and_branch(client: AsyncClient) -> None:
    result = await complete_setup(client)

    assert "settings_id" in result
    assert "branch_id" in result
    assert "owner_id" in result


async def test_setup_rejects_wrong_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/setup",
        headers={"X-Setup-Token": "noto'g'ri-token"},
        json={
            "kindergarten": {"name": "B"},
            "branch": {"name": "F"},
            "owner": {
                "full_name": "E",
                "username": "eee",
                "phone": "+998901112233",
                "password": "parol1234",
            },
        },
    )
    assert response.status_code == 401


async def test_setup_runs_only_once(client: AsyncClient) -> None:
    await complete_setup(client)

    # Ikkinchi marta setup bloklanadi.
    response = await client.post(
        "/api/v1/setup",
        headers={"X-Setup-Token": TEST_SETUP_TOKEN},
        json={
            "kindergarten": {"name": "B2"},
            "branch": {"name": "F2"},
            "owner": {
                "full_name": "E2",
                "username": "eee2",
                "phone": "+998907776655",
                "password": "parol1234",
            },
        },
    )
    assert response.status_code == 409
