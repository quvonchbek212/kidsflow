"""Telegram taklif kodi va hisobni bog'lash xizmati (7-bo'lim).

Xavfsiz jarayon:
1. menejer parent profilini yaratadi (child_service.add_guardian);
2. backend qisqa muddatli, bir martalik taklif kodini yaratadi;
3. ota-ona botda kodni yuboradi;
4. backend kod, foydalanuvchi va muddatni tekshiradi;
5. Telegram user ID parent profiliga bog'lanadi;
6. kod ishlatilgan deb belgilanadi.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import Role
from app.models.invitation import TelegramInvitation
from app.repositories.child_repository import ChildRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.user_repository import UserRepository
from app.services.access_service import AccessService
from app.services.audit_service import AuditService


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invitations = InvitationRepository(session)
        self._users = UserRepository(session)
        self._children = ChildRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create_for_parent(
        self, user_id: uuid.UUID, current_user: CurrentUser
    ) -> tuple[str, datetime]:
        """Menejer/OWNER ota-ona uchun taklif kodi yaratadi. (kod, muddat)."""
        if not self._access.is_manager_or_owner(current_user):
            raise PermissionDeniedError("Taklif kodi yaratish uchun ruxsat yo'q.")

        parent = await self._users.get_by_id(user_id)
        if parent is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")
        # Faqat SOF ota-ona hisobi: xodim hisobiga (hatto PARENT roli qo'shilgan
        # bo'lsa ham) Telegram bog'lansa, bot shu xodimning barcha huquqlari
        # bilan token olardi.
        if await self._users.roles_for(user_id) != {Role.PARENT.value}:
            raise ConflictError("Taklif kodi faqat ota-ona hisobiga beriladi.")
        # Menejer ota-onaning kamida bitta farzandini boshqara olishi kerak
        # (o'z filialida yoki hali hech qayerga yozilmagan bola).
        if not current_user.is_owner:
            own_children = await self._children.child_ids_for_guardian(user_id)
            for child_id in own_children:
                if await self._access.can_manage_child(current_user, child_id):
                    break
            else:
                raise PermissionDeniedError(
                    "Bu ota-ona sizning filialingizga tegishli emas."
                )

        settings = get_settings()
        code = secrets.token_urlsafe(6)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.invitation_ttl_minutes
        )
        self._invitations.add(
            TelegramInvitation(
                user_id=user_id,
                code_hash=_hash_code(code),
                expires_at=expires_at,
                created_by=current_user.id,
            )
        )
        await self._session.flush()
        self._audit.record(
            action="TELEGRAM_INVITATION_CREATED",
            entity_type="user",
            entity_id=user_id,
            actor_user_id=current_user.id,
        )
        return code, expires_at

    async def link_telegram(
        self,
        code: str,
        telegram_user_id: int,
        telegram_chat_id: int | None,
    ) -> tuple[uuid.UUID, str]:
        """Bot chaqiradi: kod bo'yicha Telegram hisobini profilga bog'laydi."""
        invitation = await self._invitations.get_active_by_hash(_hash_code(code))
        if invitation is None:
            raise NotFoundError("Kod yaroqsiz yoki muddati o'tgan.")

        parent = await self._users.get_by_id(invitation.user_id)
        if parent is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")

        parent.telegram_user_id = telegram_user_id
        parent.telegram_chat_id = telegram_chat_id
        invitation.used_at = datetime.now(UTC)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            # telegram_user_id boshqa foydalanuvchiga bog'langan.
            raise ConflictError(
                "Bu Telegram hisobi allaqachon boshqa profilga bog'langan."
            ) from exc

        self._audit.record(
            action="TELEGRAM_LINKED",
            entity_type="user",
            entity_id=parent.id,
            actor_user_id=parent.id,
        )
        return parent.id, parent.full_name
