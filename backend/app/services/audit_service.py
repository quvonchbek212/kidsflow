"""Audit yozuvlarini yaratish xizmati (11-bo'lim)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        before_data: dict | None = None,
        after_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Audit yozuvini sessiyaga qo'shadi (commit chaqiruvchi tomonda)."""
        self._repo.add(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                actor_user_id=actor_user_id,
                branch_id=branch_id,
                before_data=before_data,
                after_data=after_data,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
