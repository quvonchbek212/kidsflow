"""Umumiy backend klient (singleton) va yordamchilar."""

from __future__ import annotations

from api_client import BackendClient

_client: BackendClient | None = None


def get_client() -> BackendClient:
    global _client
    if _client is None:
        _client = BackendClient()
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
