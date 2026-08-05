"""AI provayder abstraksiyasi (10-bo'lim).

Almashtiriladigan (pluggable) provayderlar:
- `GeminiProvider` — Google Gemini REST API (yoki markaziy AI gateway);
- `DisabledAIProvider` — AI o'chirilgan holat (503 qaytaradi);
- test uchun soxta provayder (`tests`da) inject qilinadi.

API key faqat backendda ishlatiladi — frontend yoki botga berilmaydi (10.6-bo'lim).
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import get_settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


class AIUnavailableError(AppError):
    status_code = 503
    detail = "AI xizmati hozircha mavjud emas."


class AIQuotaExceededError(AppError):
    status_code = 429
    detail = "AI oylik token limiti tugagan."


@dataclass(frozen=True)
class AIResult:
    text: str
    input_tokens: int
    output_tokens: int


class AIProvider(Protocol):
    async def complete(self, system: str, prompt: str) -> AIResult:
        """Matnli so'rov: (system ko'rsatma, foydalanuvchi prompti) → natija."""
        ...

    async def complete_with_image(
        self, system: str, prompt: str, image: bytes, mime_type: str
    ) -> AIResult:
        """Rasm + matnli so'rov (OCR uchun)."""
        ...


class DisabledAIProvider:
    """AI o'chirilgan yoki sozlanmagan holat."""

    async def complete(self, system: str, prompt: str) -> AIResult:
        raise AIUnavailableError()

    async def complete_with_image(
        self, system: str, prompt: str, image: bytes, mime_type: str
    ) -> AIResult:
        raise AIUnavailableError()


class GeminiProvider:
    """Google Gemini `generateContent` REST API orqali ishlaydi."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        gateway_url: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        base = gateway_url or "https://generativelanguage.googleapis.com/v1beta"
        self._url = f"{base}/models/{model}:generateContent"

    async def _post(self, parts: list[dict], system: str) -> AIResult:
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.4},
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._url,
                    params={"key": self._api_key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.exception("Gemini so'rovi muvaffaqiyatsiz")
            raise AIUnavailableError() from exc

        if response.status_code != 200:
            logger.error("Gemini xatosi: %s", response.status_code)
            raise AIUnavailableError()

        data = response.json()
        text = _extract_text(data)
        usage = data.get("usageMetadata", {})
        return AIResult(
            text=text,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
        )

    async def complete(self, system: str, prompt: str) -> AIResult:
        return await self._post([{"text": prompt}], system)

    async def complete_with_image(
        self, system: str, prompt: str, image: bytes, mime_type: str
    ) -> AIResult:
        parts: list[dict] = [
            {"text": prompt},
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image).decode("ascii"),
                }
            },
        ]
        return await self._post(parts, system)


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def get_ai_provider() -> AIProvider:
    """Konfiguratsiyaga qarab AI provayderni tanlaydi (FastAPI dependency)."""
    settings = get_settings()
    if not settings.ai_enabled or not settings.gemini_api_key:
        return DisabledAIProvider()
    return GeminiProvider(
        settings.gemini_api_key,
        settings.ai_model,
        gateway_url=settings.ai_gateway_url,
        timeout=settings.ai_request_timeout_seconds,
    )
