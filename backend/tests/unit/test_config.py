"""Sozlama (config) uchun unit testlar."""

from __future__ import annotations

import pytest
from app.config import Settings
from pydantic import ValidationError

# Testlar ishlab chiquvchining `backend/.env` fayliga bog'lanib qolmasligi uchun
# production ssenariylarida barcha sirlar aniq beriladi.
STRONG_SECRETS = {
    "environment": "production",
    "jwt_secret": "x" * 40,
    "setup_token": "y" * 40,
    "encryption_key": "z" * 40,
    "bot_api_token": "w" * 40,
}


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


def test_production_accepts_changed_secrets() -> None:
    """Barcha sirlar almashtirilgan bo'lsa production'da ishga tushadi."""
    settings = Settings(**STRONG_SECRETS)

    assert settings.is_production is True


@pytest.mark.parametrize(
    ("field", "default_value"),
    [
        ("jwt_secret", "change-me-jwt-secret"),
        ("setup_token", "change-me-setup-token"),
        ("encryption_key", "change-me-encryption-key"),
        ("bot_api_token", "change-me-bot-api-token"),
    ],
)
def test_production_rejects_default_secret(field: str, default_value: str) -> None:
    """Production'da standart `change-me-…` sir bilan ishga tushib bo'lmaydi.

    Har bir sir alohida tekshiriladi: bittasi e'tibordan qolib ketsa ham ilova
    ishga tushmasligi kerak.
    """
    values = {**STRONG_SECRETS, field: default_value}

    with pytest.raises(ValidationError) as exc:
        Settings(**values)

    assert field.upper() in str(exc.value)
