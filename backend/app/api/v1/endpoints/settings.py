"""Bog'cha sozlamalari endpointlari (7-bosqich B).

Payme/Click/2FA uchun ATAYLAB hech qanday endpoint/maydon yo'q — loyiha qarori.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.enums import Role
from app.models.organization import KindergartenSettings
from app.schemas.settings import KindergartenSettingsResponse, SettingsUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_response(
    settings: KindergartenSettings, *, full: bool = True
) -> KindergartenSettingsResponse:
    """Sozlamalar javobi.

    `full=False` — ma'muriy maydonlarsiz variant. Bu endpoint hammaga ochiq,
    chunki yon paneldagi bog'cha nomi va sana/pul formati (timezone, currency,
    til) shundan olinadi. Lekin yuridik nom, manzil, telefon, hisob-faktura
    kuni va bildirishnoma sozlamalari — ma'muriy konfiguratsiya: ularni
    tarbiyachiga berishning hojati yo'q (eng kam imtiyoz tamoyili).
    """
    return KindergartenSettingsResponse(
        id=settings.id,
        name=settings.name,
        legal_name=settings.legal_name if full else None,
        address=settings.address if full else None,
        phone=settings.phone if full else None,
        timezone=settings.timezone,
        default_language=settings.default_language,
        currency=settings.currency,
        hours_text=settings.hours_text,
        auto_invoice_day=settings.auto_invoice_day if full else None,
        notification_toggles=(settings.notification_toggles or {}) if full else {},
    )


@router.get(
    "",
    response_model=KindergartenSettingsResponse,
    summary="Bog'cha sozlamalari",
)
async def get_settings(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KindergartenSettingsResponse:
    settings = await SettingsService(session).get()
    return _to_response(
        settings,
        full=current_user.has_any_role(Role.OWNER, Role.MANAGER),
    )


@router.patch(
    "",
    response_model=KindergartenSettingsResponse,
    summary="Bog'cha sozlamalarini tahrirlash (faqat OWNER)",
)
async def update_settings(
    payload: SettingsUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> KindergartenSettingsResponse:
    settings = await SettingsService(session).update(payload, current_user)
    return _to_response(settings)
