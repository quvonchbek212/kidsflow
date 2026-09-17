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
    ChildEnrollmentSummary,
    ChildResponse,
    ChildUpdateRequest,
    GuardianCreateRequest,
    GuardianSummary,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils.encryption import decrypt_text, encrypt_text
from app.utils.timezone import today_local


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

    async def list_visible(
        self, current_user: CurrentUser, branch_id: uuid.UUID | None = None
    ) -> list[Child]:
        if branch_id is not None and not self._access.can_view_branch(
            current_user, branch_id
        ):
            raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")
        visible = await self._access.visible_child_ids(current_user, branch_id)
        if visible is None:
            # OWNER/MANAGER, filial ko'rsatilmagan — barcha bolalar.
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
        await self._require_manage_child(child_id, current_user)

        fields = data.model_dump(exclude_unset=True)
        deactivating = fields.get("is_active") is False and child.is_active
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
        if deactivating:
            await self._close_enrollments(child.id, current_user)
        await self._session.flush()
        return await self._reload(child.id)

    async def _close_enrollments(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> None:
        """Faolsizlantirilgan bolaning guruhga yozilishini yopadi.

        Ilgari faolsizlantirish faqat `children.is_active` ni o'zgartirardi,
        enrollment esa ACTIVE qolardi. Avtomatik hisob-faktura va davomat
        enrollmentga qaragani uchun "nofaol" bolaga har oy hisob yozilaverardi.
        Endi faol enrollment bugungi sana bilan yakunlanadi (tarix saqlanadi),
        navbatdagisi esa bekor qilinadi. Joriy oy uchun allaqachon yaratilgan
        hisob-faktura o'zgarmaydi.
        """
        today = today_local()
        for enrollment in await self._enrollments.open_for_child(child_id):
            before = enrollment.status
            if before == EnrollmentStatus.ACTIVE.value:
                enrollment.status = EnrollmentStatus.COMPLETED.value
                enrollment.end_date = max(today, enrollment.start_date)
            else:
                enrollment.status = EnrollmentStatus.CANCELLED.value
            self._audit.record(
                action="ENROLLMENT_UPDATED",
                entity_type="enrollment",
                entity_id=enrollment.id,
                actor_user_id=current_user.id,
                branch_id=enrollment.branch_id,
                before_data={"status": before},
                after_data={
                    "status": enrollment.status,
                    "reason": "child_deactivated",
                },
            )

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
        await self._require_manage_child(child_id, current_user)

        # Mavjud foydalanuvchini topamiz yoki yangi PARENT yaratamiz.
        guardian = await self._users.get_by_login(None, data.phone, data.email)
        # Telefon/email xodimga tegishli bo'lsa vasiy qilinmaydi. Aks holda
        # menejer egasining telefonini yozib, uning hisobiga PARENT roli qo'shar,
        # keyin Telegram taklif kodi orqali o'z Telegramini shu hisobga bog'lab,
        # OWNER huquqlari bilan token olardi.
        if guardian is not None and (
            await self._users.roles_for(guardian.id) - {Role.PARENT.value}
        ):
            raise ConflictError(
                "Bu telefon yoki email xodim hisobiga tegishli — "
                "uni vasiy qilib biriktirib bo'lmaydi."
            )
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

    async def _require_manage_child(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> None:
        if not await self._access.can_manage_child(current_user, child_id):
            raise PermissionDeniedError("Bu bola sizning filialingizga tegishli emas.")

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
        enrollments = await self._enrollments.current_for_children(
            [child.id for child in children]
        )

        responses: list[ChildResponse] = []
        for child in children:
            enrollment = enrollments.get(child.id)
            responses.append(
                ChildResponse(
                    id=child.id,
                    full_name=child.full_name,
                    birth_date=child.birth_date,
                    gender=child.gender,
                    medical_notes=self.decrypt_medical(child, current_user),
                    is_active=child.is_active,
                    status=self._project_status(
                        enrollment.status if enrollment else None
                    ),
                    enrollment=(
                        ChildEnrollmentSummary(
                            id=enrollment.id,
                            group_id=enrollment.group_id,
                            start_date=enrollment.start_date,
                            status=enrollment.status,
                        )
                        if enrollment
                        else None
                    ),
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

    async def list_parents(
        self, current_user: CurrentUser, branch_id: uuid.UUID | None = None
    ) -> list[dict]:
        """Ota-onalar ro'yxati (MANAGER/OWNER): aloqa, Telegram holati, farzandlar.

        `branch_id` berilsa faqat shu filialda farzandi bor ota-onalar
        qaytariladi, va `children_names` ham shu filialdagi farzandlar bilan
        cheklanadi — boshqa filialdagi farzand nomi ko'rinib qolmasligi uchun.
        """
        self._require_manage(current_user)
        if branch_id is not None and not self._access.can_view_branch(
            current_user, branch_id
        ):
            raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")

        parents = await self._users.list_parents()

        # MANAGER filial ko'rsatmasa ham faqat o'z filiallari bilan cheklanadi —
        # ilgari barcha filiallardagi ota-onalarning telefonlari qaytardi.
        scope: list[uuid.UUID] | None
        if branch_id is not None:
            scope = [branch_id]
        elif current_user.is_owner:
            scope = None
        else:
            scope = list(current_user.branches_for(Role.MANAGER))

        if scope is None:
            child_names = await self._children.all_guardian_child_names()
        else:
            in_scope = set(await self._enrollments.child_ids_in_branches(scope))
            child_names = await self._children.guardian_child_names_for_children(
                in_scope
            )
            parents = [p for p in parents if child_names.get(p.id)]

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
