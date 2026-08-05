"""Ota-onalar uchun RAG yordamchi (10.2-bo'lim).

Faqat ichki bilim manbalaridan (knowledge_documents) foydalanadi va javobda
foydalanilgan manbani ko'rsatadi. Tibbiy, huquqiy yoki moliyaviy qarorlar bermaydi.
"""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.models.ai import KnowledgeDocument
from app.models.enums import AIFeature
from app.repositories.ai_repository import KnowledgeRepository
from app.repositories.branch_repository import BranchRepository
from app.services.ai.engine import AIEngine
from app.services.ai.provider import AIProvider

_SYSTEM = (
    "Sen bog'chaning ota-onalar uchun yordamchisisan. Faqat quyida berilgan ichki "
    "manbalardan foydalanib o'zbek tilida javob ber. Manbada javob bo'lmasa, "
    "'Bu haqda ma'lumotim yo'q, iltimos bog'cha ma'muriyatiga murojaat qiling' deb "
    "ayt. Tibbiy, huquqiy yoki moliyaviy qaror berma — bunday savollarda mutaxassisga "
    "murojaat qilishni tavsiya qil. Qaysi manbadan foydalanganingni oxirida ko'rsat."
)

_TOP_K = 5


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 2}


def _rank(question: str, docs: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
    q_words = _keywords(question)
    scored = [(len(q_words & _keywords(f"{d.title} {d.content}")), d) for d in docs]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    ranked = [d for score, d in scored if score > 0]
    # Mos manba topilmasa, eng birinchi hujjatlarni kontekst sifatida beramiz.
    return (ranked or docs)[:_TOP_K]


class ParentAssistantService:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._knowledge = KnowledgeRepository(session)
        self._branches = BranchRepository(session)
        self._engine = AIEngine(session, provider)

    async def answer(
        self, current_user: CurrentUser, question: str
    ) -> tuple[str, list[str]]:
        branch_ids = [b.id for b in await self._branches.list_all()]
        docs = await self._knowledge.list_active(branch_ids)
        selected = _rank(question, docs)

        if not selected:
            return (
                "Hozircha bilim bazasi bo'sh. Iltimos, bog'cha ma'muriyatiga "
                "murojaat qiling.",
                [],
            )

        context = "\n\n".join(
            f"[Manba {i + 1}: {doc.title}]\n{doc.content}"
            for i, doc in enumerate(selected)
        )
        prompt = f"Ichki manbalar:\n{context}\n\nOta-ona savoli: {question}"
        answer = await self._engine.run_text(
            AIFeature.PARENT_ASSISTANT.value, _SYSTEM, prompt, current_user.id
        )
        return answer, [doc.title for doc in selected]
