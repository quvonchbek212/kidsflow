"""Bog'cha sozlamalari biznes xizmati (7-bosqich B).

Payme/Click/2FA uchun ATAYLAB hech qanday maydon/mantiq yo'q — loyiha qarori.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.organization import KindergartenSettings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import SettingsUpdateRequest
from app.services.audit_service import AuditService


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SettingsRepository(session)
        self._audit = AuditService(session)

    async def get(self) -> KindergartenSettings:
        settings = await self._settings.get()
        if settings is None:
            raise NotFoundError("Bog'cha sozlamalari topilmadi — /setup bajarilmagan.")
        return settings

    async def update(
        self, data: SettingsUpdateRequest, current_user: CurrentUser
    ) -> KindergartenSettings:
        if not current_user.is_owner:
            raise PermissionDeniedError("Sozlamalarni faqat OWNER o'zgartiradi.")

        settings = await self.get()
        fields = data.model_dump(exclude_unset=True)

        if "notification_toggles" in fields:
            toggles = fields.pop("notification_toggles")
            merged = dict(settings.notification_toggles or {})
            merged.update(toggles)
            settings.notification_toggles = merged

        for field, value in fields.items():
            setattr(settings, field, value)

        self._audit.record(
            action="SETTINGS_UPDATED",
            entity_type="kindergarten_settings",
            entity_id=settings.id,
            actor_user_id=current_user.id,
        )
        return settings
