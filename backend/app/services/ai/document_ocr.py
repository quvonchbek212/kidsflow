"""Chek/kvitansiya OCR (10.4-bo'lim).

Chekdan summa, sana va ta'minotchini TAKLIF sifatida ajratadi. Menejer
tasdiqlamaguncha bu qiymatlar moliyaviy yozuvga aylanmaydi.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import AIFeature
from app.repositories.file_repository import FileRepository
from app.schemas.ai import OCRSuggestion
from app.services.access_service import AccessService
from app.services.ai.engine import AIEngine
from app.services.ai.provider import AIProvider
from app.utils import file_storage

_SYSTEM = (
    "Sen chek/kvitansiyadan ma'lumot ajratuvchisan. Faqat JSON qaytar, izohsiz: "
    '{"amount": <son yoki null>, "expense_date": "YYYY-MM-DD yoki null", '
    '"vendor": "<matn yoki null>"}. Summani faqat son sifatida yoz.'
)
_IMAGE_TYPES = {"image/jpeg", "image/png"}


class DocumentOCRService:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._files = FileRepository(session)
        self._access = AccessService(session)
        self._engine = AIEngine(session, provider)

    async def extract(
        self, file_id: uuid.UUID, current_user: CurrentUser
    ) -> OCRSuggestion:
        # Chek — moliyaviy kontekst, faqat MANAGER/OWNER.
        if not self._access.is_manager_or_owner(current_user):
            raise PermissionDeniedError("OCR uchun MANAGER yoki OWNER kerak.")

        record = await self._files.get_by_id(file_id)
        if record is None:
            raise NotFoundError("Fayl topilmadi.")
        if record.content_type not in _IMAGE_TYPES:
            raise ConflictError("OCR faqat rasm (jpeg/png) uchun ishlaydi.")

        try:
            content = file_storage.read_file(record.storage_key)
        except FileNotFoundError as exc:
            raise NotFoundError("Fayl mazmuni topilmadi.") from exc

        raw = await self._engine.run_image(
            AIFeature.OCR.value,
            _SYSTEM,
            "Ushbu chekdan summa, sana va ta'minotchini ajrat.",
            content,
            record.content_type,
            current_user.id,
        )
        return _parse(raw)


def _parse(raw: str) -> OCRSuggestion:
    # Kod bloklari (```json ... ```) ni tozalaymiz.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return OCRSuggestion(raw_text=raw)

    return OCRSuggestion(
        amount=_to_decimal(data.get("amount")),
        expense_date=_to_date(data.get("expense_date")),
        vendor=data.get("vendor") or None,
        raw_text=raw,
    )


def _to_decimal(value: object):  # type: ignore[no-untyped-def]
    from decimal import Decimal, InvalidOperation

    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: object) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
