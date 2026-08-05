"""Pytest umumiy fixturalar.

Integratsiya testlari xotiradagi SQLite bazasi bilan ishlaydi (tashqi PostgreSQL
talab qilinmaydi). `get_session` dependency'si shu test bazasiga yo'naltiriladi.
StaticPool bitta ulanishni saqlaydi, shuning uchun in-memory baza test davomida
saqlanib qoladi.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import app.models  # noqa: F401 — barcha modellarni Base.metadata'ga ro'yxatga olish
import pytest
from app.database import Base, get_session
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Setup uchun test tokeni (config'dagi standart qiymat bilan mos).
TEST_SETUP_TOKEN = "change-me-setup-token"


@pytest.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """To'g'ridan-to'g'ri DB'ga yozish uchun (seed) sessiya."""
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def _fixed_test_secrets(monkeypatch) -> None:
    """Sirlarni testlar kutgan qiymatlarga qotiradi.

    `Settings` `.env` faylini o'qiydi, shuning uchun ishlab chiquvchi o'z
    `backend/.env` faylida SETUP_TOKEN yoki BOT_API_TOKEN ni o'zgartirsa (masalan
    xavfsizlik uchun tasodifiy qiymatga almashtirsa) butun test to'plami 401
    bilan yiqilardi. Testlar lokal muhit sozlamalariga bog'liq bo'lmasligi kerak.
    """
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "setup_token", TEST_SETUP_TOKEN)
    monkeypatch.setattr(get_settings(), "bot_api_token", TEST_BOT_TOKEN)


@pytest.fixture(autouse=True)
def _temp_file_storage(tmp_path, monkeypatch) -> None:
    """Fayl testlari vaqtinchalik katalogga yozsin (loyiha katalogini bulg'amasin)."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "file_storage_path", str(tmp_path / "storage"))


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch) -> None:
    """Rate limitni standart o'chirib qo'yamiz — ssenariylar ko'p login qiladi.

    Rate limitni maxsus test o'zi yoqadi.
    """
    from app.config import get_settings
    from app.core.rate_limit import InMemoryRateLimiter, get_rate_limiter

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)
    limiter = get_rate_limiter()
    if isinstance(limiter, InMemoryRateLimiter):
        limiter.reset()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Test bazasiga ulangan HTTP klient."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- Yordamchi funksiyalar ---


async def complete_setup(
    client: AsyncClient,
    *,
    owner_username: str = "egasi",
    owner_phone: str = "+998901112233",
    owner_email: str | None = None,
    owner_password: str = "owner-parol-123",
    branch_name: str = "Markaziy filial",
) -> dict:
    """/setup ni chaqirib, OWNER va birinchi filialni yaratadi."""
    owner: dict = {
        "full_name": "Egasi",
        "username": owner_username,
        "phone": owner_phone,
        "password": owner_password,
    }
    if owner_email is not None:
        owner["email"] = owner_email
    response = await client.post(
        "/api/v1/setup",
        headers={"X-Setup-Token": TEST_SETUP_TOKEN},
        json={
            "kindergarten": {"name": "Test bog'cha"},
            "branch": {"name": branch_name, "capacity": 50},
            "owner": owner,
            "default_language": "uz",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, login_value: str, password: str) -> dict:
    """Login qilib token juftligini qaytaradi."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"login": login_value, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


TEST_BOT_TOKEN = "change-me-bot-api-token"


def bot_header() -> dict[str, str]:
    return {"X-Bot-Token": TEST_BOT_TOKEN}


class FakeTelegramSender:
    """Testlar uchun soxta Telegram yuboruvchi — yuborilganlarni saqlaydi."""

    def __init__(self, succeed: bool = True) -> None:
        self.succeed = succeed
        self.sent: list[tuple[int, str]] = []

    async def send(self, chat_id: int, text: str) -> bool:
        self.sent.append((chat_id, text))
        return self.succeed


async def run_outbox(session_factory, sender) -> tuple[int, int]:
    """Outbox processorni test bazasida bir marta ishga tushiradi."""
    from app.services.outbox_processor import OutboxProcessor

    async with session_factory() as session:
        processor = OutboxProcessor(session, sender)
        result = await processor.run_once()
        await session.commit()
        return result


class FakeEmailSender:
    """Testlar uchun soxta email yuboruvchi — yuborilganlarni saqlaydi."""

    def __init__(self, succeed: bool = True) -> None:
        self.succeed = succeed
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, body: str) -> bool:
        self.sent.append((to, subject, body))
        return self.succeed


class FakeAIProvider:
    """Testlar uchun soxta AI provayder — real Gemini kaliti kerak emas."""

    def __init__(self, text: str = "AI tayyorlagan matn", image_text: str = "") -> None:
        self.text = text
        self.image_text = (
            image_text
            or '{"amount": 750000, "expense_date": "2026-09-03", "vendor": "Test"}'
        )
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, prompt: str):
        from app.services.ai.provider import AIResult

        self.calls.append((system, prompt))
        return AIResult(text=self.text, input_tokens=10, output_tokens=20)

    async def complete_with_image(
        self, system: str, prompt: str, image: bytes, mime_type: str
    ):
        from app.services.ai.provider import AIResult

        self.calls.append((system, prompt))
        return AIResult(text=self.image_text, input_tokens=15, output_tokens=25)


def override_ai_provider(provider: FakeAIProvider) -> None:
    """AI endpointlari uchun soxta provayderni ulaydi."""
    from app.services.ai.provider import get_ai_provider

    app.dependency_overrides[get_ai_provider] = lambda: provider


# Kichik yaroqli PNG (1x1) — fayl testlari uchun.
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


async def create_staff(
    client: AsyncClient,
    owner_access: str,
    *,
    role: str,
    phone: str,
    password: str,
    full_name: str = "Xodim",
    branch_id: str | None = None,
    username: str | None = None,
) -> str:
    """OWNER xodim yaratadi va uning user_id sini qaytaradi."""
    # Username berilmasa, telefon raqamidan hosil qilinadi (testlarda unique).
    resolved_username = username or f"u{phone.lstrip('+')}"
    body: dict = {
        "full_name": full_name,
        "username": resolved_username,
        "phone": phone,
        "password": password,
        "role": role,
    }
    if branch_id is not None:
        body["branch_id"] = branch_id
    resp = await client.post(
        "/api/v1/users", headers=auth_header(owner_access), json=body
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]
