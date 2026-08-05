"""Dastlabki sozlash endpointi (4.1-bo'lim)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.rate_limit import setup_rate_limit
from app.database import get_session
from app.schemas.setup import SetupRequest, SetupResponse
from app.services.setup_service import SetupService

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(
    "",
    response_model=SetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tizimni birinchi marta sozlash",
    dependencies=[Depends(setup_rate_limit)],
)
async def run_setup(
    payload: SetupRequest,
    x_setup_token: str = Header(..., alias="X-Setup-Token"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SetupResponse:
    """OWNER, birinchi filial va bog'cha sozlamalarini bir transaction'da yaratadi.

    Faqat baza hali sozlanmagan bo'lsa va to'g'ri `X-Setup-Token` berilsa ishlaydi.
    """
    service = SetupService(session)
    return await service.run(payload, x_setup_token, settings.setup_token)
