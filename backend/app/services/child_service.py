"""Bola va vasiy biznes xizmati."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.child import Child, ChildGuardian
from app.models.enums import EnrollmentStatus, Role
from app.models.user import User, UserRoleAssignment
from app.repositories.child_repository import ChildRepository, EnrollmentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.child import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    GuardianCreateRequest,
    GuardianSummary,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils.encryption import decrypt_text, encrypt_text


class ChildService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._children = ChildRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._users = UserRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self, data: ChildCreateRequest, current_user: CurrentUser
    ) -> Child:
        self._require_manage(current_user)
        child = Child(
            full_name=data.full_name,
            birth_date=data.birth_date,
            gender=data.gender.value if data.gender else None,
            medical_notes_encrypted=encrypt_text(data.medical_notes),
        )
        self._children.add(child)
        await self._session.flush()
        self._audit.record(
            action="CHILD_CREATED",
            entity_type="child",
            entity_id=child.id,
            actor_user_id=current_user.id,
            after_data={"full_name": child.full_name},
        )
        return await self._reload(child.id)

    async def get(self, child_id: uuid.UUID, current_user: CurrentUser) -> Child:
        if not await self._access.can_view_child(current_user, child_id):
            raise PermissionDeniedError("Bu bola ma'lumotiga kirish huquqi yo'q.")
        child = await self._children.get_loaded(child_id)
        if child is None:
            raise NotFoundError("Bola topilmadi.")
        return child

    async def list_visible(self, current_user: CurrentUser) -> list[Child]:
        visible = await self._access.visible_child_ids(current_user)
        if visible is None:
            # OWNER/MANAGER — barcha bolalar.
            return await self._children.list_all()
        return await self._children.list_by_ids(visible)

    async def update(
        self,
        child_id: uuid.UUID,
        data: ChildUpdateRequest,
        current_user: CurrentUser,
    ) -> Child:
        self._require_manage(current_user)
        child = await self._children.get_by_id(child_id)
        if child is None:
            raise NotFoundError("Bola topilmadi.")

        fields = data.model_dump(exclude_unset=True)
        if "gender" in fields:
            child.gender = data.gender.value if data.gender else None
            fields.pop("gender")
        if "medical_notes" in fields:
            child.medical_notes_encrypted = encrypt_text(data.medical_notes)
            fields.pop("medical_notes")
        for field, value in fields.items():
            setattr(child, field, value)

        self._audit.record(
            action="CHILD_UPDATED",
            entity_type="child",
            entity_id=child.id,
            actor_user_id=current_user.id,
        )
        await self._session.flush()
        return await self._reload(child.id)

    async def add_guardian(
        self,
        child_id: uuid.UUID,
        data: GuardianCreateRequest,
        current_user: CurrentUser,
    ) -> ChildGuardian:
        self._require_manage(current_user)
        child = await self._children.get_by_id(child_id)
        if child is None:
            raise NotFoundError("Bola topilmadi.")

        # Mavjud foydalanuvchini topamiz yoki yangi PARENT yaratamiz.
        guardian = await self._users.get_by_login(None, data.phone, data.email)
        if guardian is None:
            guardian = User(
                full_name=data.full_name,
                phone=data.phone,
                email=data.email,
                password_hash=None,  # ota-ona Telegram orqali kiradi
            )
            self._users.add(guardian)
            await self._session.flush()

        # PARENT roli mavjud bo'lmasa qo'shamiz (branch'siz — kirish guardian
        # aloqasi orqali boshqariladi).
        if not await self._users.role_assignment_exists(guardian.id, Role.PARENT.value):
            self._users.add_role_assignment(
                UserRoleAssignment(
                    user_id=guardian.id,
                    role=Role.PARENT.value,
                    branch_id=None,
                    assigned_by=current_user.id,
                )
            )

        if await self._children.guardian_link_exists(child_id, guardian.id):
            raise ConflictError("Bu vasiy allaqachon biriktirilgan.")

        link = ChildGuardian(
            child_id=child_id,
            guardian_user_id=guardian.id,
            relationship_type=data.relationship_type.value,
            is_primary=data.is_primary,
            can_pick_up=data.can_pick_up,
            receives_notifications=data.receives_notifications,
        )
        self._children.add_guardian(link)
        await self._session.flush()

        self._audit.record(
            action="GUARDIAN_ADDED",
            entity_type="child_guardian",
            entity_id=link.id,
            actor_user_id=current_user.id,
            after_data={
                "child_id": str(child_id),
                "guardian_user_id": str(guardian.id),
            },
        )
        return link

    # --- yordamchilar ---

    def _require_manage(self, current_user: CurrentUser) -> None:
        if not self._access.is_manager_or_owner(current_user):
            raise PermissionDeniedError("Bu amal uchun MANAGER yoki OWNER kerak.")

    async def _reload(self, child_id: uuid.UUID) -> Child:
        child = await self._children.get_loaded(child_id)
        if child is None:
            raise NotFoundError("Bola topilmadi.")
        return child

    @staticmethod
    def decrypt_medical(child: Child, current_user: CurrentUser) -> str | None:
        """Tibbiy izohni faqat OWNER/MANAGER uchun ochadi."""
        if not (current_user.is_owner or current_user.has_any_role(Role.MANAGER)):
            return None
        return decrypt_text(child.medical_notes_encrypted)

    async def to_response(
        self, child: Child, current_user: CurrentUser
    ) -> ChildResponse:
        """Bir bolani javob sxemasiga aylantiradi (vasiy ismlari bilan)."""
        return (await self.to_responses([child], current_user))[0]

    @staticmethod
    def _project_status(enrollment_status: str | None) -> str:
        """Enrollment holatini mockup'ning active/waiting/left ko'rinishiga o'giradi."""
        if enrollment_status == EnrollmentStatus.PLANNED.value:
            return "waiting"
        if enrollment_status == EnrollmentStatus.ACTIVE.value:
            return "active"
        # PAUSED/COMPLETED/CANCELLED yoki enrollment umuman yo'q → left.
        return "left"

    async def to_responses(
        self, children: list[Child], current_user: CurrentUser
    ) -> list[ChildResponse]:
        """Bolalar ro'yxatini javobga aylantiradi (vasiy ismlarini bitta so'rovda)."""
        guardian_ids = [
            g.guardian_user_id for child in children for g in child.guardians
        ]
        names = await self._users.names_by_ids(list(set(guardian_ids)))
        statuses = await self._enrollments.latest_statuses_for_children(
            [child.id for child in children]
        )

        responses: list[ChildResponse] = []
        for child in children:
            responses.append(
                ChildResponse(
                    id=child.id,
                    full_name=child.full_name,
                    birth_date=child.birth_date,
                    gender=child.gender,
                    medical_notes=self.decrypt_medical(child, current_user),
                    is_active=child.is_active,
                    status=self._project_status(statuses.get(child.id)),
                    guardians=[
                        GuardianSummary(
                            guardian_user_id=g.guardian_user_id,
                            full_name=names.get(g.guardian_user_id, ""),
                            relationship_type=g.relationship_type,
                            is_primary=g.is_primary,
                            can_pick_up=g.can_pick_up,
                            receives_notifications=g.receives_notifications,
                        )
                        for g in child.guardians
                    ],
                )
            )
        return responses

    async def list_parents(self, current_user: CurrentUser) -> list[dict]:
        """Ota-onalar ro'yxati (MANAGER/OWNER): aloqa, Telegram holati, farzandlar."""
        self._require_manage(current_user)
        parents = await self._users.list_parents()
        child_names = await self._children.all_guardian_child_names()
        return [
            {
                "id": p.id,
                "full_name": p.full_name,
                "phone": p.phone,
                "email": p.email,
                "telegram_linked": p.telegram_user_id is not None,
                "children_names": child_names.get(p.id, []),
            }
            for p in parents
        ]
