"""AI endpointlari (10-bo'lim).

AI faqat tayyor ma'lumotni tushuntiradi/matn yaratadi. Barcha so'rovlar backend
orqali — API key frontend/botga berilmaydi. AI o'chirilgan bo'lsa 503 qaytadi.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, require_roles
from app.models.enums import Role
from app.repositories.ai_repository import AIUsageRepository
from app.schemas.ai import (
    AIUsageLogResponse,
    AssistantRequest,
    AssistantResponse,
    DailyReportDraftResponse,
    FinanceNarrativeRequest,
    FinanceNarrativeResponse,
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentResponse,
    OCRRequest,
    OCRSuggestion,
    TranslationRequest,
    TranslationResponse,
)
from app.services.ai.document_ocr import DocumentOCRService
from app.services.ai.finance_narrator import FinanceNarratorService
from app.services.ai.knowledge_service import KnowledgeService
from app.services.ai.parent_assistant import ParentAssistantService
from app.services.ai.provider import AIProvider, get_ai_provider
from app.services.ai.report_generator import ReportAIService
from app.services.ai.translation import TranslationService

router = APIRouter(tags=["ai"])


@router.post(
    "/daily-reports/{report_id}/ai-draft",
    response_model=DailyReportDraftResponse,
    summary="Kunlik hisobot uchun AI matn tayyorlash (draft; TEACHER/MANAGER)",
)
async def generate_report_draft(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> DailyReportDraftResponse:
    report = await ReportAIService(session, provider).generate_draft(
        report_id, current_user
    )
    return DailyReportDraftResponse(
        daily_report_id=report.id, ai_draft=report.ai_draft or ""
    )


@router.post(
    "/ai/finance-narrative",
    response_model=FinanceNarrativeResponse,
    summary="Moliyaviy ko'rsatkichlarni AI sharhi (OWNER/MANAGER)",
)
async def finance_narrative(
    payload: FinanceNarrativeRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> FinanceNarrativeResponse:
    text = await FinanceNarratorService(session, provider).narrate(
        current_user, payload.period_start, payload.period_end
    )
    return FinanceNarrativeResponse(narrative=text)


@router.post(
    "/ai/assistant",
    response_model=AssistantResponse,
    summary="Ota-onalar uchun RAG yordamchi",
)
async def assistant(
    payload: AssistantRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> AssistantResponse:
    answer, sources = await ParentAssistantService(session, provider).answer(
        current_user, payload.question
    )
    return AssistantResponse(answer=answer, sources=sources)


@router.post(
    "/ai/ocr",
    response_model=OCRSuggestion,
    summary="Chekdan ma'lumot ajratish (taklif; MANAGER/OWNER)",
)
async def ocr(
    payload: OCRRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> OCRSuggestion:
    return await DocumentOCRService(session, provider).extract(
        payload.file_id, current_user
    )


@router.post(
    "/ai/translate",
    response_model=TranslationResponse,
    summary="Matn tarjimasi (uz/ru/en)",
)
async def translate(
    payload: TranslationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> TranslationResponse:
    translated = await TranslationService(session, provider).translate(
        payload.text, payload.target_language, current_user
    )
    return TranslationResponse(
        original_text=payload.text,
        translated_text=translated,
        target_language=payload.target_language,
    )


# --- Bilim bazasi (RAG manba) ---


@router.post(
    "/knowledge-documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bilim hujjati yaratish (MANAGER/OWNER)",
)
async def create_knowledge_document(
    payload: KnowledgeDocumentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KnowledgeDocumentResponse:
    doc = await KnowledgeService(session).create(payload, current_user)
    return KnowledgeDocumentResponse(
        id=doc.id,
        branch_id=doc.branch_id,
        category=doc.category,
        title=doc.title,
        content=doc.content,
        is_active=doc.is_active,
    )


@router.get(
    "/knowledge-documents",
    response_model=list[KnowledgeDocumentResponse],
    summary="Bilim hujjatlari ro'yxati (MANAGER/OWNER)",
)
async def list_knowledge_documents(
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[KnowledgeDocumentResponse]:
    docs = await KnowledgeService(session).list_visible(current_user)
    return [
        KnowledgeDocumentResponse(
            id=d.id,
            branch_id=d.branch_id,
            category=d.category,
            title=d.title,
            content=d.content,
            is_active=d.is_active,
        )
        for d in docs
    ]


@router.get(
    "/ai/usage",
    response_model=list[AIUsageLogResponse],
    summary="AI foydalanish jurnali (OWNER)",
)
async def ai_usage(
    current_user: CurrentUser = Depends(require_roles(Role.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> list[AIUsageLogResponse]:
    logs = await AIUsageRepository(session).recent()
    return [
        AIUsageLogResponse(
            id=log.id,
            feature=log.feature,
            model=log.model,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            estimated_cost=log.estimated_cost,
            created_at=log.created_at,
        )
        for log in logs
    ]
