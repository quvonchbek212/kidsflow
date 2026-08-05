"""FastAPI ilova kirish nuqtasi.

API versiyasi boshidan `/api/v1` bilan boshlanadi (loyiha strukturasi, 6-bo'lim).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Ilova hayotiy sikli: ishga tushish va to'xtash hodisalari."""
    settings = get_settings()
    configure_logging(debug=settings.debug)
    logger.info("Ilova ishga tushdi", extra={"environment": settings.environment})
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Ilova to'xtatildi")


def create_app() -> FastAPI:
    """FastAPI ilovasini yaratadi va sozlaydi (application factory)."""
    settings = get_settings()

    # Interaktiv hujjatlar production'da yopiladi: ular butun API sxemasini,
    # jumladan endpoint nomlari va so'rov strukturalarini oshkor qiladi. Bu
    # o'z-o'zidan zaiflik emas, lekin hujumchiga bepul xarita beradi va
    # hujjatlar sahifasi hech qanday autentifikatsiya talab qilmaydi.
    docs_enabled = not settings.is_production

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Xususiy bog'chalar uchun boshqaruv platformasi",
        openapi_url=(
            f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        lifespan=lifespan,
    )

    # Middleware tartibi: oxirgi qo'shilgan birinchi ishlaydi. So'rov logging eng
    # tashqarida bo'lsin (to'liq davomiylikni o'lchash uchun).
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.request_logging_enabled:
        app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
