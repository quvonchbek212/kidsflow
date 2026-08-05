"""Kunlik hisobot uchun AI matn tayyorlash (10.1-bo'lim).

AI faqat tarbiyachi kiritgan faktlardan foydalanadi: yangi fakt qo'shmaydi,
sog'liq tashxisi bermaydi. Natija `ai_draft` ga saqlanadi — tarbiyachi uni
`final_summary` sifatida tasdiqlamaguncha ota-onaga yuborilmaydi (draft holicha).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.daily_report import DailyReport
from app.models.enums import AIFeature
from app.repositories.daily_report_repository import DailyReportRepository
from app.services.access_service import AccessService
from app.services.ai.engine import AIEngine
from app.services.ai.provider import AIProvider

_SYSTEM = (
    "Sen bog'cha tarbiyachisiga yordam beruvchi yordamchisan. Faqat berilgan "
    "faktlardan foydalanib, ota-onaga yuboriladigan iliq, tabiiy o'zbekcha matn "
    "tayyorla. Yangi fakt qo'shma. Bolaning sog'lig'i bo'yicha tashxis qo'yma. "
    "Faqat berilgan ma'lumotni qayta ifodala. 2-4 jumla yoz."
)

_MEAL_UZ = {
    "ATE_WELL": "yaxshi ovqatlandi",
    "ATE_SOME": "biroz ovqatlandi",
    "REFUSED": "ovqatdan bosh tortdi",
}
_MOOD_UZ = {
    "HAPPY": "quvnoq",
    "CALM": "xotirjam",
    "TIRED": "charchagan",
    "SAD": "xafa",
    "SICK": "betob",
}


class ReportAIService:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self._reports = DailyReportRepository(session)
        self._access = AccessService(session)
        self._engine = AIEngine(session, provider)

    async def generate_draft(
        self, report_id: uuid.UUID, current_user: CurrentUser
    ) -> DailyReport:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise NotFoundError("Hisobot topilmadi.")
        if not await self._access.can_mark_attendance_for_child(
            current_user, report.child_id, report.branch_id
        ):
            raise PermissionDeniedError("Bu hisobot uchun ruxsat yo'q.")
        if report.published_at is not None:
            raise ConflictError("E'lon qilingan hisobot uchun draft yaratilmaydi.")

        facts = self._facts(report)
        if not facts:
            raise ConflictError("AI matn uchun yetarli fakt yo'q.")

        draft = await self._engine.run_text(
            AIFeature.DAILY_REPORT.value,
            _SYSTEM,
            "Quyidagi faktlardan matn tayyorla:\n" + facts,
            current_user.id,
        )
        report.ai_draft = draft
        return report

    @staticmethod
    def _facts(report: DailyReport) -> str:
        lines: list[str] = []
        if report.meal_status:
            lines.append(
                f"- Ovqatlanish: {_MEAL_UZ.get(report.meal_status, report.meal_status)}"
            )
        if report.nap_minutes is not None:
            lines.append(f"- Uyqu: {report.nap_minutes} daqiqa")
        if report.mood:
            lines.append(f"- Kayfiyat: {_MOOD_UZ.get(report.mood, report.mood)}")
        if report.activities_text:
            lines.append(f"- Faoliyatlar: {report.activities_text}")
        if report.teacher_note:
            lines.append(f"- Tarbiyachi izohi: {report.teacher_note}")
        return "\n".join(lines)
