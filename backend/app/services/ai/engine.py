"""AI engine — limit tekshiruvi va foydalanish hisobini yuritish (10.6-bo'lim).

Har bir AI so'rovi oldidan oylik token limiti tekshiriladi, so'rovdan keyin
token va baholangan xarajat `ai_usage_logs` ga yoziladi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.ai import AIUsageLog
from app.repositories.ai_repository import AIUsageRepository
from app.services.ai.provider import AIProvider, AIQuotaExceededError, AIResult


def _month_start() -> date:
    now = datetime.now(UTC)
    return date(now.year, now.month, 1)


def _estimate_cost(input_tokens: int, output_tokens: int) -> Decimal:
    settings = get_settings()
    cost = Decimal(input_tokens) / Decimal(1_000_000) * Decimal(
        str(settings.ai_input_cost_per_million)
    ) + Decimal(output_tokens) / Decimal(1_000_000) * Decimal(
        str(settings.ai_output_cost_per_million)
    )
    return cost.quantize(Decimal("0.000001"))


class AIEngine:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self._provider = provider
        self._usage = AIUsageRepository(session)

    async def _check_limit(self) -> None:
        limit = get_settings().ai_monthly_token_limit
        if limit <= 0:
            return
        used = await self._usage.tokens_since(_month_start())
        if used >= limit:
            raise AIQuotaExceededError()

    async def _record(
        self, feature: str, result: AIResult, user_id: uuid.UUID | None
    ) -> None:
        self._usage.add(
            AIUsageLog(
                feature=feature,
                model=get_settings().ai_model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost=_estimate_cost(
                    result.input_tokens, result.output_tokens
                ),
                user_id=user_id,
            )
        )
        await self._session.flush()

    async def run_text(
        self,
        feature: str,
        system: str,
        prompt: str,
        user_id: uuid.UUID | None,
    ) -> str:
        await self._check_limit()
        result = await self._provider.complete(system, prompt)
        await self._record(feature, result, user_id)
        return result.text

    async def run_image(
        self,
        feature: str,
        system: str,
        prompt: str,
        image: bytes,
        mime_type: str,
        user_id: uuid.UUID | None,
    ) -> str:
        await self._check_limit()
        result = await self._provider.complete_with_image(
            system, prompt, image, mime_type
        )
        await self._record(feature, result, user_id)
        return result.text
