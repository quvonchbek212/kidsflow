"""Smoke test: health endpointlari ishlayotganini tekshiradi (17-bo'lim topshirig'i)."""

from __future__ import annotations

import pytest
from app import __version__
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_liveness_ok(client: AsyncClient) -> None:
    """`/api/v1/health` 200 va to'g'ri versiyani qaytaradi."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["app"] == "KIDSFLOW"


async def test_readiness_ok(client: AsyncClient) -> None:
    """`/api/v1/health/ready` DB ishlaganda 200 va `ready` qaytaradi."""
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"


async def test_openapi_available(client: AsyncClient) -> None:
    """OpenAPI sxemasi frontend typed-client uchun mavjud (8-bo'lim)."""
    response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "KIDSFLOW"
