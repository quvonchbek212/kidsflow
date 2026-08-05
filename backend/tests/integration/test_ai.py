"""AI funksiyalari (10-bo'lim) — soxta provayder bilan, guardrail tekshiruvi bilan."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TINY_PNG,
    FakeAIProvider,
    auth_header,
    complete_setup,
    create_staff,
    login,
    override_ai_provider,
)

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _base(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000001",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000001", "mgr-123-456"))["access_token"]
    return {"owner": owner, "manager": manager, "branch_id": branch_id}


async def _report_scenario(client: AsyncClient) -> dict:
    b = await _base(client)
    manager = b["manager"]
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(manager),
            json={"full_name": "Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": b["branch_id"], "name": "G", "capacity": 10},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(manager),
        json={
            "branch_id": b["branch_id"],
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    teacher_id = await create_staff(
        client,
        b["owner"],
        role="TEACHER",
        phone="+998900000003",
        password="teacher-123",
        branch_id=b["branch_id"],
    )
    await client.post(
        f"/api/v1/groups/{group_id}/teachers",
        headers=auth_header(manager),
        json={"teacher_user_id": teacher_id},
    )
    teacher = (await login(client, "+998900000003", "teacher-123"))["access_token"]
    report_id = (
        await client.post(
            "/api/v1/daily-reports",
            headers=auth_header(teacher),
            json={
                "child_id": child_id,
                "report_date": "2026-09-02",
                "meal_status": "ATE_WELL",
                "mood": "HAPPY",
                "activities_text": "Rasm chizdi.",
            },
        )
    ).json()["id"]
    b.update({"teacher": teacher, "report_id": report_id, "child_id": child_id})
    return b


async def test_ai_disabled_returns_503(client: AsyncClient) -> None:
    b = await _base(client)
    # Provayder override qilinmagan → AI o'chirilgan (default) → 503.
    resp = await client.post(
        "/api/v1/ai/translate",
        headers=auth_header(b["manager"]),
        json={"text": "Salom", "target_language": "en"},
    )
    assert resp.status_code == 503


async def test_translate_and_usage_logged(client: AsyncClient) -> None:
    b = await _base(client)
    provider = FakeAIProvider(text="Hello")
    override_ai_provider(provider)

    resp = await client.post(
        "/api/v1/ai/translate",
        headers=auth_header(b["manager"]),
        json={"text": "Salom", "target_language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["translated_text"] == "Hello"
    assert body["original_text"] == "Salom"

    # Foydalanish jurnalga yozildi (OWNER ko'radi).
    usage = await client.get("/api/v1/ai/usage", headers=auth_header(b["owner"]))
    assert usage.status_code == 200
    logs = usage.json()
    assert len(logs) == 1
    assert logs[0]["feature"] == "TRANSLATION"
    assert logs[0]["input_tokens"] == 10


async def test_report_ai_draft_not_published(client: AsyncClient) -> None:
    b = await _report_scenario(client)
    provider = FakeAIProvider(text="Bugun bolangiz yaxshi ovqatlandi va quvnoq bo'ldi.")
    override_ai_provider(provider)

    resp = await client.post(
        f"/api/v1/daily-reports/{b['report_id']}/ai-draft",
        headers=auth_header(b["teacher"]),
    )
    assert resp.status_code == 200
    assert resp.json()["ai_draft"] == provider.text

    # AI drafti faqat qoralama — hisobot hali e'lon qilinmagan (guardrail).
    report = await client.get(
        f"/api/v1/daily-reports/{b['report_id']}", headers=auth_header(b["teacher"])
    )
    assert report.json()["is_published"] is False

    # AI faqat berilgan faktlardan foydalandi (prompt faktlarni o'z ichiga oladi).
    _, prompt = provider.calls[0]
    assert "yaxshi ovqatlandi" in prompt
    assert "quvnoq" in prompt


async def test_finance_narrative_uses_real_numbers(client: AsyncClient) -> None:
    b = await _base(client)
    provider = FakeAIProvider(text="Daromad barqaror.")
    override_ai_provider(provider)

    resp = await client.post(
        "/api/v1/ai/finance-narrative",
        headers=auth_header(b["manager"]),
        json={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert resp.status_code == 200
    assert resp.json()["narrative"] == "Daromad barqaror."
    # AI ga faqat SQL orqali hisoblangan raqamlar berildi (guardrail).
    _, prompt = provider.calls[0]
    assert "accrual" in prompt.lower() or "hisoblangan daromad" in prompt.lower()


async def test_parent_assistant_cites_sources(client: AsyncClient) -> None:
    b = await _base(client)
    await client.post(
        "/api/v1/knowledge-documents",
        headers=auth_header(b["manager"]),
        json={
            "category": "WORKING_HOURS",
            "title": "Ish vaqti",
            "content": "Bog'cha 08:00 dan 18:00 gacha ishlaydi.",
        },
    )
    provider = FakeAIProvider(text="Bog'cha 08:00 dan 18:00 gacha ochiq.")
    override_ai_provider(provider)

    resp = await client.post(
        "/api/v1/ai/assistant",
        headers=auth_header(b["manager"]),
        json={"question": "Bog'cha necha soatda ochiladi?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == provider.text
    assert "Ish vaqti" in body["sources"]  # foydalanilgan manba ko'rsatildi


async def test_ocr_returns_suggestion(client: AsyncClient) -> None:
    b = await _base(client)
    file_id = (
        await client.post(
            "/api/v1/files",
            headers=auth_header(b["manager"]),
            files={"upload": ("receipt.png", TINY_PNG, "image/png")},
        )
    ).json()["id"]
    provider = FakeAIProvider(
        image_text='{"amount": 750000, "expense_date": "2026-09-03", "vendor": "Do\'kon"}'
    )
    override_ai_provider(provider)

    resp = await client.post(
        "/api/v1/ai/ocr",
        headers=auth_header(b["manager"]),
        json={"file_id": file_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Bu faqat taklif — moliyaviy yozuv emas (guardrail).
    assert str(body["amount"]) in ("750000", "750000.0", "750000.00")
    assert body["expense_date"] == "2026-09-03"
    assert body["vendor"] == "Do'kon"


async def test_ai_monthly_token_limit(client: AsyncClient, monkeypatch) -> None:
    from app.config import get_settings

    b = await _base(client)
    monkeypatch.setattr(get_settings(), "ai_monthly_token_limit", 1)
    override_ai_provider(FakeAIProvider(text="ok"))

    first = await client.post(
        "/api/v1/ai/translate",
        headers=auth_header(b["manager"]),
        json={"text": "a", "target_language": "en"},
    )
    assert first.status_code == 200  # birinchi so'rov limit ichida

    second = await client.post(
        "/api/v1/ai/translate",
        headers=auth_header(b["manager"]),
        json={"text": "b", "target_language": "en"},
    )
    assert second.status_code == 429  # limit oshdi
