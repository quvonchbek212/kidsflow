"""Health-check endpointlari (12-bo'lim: har bir servisda healthcheck)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.health import HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness")
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Servis ishga tushganini bildiradi (bog'liqliklarni tekshirmaydi)."""
    return HealthResponse(
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness",
)
async def readiness(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Ma'lumotlar bazasi ulanishini tekshiradi.

    DB ishlamasa 503 qaytaradi — orkestrator (Docker/K8s) shu asosda trafikni
    boshqaradi.
    """
    database_status: str = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — har qanday DB xatosi degraded hisoblanadi
        logger.exception("Readiness tekshiruvida DB xatosi")
        database_status = "error"

    is_ready = database_status == "ok"
    body = ReadinessResponse(
        status="ready" if is_ready else "degraded",
        database="ok" if is_ready else "error",
    )
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content=body.model_dump(),
    )
