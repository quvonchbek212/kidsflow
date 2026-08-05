"""Telegram bot sozlamalari.

Bot faqat backend API bilan ishlaydi, database paroli berilmaydi
(loyiha strukturasi, 7-bo'lim).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(default="", description="BotFather'dan olingan token")
    backend_api_url: str = "http://backend:8000/api/v1"
    # Backend bot endpointlariga kirish uchun umumiy sir (X-Bot-Token).
    backend_bot_token: str = Field(default="", description="Backend BOT_API_TOKEN")
    default_language: str = "uz"
    request_timeout_seconds: float = 10.0


@lru_cache
def get_bot_settings() -> BotSettings:
    return BotSettings()
