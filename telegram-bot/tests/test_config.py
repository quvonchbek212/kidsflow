"""Bot sozlamalari uchun oddiy smoke test."""

from __future__ import annotations

from config import BotSettings


def test_default_backend_url() -> None:
    settings = BotSettings()
    assert settings.backend_api_url.endswith("/api/v1")
    assert settings.default_language == "uz"
