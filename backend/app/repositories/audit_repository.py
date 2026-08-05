"""Audit jurnali yozuvlari uchun DB so'rovlari."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, log: AuditLog) -> None:
        self._session.add(log)
