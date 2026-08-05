"""Outbox hodisalarini qayta ishlash va bildirishnomalarni yuborish (9-bo'lim).

Ikki bosqich:
1. `process_outbox` — PENDING outbox hodisalaridan bildirishnoma yozuvlari
   yaratadi va hodisani PROCESSED qiladi (ishonchli hand-off).
2. `dispatch_notifications` — PENDING bildirishnomalarni Telegram orqali yuboradi
   va holatini yangilaydi (retry bilan).

Ajratish Telegram vaqtincha ishlamasa ham yozuvlar yo'qolmasligini ta'minlaydi.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    OutboxStatus,
)
from app.models.messaging import Notification, OutboxEvent
from app.repositories.child_repository import ChildRepository
from app.repositories.daily_report_repository import DailyReportRepository
from app.repositories.finance_repository import InvoiceRepository
from app.repositories.messaging_repository import (
    NotificationRepository,
    OutboxRepository,
)
from app.repositories.settings_repository import SettingsRepository
from app.services.attendance_service import CHILD_CHECKED_IN, CHILD_SICK
from app.services.daily_report_service import DAILY_REPORT_PUBLISHED
from app.services.notification_scheduler import (
    BIRTHDAY_GREETING,
    DEBT_WARNING,
    PAYMENT_REMINDER,
)
from app.services.payment_service import PAYMENT_RECORDED
from app.services.telegram_sender import TelegramSender
from app.utils.money import money

logger = logging.getLogger(__name__)

# 7-bosqich B: shu turlar `notification_toggles` orqali yoqilgan/o'chirilgan
# bo'lishi mumkin (standart — yoqilgan, kalit topilmasa ham).
_TOGGLEABLE_TYPES = frozenset(
    {CHILD_CHECKED_IN, CHILD_SICK, PAYMENT_REMINDER, DEBT_WARNING, BIRTHDAY_GREETING}
)


class OutboxProcessor:
    def __init__(self, session: AsyncSession, sender: TelegramSender) -> None:
        self._session = session
        self._sender = sender
        self._outbox = OutboxRepository(session)
        self._notifications = NotificationRepository(session)
        self._children = ChildRepository(session)
        self._reports = DailyReportRepository(session)
        self._invoices = InvoiceRepository(session)
        self._settings = SettingsRepository(session)
        self._toggles: dict[str, bool] | None = None

    async def _is_enabled(self, event_type: str) -> bool:
        if event_type not in _TOGGLEABLE_TYPES:
            return True
        if self._toggles is None:
            settings = await self._settings.get()
            self._toggles = (settings.notification_toggles or {}) if settings else {}
        return self._toggles.get(event_type, True)

    async def process_outbox(self, limit: int = 50) -> int:
        """PENDING outbox hodisalaridan bildirishnoma yaratadi."""
        events = await self._outbox.fetch_pending(limit)
        for event in events:
            try:
                await self._handle_event(event)
                event.status = OutboxStatus.PROCESSED.value
                event.processed_at = datetime.now(UTC)
            except Exception:  # noqa: BLE001 — hodisa qayta urinishga qoladi
                logger.exception("Outbox hodisasini qayta ishlashda xatolik")
                event.retry_count += 1
                if event.retry_count >= get_settings().outbox_max_retries:
                    event.status = OutboxStatus.FAILED.value
        await self._session.flush()
        return len(events)

    async def dispatch_notifications(self, limit: int = 50) -> int:
        """PENDING bildirishnomalarni yuboradi va holatini yangilaydi."""
        pending = await self._notifications.fetch_pending(limit)
        for notification in pending:
            text = str(notification.payload.get("text", ""))
            chat_id = notification.target_chat_id
            sent = False
            if chat_id is not None:
                sent = await self._sender.send(chat_id, text)
            if sent:
                notification.status = NotificationStatus.SENT.value
                notification.sent_at = datetime.now(UTC)
            else:
                notification.retry_count += 1
        await self._session.flush()
        return len(pending)

    async def run_once(self, limit: int = 50) -> tuple[int, int]:
        processed = await self.process_outbox(limit)
        dispatched = await self.dispatch_notifications(limit)
        return processed, dispatched

    # --- hodisa turlari ---

    async def _handle_event(self, event: OutboxEvent) -> None:
        if event.event_type in _TOGGLEABLE_TYPES and not await self._is_enabled(
            event.event_type
        ):
            return  # Bu tur o'chirilgan — jim o'tkazib yuboriladi (PROCESSED bo'ladi).

        if event.event_type == DAILY_REPORT_PUBLISHED:
            await self._handle_daily_report_published(event)
        elif event.event_type == PAYMENT_RECORDED:
            await self._handle_payment_recorded(event)
        elif event.event_type == CHILD_CHECKED_IN:
            await self._handle_child_checked_in(event)
        elif event.event_type == CHILD_SICK:
            await self._handle_child_sick(event)
        elif event.event_type == PAYMENT_REMINDER:
            await self._handle_payment_reminder(event)
        elif event.event_type == DEBT_WARNING:
            await self._handle_debt_warning(event)
        elif event.event_type == BIRTHDAY_GREETING:
            await self._handle_birthday_greeting(event)
        else:
            logger.warning(
                "Noma'lum outbox hodisa turi", extra={"event_type": event.event_type}
            )

    async def _handle_daily_report_published(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        report_id = event.payload.get("daily_report_id", "")
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        text = f"{child_name} uchun kunlik hisobot tayyor."

        targets = await self._children.notifiable_guardian_targets(child_id)
        for user_id, chat_id in targets:
            self._notifications.add(
                Notification(
                    user_id=user_id,
                    channel=NotificationChannel.TELEGRAM.value,
                    notification_type=NotificationType.DAILY_REPORT.value,
                    payload={"text": text, "daily_report_id": report_id},
                    target_chat_id=chat_id,
                    status=NotificationStatus.PENDING.value,
                )
            )

    async def _handle_payment_recorded(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        amount = event.payload.get("amount", "")
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        text = f"{child_name} uchun {amount} so'm to'lov qabul qilindi. Rahmat!"

        targets = await self._children.notifiable_guardian_targets(child_id)
        for user_id, chat_id in targets:
            self._notifications.add(
                Notification(
                    user_id=user_id,
                    channel=NotificationChannel.TELEGRAM.value,
                    notification_type=NotificationType.PAYMENT_RECEIVED.value,
                    payload={
                        "text": text,
                        "payment_id": event.payload.get("payment_id", ""),
                    },
                    target_chat_id=chat_id,
                    status=NotificationStatus.PENDING.value,
                )
            )

    async def _notify_guardians(
        self, child_id: uuid.UUID, notification_type: str, text: str, extra: dict
    ) -> None:
        """5 ta yangi bildirishnoma turi uchun umumiy yordamchi (7-bosqich B)."""
        targets = await self._children.notifiable_guardian_targets(child_id)
        for user_id, chat_id in targets:
            self._notifications.add(
                Notification(
                    user_id=user_id,
                    channel=NotificationChannel.TELEGRAM.value,
                    notification_type=notification_type,
                    payload={"text": text, **extra},
                    target_chat_id=chat_id,
                    status=NotificationStatus.PENDING.value,
                )
            )

    async def _handle_child_checked_in(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        text = f"{child_name} bog'chaga keldi."
        await self._notify_guardians(
            child_id, NotificationType.CHILD_CHECKED_IN.value, text, {}
        )

    async def _handle_child_sick(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        text = f"{child_name} bugun kasal deb belgilandi."
        await self._notify_guardians(
            child_id, NotificationType.CHILD_SICK.value, text, {}
        )

    async def _handle_payment_reminder(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        amount = money(event.payload.get("amount", 0))
        text = f"{child_name} uchun {amount} so'm qoldiq to'lov bor. Iltimos, to'lovni amalga oshiring."
        await self._notify_guardians(
            child_id,
            NotificationType.PAYMENT_REMINDER.value,
            text,
            {"amount": str(amount)},
        )

    async def _handle_debt_warning(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        amount = money(event.payload.get("amount", 0))
        days_late = event.payload.get("days_late", 0)
        text = (
            f"{child_name} uchun {amount} so'm qarz {days_late} kundan beri "
            "to'lanmagan. Iltimos, tezroq to'lovni amalga oshiring."
        )
        await self._notify_guardians(
            child_id,
            NotificationType.DEBT_WARNING.value,
            text,
            {"amount": str(amount), "days_late": days_late},
        )

    async def _handle_birthday_greeting(self, event: OutboxEvent) -> None:
        child_id = uuid.UUID(event.payload["child_id"])
        child = await self._children.get_by_id(child_id)
        child_name = child.full_name if child else "Bola"
        text = f"{child_name}ni tug'ilgan kuni bilan tabriklaymiz! 🎉"
        await self._notify_guardians(
            child_id, NotificationType.BIRTHDAY_GREETING.value, text, {}
        )
