"""AI sxemalari (10-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import KnowledgeCategory

# --- Daily report AI draft ---


class DailyReportDraftResponse(BaseModel):
    daily_report_id: uuid.UUID
    ai_draft: str


# --- Finance narrative ---


class FinanceNarrativeRequest(BaseModel):
    period_start: date
    period_end: date


class FinanceNarrativeResponse(BaseModel):
    narrative: str


# --- Parent assistant (RAG) ---


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AssistantResponse(BaseModel):
    answer: str
    sources: list[str]  # foydalanilgan ichki manba nomlari (10.2-bo'lim)


# --- OCR ---


class OCRRequest(BaseModel):
    file_id: uuid.UUID


class OCRSuggestion(BaseModel):
    """Chekdan ajratilgan taklif — menejer tasdiqlamaguncha yozuv emas (10.4-bo'lim)."""

    amount: Decimal | None = None
    expense_date: date | None = None
    vendor: str | None = None
    raw_text: str | None = None


# --- Translation ---


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    target_language: str = Field(pattern="^(uz|ru|en)$")


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    target_language: str


# --- Knowledge documents (RAG manba) ---


class KnowledgeDocumentCreateRequest(BaseModel):
    branch_id: uuid.UUID | None = None
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=8000)


class KnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    branch_id: uuid.UUID | None
    category: str
    title: str
    content: str
    is_active: bool


# --- AI usage ---


class AIUsageLogResponse(BaseModel):
    id: uuid.UUID
    feature: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal
    created_at: datetime
