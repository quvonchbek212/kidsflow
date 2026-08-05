"""Production tayyorgarligi: xavfsizlik sarlavhalari, request ID, rate limit."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_security_headers_present(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in resp.headers


async def test_request_id_header_present(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.headers.get("x-request-id")


async def test_login_is_rate_limited(client: AsyncClient, monkeypatch) -> None:
    from app.config import get_settings
    from app.core.rate_limit import get_rate_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "login_rate_limit_max", 3)
    get_rate_limiter().reset()

    codes = []
    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "+998900000000", "password": "noto'g'ri"},
        )
        codes.append(resp.status_code)

    # Dastlabki 3 urinish 401 (limit ichida), keyingilari 429.
    assert codes[:3] == [401, 401, 401]
    assert 429 in codes[3:]
