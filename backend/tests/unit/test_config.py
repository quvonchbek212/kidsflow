"""Sozlama (config) uchun unit testlar."""

from __future__ import annotations

from app.config import Settings


def test_cors_origins_parsed_from_string() -> None:
    """Vergul bilan ajratilgan CORS ro'yxati to'g'ri bo'linadi."""
    settings = Settings(cors_origins="http://a.uz, http://b.uz")

    assert settings.cors_origins == ["http://a.uz", "http://b.uz"]


def test_defaults_are_development() -> None:
    """Standart muhit — development."""
    settings = Settings()

    assert settings.environment == "development"
    assert settings.is_production is False
    assert settings.api_v1_prefix == "/api/v1"
