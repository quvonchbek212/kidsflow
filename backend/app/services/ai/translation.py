"""Matn tarjimasi (10.5-bo'lim): o'zbek, rus, ingliz. Asl matn ham saqlanadi."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.models.enums import AIFeature
from app.services.ai.engine import AIEngine
from app.services.ai.provider import AIProvider

_LANG_NAMES = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}

_SYSTEM = (
    "Sen professional tarjimonsan. Berilgan matnni ko'rsatilgan tilga tarjima qil. "
    "Faqat tarjimani qaytar, hech qanday izoh yoki qo'shimcha matn yozma."
)


class TranslationService:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._engine = AIEngine(session, provider)

    async def translate(
        self, text: str, target_language: str, current_user: CurrentUser
    ) -> str:
        lang_name = _LANG_NAMES.get(target_language, target_language)
        prompt = f"Matnni {lang_name} tiliga tarjima qil:\n\n{text}"
        return await self._engine.run_text(
            AIFeature.TRANSLATION.value, _SYSTEM, prompt, current_user.id
        )
