"""Kunlik texnik tozalash (worker).

- `refresh_tokens`, `password_reset_tokens`: muddati o'tgan yoki ishlatilgani
  darhol o'chadi — ular hech narsaga yaramaydi.
- `notifications` (SENT/FAILED) va `outbox_events` (PROCESSED/FAILED):
  `notification_retention_days` (90) kundan eskilari. Kutayotganlariga tegilmaydi.
- `audit_logs`: `audit_retention_days` (365) kundan eskilari.

Muddatlar egasi bilan kelishilgan (2026-09-17); `.env` orqali o'zgartiriladi.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import Executable, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.audit import AuditLog
from app.models.enums import NotificationStatus, OutboxStatus
from app.models.messaging import Notification, OutboxEvent
from app.repositories.messaging_repository import DailyJobRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.utils.timezone import today_local

logger = logging.getLogger(__name__)

_JOB_NAME = "maintenance"


async def run_daily(session: AsyncSession) -> int:
    """Eskirgan tokenlarni o'chiradi (kuniga bir marta). O'chirilganlar soni."""
    if not await DailyJobRepository(session).try_claim(_JOB_NAME, today_local()):
        return 0
    now = datetime.now(UTC)
    settings = get_settings()
    removed = await RefreshTokenRepository(session).delete_stale(now)
    removed += await PasswordResetRepository(session).delete_stale(now)

    if settings.notification_retention_days > 0:
        cutoff = now - timedelta(days=settings.notification_retention_days)
        removed += await _delete(
            session,
            delete(Notification).where(
                Notification.created_at < cutoff,
                Notification.status.in_(
                    [NotificationStatus.SENT.value, NotificationStatus.FAILED.value]
                ),
            ),
        )
        removed += await _delete(
            session,
            delete(OutboxEvent).where(
                OutboxEvent.created_at < cutoff,
                OutboxEvent.status.in_(
                    [OutboxStatus.PROCESSED.value, OutboxStatus.FAILED.value]
                ),
            ),
        )

    if settings.audit_retention_days > 0:
        cutoff = now - timedelta(days=settings.audit_retention_days)
        removed += await _delete(
            session, delete(AuditLog).where(AuditLog.created_at < cutoff)
        )

    if removed:
        logger.info("Eskirgan tokenlar tozalandi", extra={"removed": removed})
    return removed


async def _delete(session: AsyncSession, stmt: Executable) -> int:
    result = await session.execute(stmt)
    return int(getattr(result, "rowcount", 0) or 0)
