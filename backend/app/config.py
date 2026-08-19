"""Application configuration.

Barcha sozlamalar muhit o'zgaruvchilaridan (`.env`) o'qiladi. Har bir bog'cha
alohida deployment bo'lgani uchun sozlamalar shu deployment `.env` fayli orqali
beriladi (loyiha strukturasi, 2.2-bo'lim).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Deployment sozlamalari."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Umumiy ---
    app_name: str = "KIDSFLOW"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Interfeys vaqt zonasi (5-bo'lim: UTC saqlanadi, Asia/Tashkent ko'rsatiladi)
    timezone: str = "Asia/Tashkent"
    default_language: Literal["uz", "ru", "en"] = "uz"
    currency: str = "UZS"

    # --- Xavfsizlik ---
    # Bir martalik setup tokeni (4.1-bo'lim).
    setup_token: str = Field(default="change-me-setup-token", min_length=8)
    jwt_secret: str = Field(default="change-me-jwt-secret", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # Tibbiy/sog'liq ma'lumotlarini shifrlash uchun parol-kalit (11-bo'lim).
    encryption_key: str = Field(default="change-me-encryption-key", min_length=8)

    # Telegram bot backend API'ga kirishi uchun umumiy sir (7-bo'lim).
    bot_api_token: str = Field(default="change-me-bot-api-token", min_length=8)

    # Telegram taklif kodi amal qilish muddati (daqiqa).
    invitation_ttl_minutes: int = 60

    # --- Rate limiting (11-bo'lim: login/setup endpointlariga) ---
    rate_limit_enabled: bool = True
    # "memory" — bitta process uchun; "redis" — bir nechta instans uchun (prod).
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    login_rate_limit_max: int = 10
    login_rate_limit_window_seconds: int = 60
    setup_rate_limit_max: int = 5
    setup_rate_limit_window_seconds: int = 300

    # Hisob darajasidagi qulf. IP bo'yicha limit bir nechta IP dan taqsimlangan
    # hujumni to'xtata olmaydi, shuning uchun ketma-ket muvaffaqiyatsiz
    # urinishlar foydalanuvchi bo'yicha ham sanaladi.
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15

    # --- Monitoring / observability ---
    # So'rov loglarini (method/path/status/davomiylik) yoqish.
    request_logging_enabled: bool = True

    # --- Fayl saqlash (11-bo'lim) ---
    file_storage_path: str = "storage"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    # Antivirus (ClamAV). O'chirilgan bo'lsa fayllar PENDING deb belgilanadi —
    # ya'ni "tekshirilmagan", ilgarigidek yolg'ondan CLEAN emas.
    file_scan_enabled: bool = False
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    file_scan_timeout_seconds: float = 30.0
    allowed_upload_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "application/pdf"],
    )

    # --- Worker / bildirishnoma (9-bo'lim) ---
    # Backend worker Telegram xabar yuborishi uchun bot tokeni. Bo'sh bo'lsa,
    # bildirishnomalar navbatда qoladi (yuborilmaydi).
    telegram_bot_token: str = ""
    worker_poll_interval_seconds: int = 5
    outbox_max_retries: int = 5

    # --- Email (parolni tiklash uchun SMTP) ---
    # Bo'sh bo'lsa (smtp_host=""), tiklash havolasi haqiqatda yuborilmaydi —
    # faqat log'ga yoziladi (lokal/test muhitlar uchun).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_from_name: str = "KIDSFLOW"
    password_reset_ttl_minutes: int = 30
    # Tiklash havolasi shu bazaga qo'shiladi (frontend login/reset-password sahifasi).
    frontend_base_url: str = "http://localhost:3000"

    # --- AI / Gemini (10-bo'lim) ---
    # AI standart o'chirilgan (MVP AI'siz ishlaydi). Yoqish uchun kalit + true.
    ai_enabled: bool = False
    gemini_api_key: str = ""
    # Markaziy AI gateway (ixtiyoriy). Bo'sh bo'lsa Google endpointi ishlatiladi.
    ai_gateway_url: str = ""
    ai_model: str = "gemini-2.0-flash"
    ai_request_timeout_seconds: float = 30.0
    # Oylik token limiti (0 = cheksiz). Limit oshsa AI so'rovlari bloklanadi.
    ai_monthly_token_limit: int = 0
    # Xarajat baholash uchun 1M token narxi (USD, estimated_cost uchun).
    ai_input_cost_per_million: float = 0.10
    ai_output_cost_per_million: float = 0.40

    @field_validator("allowed_upload_types", mode="before")
    @classmethod
    def _split_types(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # --- Ma'lumotlar bazasi ---
    # asyncpg drayveri talab qilinadi (async SQLAlchemy).
    database_url: str = "postgresql+asyncpg://kidsflow:kidsflow@localhost:5432/kidsflow"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # --- Redis (worker navbatlari uchun) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- CORS ---
    # NoDecode: pydantic-settings qiymatni JSON deb o'qimasin, biz vergul bilan
    # ajratamiz.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Vergul bilan ajratilgan CORS ro'yxatini qo'llab-quvvatlash."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _forbid_default_secrets_in_production(self) -> Settings:
        """Productionda standart sirlar bilan ishga tushishga yo'l qo'ymaydi.

        `.env` fayli namunadan nusxa olinganda `change-me-…` qiymatlari
        o'zgartirilmay qolib ketishi oson. Bunday holda JWT tokenlari hammaga
        ma'lum kalit bilan imzolanadi va `/setup` endpointi himoyasiz qoladi,
        shuning uchun ilova ishga tushmasligi kerak.

        ENCRYPTION_KEY va BOT_API_TOKEN ham shu ro'yxatda: birinchisidan
        bolalarning tibbiy izohlarini shifrlash kaliti hosil qilinadi (standart
        qiymatda shifrlash ma'nosiz bo'lib qoladi), ikkinchisi esa
        `/telegram/session` orqali istalgan ota-ona nomidan token olish
        imkonini beradi.
        """
        if not self.is_production:
            return self
        defaults = {
            "JWT_SECRET": (self.jwt_secret, "change-me-jwt-secret"),
            "SETUP_TOKEN": (self.setup_token, "change-me-setup-token"),
            "ENCRYPTION_KEY": (self.encryption_key, "change-me-encryption-key"),
            "BOT_API_TOKEN": (self.bot_api_token, "change-me-bot-api-token"),
        }
        unchanged = [
            name
            for name, (value, default) in defaults.items()
            if value.startswith(default)
        ]
        if unchanged:
            raise ValueError(
                "Production muhitida quyidagi sozlamalar standart qiymatda qolgan: "
                + ", ".join(unchanged)
                + ". Ularni `.env` faylida o'zgartiring."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qib, keshda saqlaydi."""
    return Settings()
