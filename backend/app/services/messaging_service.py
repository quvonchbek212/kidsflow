"""Ommaviy xabar yuborish va xabar statistikasi (7-bosqich B).

Avtomatik bildirishnomalardan farqli o'laroq (`notification_scheduler.py` +
`OutboxProcessor`), ommaviy xabar matni yuborish vaqtida allaqachon tayyor —
shu sabab OutboxEvent orqali emas, to'g'ridan-to'g'ri `Notification` qatori
sifatida yoziladi; workerning `dispatch_notifications()` uni avtomatik yuboradi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    Role,
)
from app.models.messaging import Notification
from app.repositories.child_repository import ChildRepository, EnrollmentRepository
from app.repositories.finance_repository import InvoiceRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.messaging_repository import NotificationRepository
from app.schemas.messaging import BroadcastCreateRequest, MessagingStatsResponse
from app.services.audit_service import AuditService


class MessagingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._children = ChildRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._groups = GroupRepository(session)
        self._invoices = InvoiceRepository(session)
        self._notifications = NotificationRepository(session)
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
        return await self._enrollments.child_ids_in_branches([data.branch_id])

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

        child_ids = await self._enrollments.child_ids_in_branches([branch_id])
        targets = await self._children.notifiable_guardian_targets_for_children(
            child_ids
        )
        user_ids = [user_id for user_id, _ in targets]

        month_start = datetime.now(UTC).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        sent_this_month = await self._notifications.count_sent_for_users_since(
            user_ids, month_start
        )
        return MessagingStatsResponse(
            connected_families=len(user_ids),
            sent_this_month=sent_this_month,
        )
