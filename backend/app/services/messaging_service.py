"""Ommaviy xabar yuborish va xabar statistikasi (7-bosqich B).

Avtomatik bildirishnomalardan farqli o'laroq (`notification_scheduler.py` +
`OutboxProcessor`), ommaviy xabar matni yuborish vaqtida allaqachon tayyor —
shu sabab OutboxEvent orqali emas, to'g'ridan-to'g'ri `Notification` qatori
sifatida yoziladi; workerning `dispatch_notifications()` uni avtomatik yuboradi.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import (
    EnrollmentStatus,
    MessageDirection,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    Role,
)
from app.models.messaging import Notification, ParentMessage
from app.repositories.child_repository import ChildRepository, EnrollmentRepository
from app.repositories.finance_repository import InvoiceRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.messaging_repository import (
    BranchNotificationSettingsRepository,
    NotificationRepository,
    ParentMessageRepository,
)
from app.schemas.messaging import (
    BranchNotificationSettingsResponse,
    BranchNotificationSettingsUpdateRequest,
    BroadcastCreateRequest,
    MessageThreadSummary,
    MessagingStatsResponse,
    ParentMessageResponse,
)
from app.services.audit_service import AuditService
from app.services.billing_service import DEFAULT_INVOICE_DUE_DAY
from app.services.notification_scheduler import (
    DEFAULT_DEBT_WARNING_DAYS_LATE,
    DEFAULT_PAYMENT_REMINDER_DAYS_BEFORE,
)
from app.utils.timezone import month_start_utc


class MessagingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._children = ChildRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._groups = GroupRepository(session)
        self._invoices = InvoiceRepository(session)
        self._notifications = NotificationRepository(session)
        self._branch_settings = BranchNotificationSettingsRepository(session)
        self._parent_messages = ParentMessageRepository(session)
        self._audit = AuditService(session)

    async def _target_child_ids(
        self, data: BroadcastCreateRequest, current_user: CurrentUser
    ) -> list[uuid.UUID]:
        if data.audience == "group":
            if data.group_id is None:
                raise PermissionDeniedError(
                    "Guruh auditoriyasi uchun group_id ko'rsatilishi shart."
                )
            group = await self._groups.get_by_id(data.group_id)
            if group is None or group.branch_id != data.branch_id:
                raise NotFoundError("Guruh topilmadi.")
            return await self._enrollments.child_ids_in_groups([data.group_id])
        if data.audience == "debtors":
            outstanding = await self._invoices.list_outstanding_for_branch(
                data.branch_id
            )
            return list({invoice.child_id for invoice in outstanding})
        # Faqat hozir qatnayotgan bolalar: bog'chadan ketgan oilalar
        # ommaviy xabar olmasligi kerak.
        return await self._enrollments.child_ids_in_branches(
            [data.branch_id], statuses=[EnrollmentStatus.ACTIVE.value]
        )

    async def broadcast(
        self, data: BroadcastCreateRequest, current_user: CurrentUser
    ) -> int:
        if not current_user.can_access_branch(data.branch_id, Role.MANAGER):
            raise PermissionDeniedError("Bu filialga xabar yuborish huquqi yo'q.")

        child_ids = await self._target_child_ids(data, current_user)
        targets = await self._children.notifiable_guardian_targets_for_children(
            child_ids
        )

        for user_id, chat_id in targets:
            self._notifications.add(
                Notification(
                    user_id=user_id,
                    channel=NotificationChannel.TELEGRAM.value,
                    notification_type=NotificationType.BROADCAST.value,
                    payload={"text": data.text},
                    target_chat_id=chat_id,
                    status=NotificationStatus.PENDING.value,
                )
            )

        await self._session.flush()
        self._audit.record(
            action="BROADCAST_SENT",
            entity_type="branch",
            entity_id=data.branch_id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"audience": data.audience, "recipients": len(targets)},
        )
        return len(targets)

    async def stats(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> MessagingStatsResponse:
        if not current_user.can_access_branch(branch_id, Role.MANAGER):
            raise PermissionDeniedError("Bu filial statistikasini ko'rish huquqi yo'q.")

        child_ids = await self._enrollments.child_ids_in_branches(
            [branch_id], statuses=[EnrollmentStatus.ACTIVE.value]
        )
        targets = await self._children.notifiable_guardian_targets_for_children(
            child_ids
        )
        user_ids = [user_id for user_id, _ in targets]

        sent_this_month = await self._notifications.count_sent_for_users_since(
            user_ids, month_start_utc()
        )
        return MessagingStatsResponse(
            connected_families=len(user_ids),
            sent_this_month=sent_this_month,
        )

    # --- Filial kesimidagi bildirishnoma sozlamalari ---

    def _require_branch(self, branch_id: uuid.UUID, current_user: CurrentUser) -> None:
        if not current_user.can_access_branch(branch_id, Role.MANAGER):
            raise PermissionDeniedError("Bu filialga ruxsat yo'q.")

    async def get_branch_settings(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> BranchNotificationSettingsResponse:
        self._require_branch(branch_id, current_user)
        config = await self._branch_settings.get(branch_id)
        if config is None:
            # Yozuv hali yo'q — standart qiymatlar qaytariladi. Qator faqat
            # birinchi tahrirda yaratiladi (bo'sh yozuvlar to'planmasin).
            return BranchNotificationSettingsResponse(
                branch_id=branch_id,
                toggles={},
                payment_reminder_days_before=DEFAULT_PAYMENT_REMINDER_DAYS_BEFORE,
                debt_warning_days_late=DEFAULT_DEBT_WARNING_DAYS_LATE,
                invoice_due_day=DEFAULT_INVOICE_DUE_DAY,
            )
        return BranchNotificationSettingsResponse(
            branch_id=config.branch_id,
            toggles=dict(config.toggles or {}),
            payment_reminder_days_before=config.payment_reminder_days_before,
            debt_warning_days_late=config.debt_warning_days_late,
            invoice_due_day=config.invoice_due_day,
        )

    async def update_branch_settings(
        self,
        branch_id: uuid.UUID,
        data: BranchNotificationSettingsUpdateRequest,
        current_user: CurrentUser,
    ) -> BranchNotificationSettingsResponse:
        self._require_branch(branch_id, current_user)
        config = await self._branch_settings.get_or_create(branch_id)

        if data.toggles is not None:
            # Qisman yangilash: frontend bitta kalitni yuborsa qolganlari
            # o'z holicha qoladi.
            merged = dict(config.toggles or {})
            merged.update(data.toggles)
            config.toggles = merged
        if data.payment_reminder_days_before is not None:
            config.payment_reminder_days_before = data.payment_reminder_days_before
        if data.debt_warning_days_late is not None:
            config.debt_warning_days_late = data.debt_warning_days_late
        if data.invoice_due_day is not None:
            config.invoice_due_day = data.invoice_due_day

        await self._session.flush()
        self._audit.record(
            action="NOTIFICATION_SETTINGS_UPDATED",
            entity_type="branch",
            entity_id=branch_id,
            actor_user_id=current_user.id,
            branch_id=branch_id,
            after_data={
                "toggles": dict(config.toggles or {}),
                "payment_reminder_days_before": config.payment_reminder_days_before,
                "debt_warning_days_late": config.debt_warning_days_late,
                "invoice_due_day": config.invoice_due_day,
            },
        )
        return BranchNotificationSettingsResponse(
            branch_id=config.branch_id,
            toggles=dict(config.toggles or {}),
            payment_reminder_days_before=config.payment_reminder_days_before,
            debt_warning_days_late=config.debt_warning_days_late,
            invoice_due_day=config.invoice_due_day,
        )

    # --- Ota-ona ↔ xodim yozishmalari ---

    async def send_from_parent(
        self, guardian_user_id: uuid.UUID, text: str
    ) -> uuid.UUID:
        """Ota-ona botdan yuborgan savolni saqlaydi.

        Filial ota-onaning farzandidan aniqlanadi — ota-ona o'zi filial
        tanlamaydi. Bir nechta farzandi turli filialda bo'lsa, birinchisi
        olinadi: xodim javob berganda suhbat baribir shu filialda ko'rinadi.
        """
        child_ids = await self._children.child_ids_for_guardian(guardian_user_id)
        if not child_ids:
            raise NotFoundError("Sizga biriktirilgan bola topilmadi.")

        branch_id = await self._enrollments.branch_for_child(child_ids[0])
        if branch_id is None:
            raise NotFoundError("Bola filiali aniqlanmadi.")

        message = ParentMessage(
            branch_id=branch_id,
            guardian_user_id=guardian_user_id,
            direction=MessageDirection.IN.value,
            text=text,
        )
        self._parent_messages.add(message)
        await self._session.flush()
        return message.id

    async def list_threads(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> list[MessageThreadSummary]:
        self._require_branch(branch_id, current_user)
        summaries = await self._parent_messages.thread_summaries(branch_id)
        if not summaries:
            return []

        guardian_ids = [row[0] for row in summaries]
        # Uchala qidiruv ham bitta so'rovdan iborat — suhbat boshiga so'rov
        # yubormaslik uchun (N+1).
        profiles = await self._children.user_profiles(guardian_ids)
        child_names = await self._children.child_names_for_guardians(guardian_ids)
        last_texts = await self._parent_messages.last_message_texts(branch_id)

        threads: list[MessageThreadSummary] = []
        for guardian_id, last_at, unread in summaries:
            name, phone = profiles.get(guardian_id, ("—", None))
            threads.append(
                MessageThreadSummary(
                    guardian_user_id=guardian_id,
                    guardian_name=name,
                    guardian_phone=phone,
                    children=child_names.get(guardian_id, []),
                    last_message_at=last_at,
                    last_message_text=last_texts.get(guardian_id, ""),
                    unread_count=int(unread or 0),
                )
            )
        return threads

    async def get_thread(
        self,
        branch_id: uuid.UUID,
        guardian_user_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> list[ParentMessageResponse]:
        self._require_branch(branch_id, current_user)
        messages = await self._parent_messages.list_thread(branch_id, guardian_user_id)
        # Suhbat ochilishi — o'qilgan deb belgilash uchun yetarli signal.
        await self._parent_messages.mark_thread_read(branch_id, guardian_user_id)

        staff_ids = [m.staff_user_id for m in messages if m.staff_user_id is not None]
        staff_profiles = await self._children.user_profiles(staff_ids)
        await self._session.flush()
        return [
            ParentMessageResponse(
                id=m.id,
                direction=m.direction,
                text=m.text,
                created_at=m.created_at,
                read_at=m.read_at,
                staff_name=(
                    staff_profiles[m.staff_user_id][0]
                    if m.staff_user_id in staff_profiles
                    else None
                ),
            )
            for m in messages
        ]

    async def reply_to_parent(
        self,
        branch_id: uuid.UUID,
        guardian_user_id: uuid.UUID,
        text: str,
        current_user: CurrentUser,
    ) -> ParentMessageResponse:
        """Xodim javobi: yozishmaga saqlanadi va Telegramga navbatga qo'yiladi."""
        self._require_branch(branch_id, current_user)

        message = ParentMessage(
            branch_id=branch_id,
            guardian_user_id=guardian_user_id,
            direction=MessageDirection.OUT.value,
            text=text,
            staff_user_id=current_user.id,
        )
        self._parent_messages.add(message)

        chat_id = await self._children.telegram_chat_id_for_user(guardian_user_id)
        if chat_id is not None:
            self._notifications.add(
                Notification(
                    user_id=guardian_user_id,
                    channel=NotificationChannel.TELEGRAM.value,
                    notification_type=NotificationType.STAFF_REPLY.value,
                    payload={"text": text},
                    target_chat_id=chat_id,
                    status=NotificationStatus.PENDING.value,
                )
            )

        await self._session.flush()
        self._audit.record(
            action="PARENT_MESSAGE_REPLIED",
            entity_type="user",
            entity_id=guardian_user_id,
            actor_user_id=current_user.id,
            branch_id=branch_id,
        )
        return ParentMessageResponse(
            id=message.id,
            direction=MessageDirection.OUT.value,
            text=message.text,
            created_at=message.created_at,
            read_at=None,
            staff_name=None,
        )

    async def unread_count(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> int:
        self._require_branch(branch_id, current_user)
        return await self._parent_messages.unread_count(branch_id)
