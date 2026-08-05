"""Telegram xabar yuborish abstraksiyasi (9-bo'lim).

Worker outbox hodisalarini qayta ishlab, bildirishnomalarni shu interfeys orqali
yuboradi. Test va konfiguratsiyalanmagan holatlar uchun almashtiriladigan (pluggable)
implementatsiyalar mavjud.
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class TelegramSender(Protocol):
    async def send(self, chat_id: int, text: str) -> bool:
        """Xabar yuboradi. Muvaffaqiyatda True qaytaradi."""
        ...


class NoopTelegramSender:
    """Bot tokeni sozlanmagan holat — hech narsa yubormaydi."""

    async def send(self, chat_id: int, text: str) -> bool:
        logger.info(
            "Telegram sozlanmagan — xabar navbatda qoldi",
            extra={"chat_id": chat_id},
        )
        return False


class HttpxTelegramSender:
    """Telegram Bot API orqali real yuboruvchi."""

    def __init__(self, bot_token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, chat_id: int, text: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._base_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
            return response.status_code == 200
        except httpx.HTTPError:
            logger.exception("Telegram xabar yuborishda xatolik")
            return False


def get_default_sender() -> TelegramSender:
    """Konfiguratsiyaga qarab yuboruvchini tanlaydi."""
    token = get_settings().telegram_bot_token
    if token:
        return HttpxTelegramSender(token)
    return NoopTelegramSender()
