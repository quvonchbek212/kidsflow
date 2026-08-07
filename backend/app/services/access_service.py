"""Bola va guruhga kirish huquqini DB aloqalari orqali tekshiruvchi qatlam.

Ruxsatlar backend darajasida tekshiriladi (2.3-bo'lim). Bu yerda quyidagi
qoidalar amalga oshiriladi (3-bo'lim rollari):

- OWNER: hamma narsani ko'radi.
- MANAGER: o'z filial(lar)idagi operatsiyalar (enrollment, davomat, guruh).
- TEACHER: faqat biriktirilgan guruhlaridagi bolalar.
- PARENT: faqat vasiy sifatida biriktirilgan bolalar.

Eslatma: `children` jadvali filialga bog'lanmagan (5.3-bo'lim) — bola filialga
enrollment orqali bog'lanadi. Shu sabab OWNER/MANAGER bola profilini ko'ra oladi,
ammo filialga bog'liq amallar (enrollment/davomat/guruh) qat'iy filial tekshiruvidan
o'tadi.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.models.enums import Role
from app.repositories.child_repository import (
    ChildRepository,
    EnrollmentRepository,
)
from app.repositories.group_repository import GroupRepository


class AccessService:
    def __init__(self, session: AsyncSession) -> None:
        self._groups = GroupRepository(session)
        self._children = ChildRepository(session)
        self._enrollments = EnrollmentRepository(session)

    def is_manager_or_owner(self, user: CurrentUser) -> bool:
        return user.is_owner or user.has_any_role(Role.MANAGER)

    async def visible_child_ids(
        self, user: CurrentUser, branch_id: uuid.UUID | None = None
    ) -> list[uuid.UUID] | None:
        """Foydalanuvchi ko'ra oladigan bola ID'lari. None = barcha bolalar.

        `branch_id` berilsa natija shu filialda enrollmenti bor bolalar bilan
        kesishtiriladi. Bola filialga enrollment orqali bog'langani uchun
        (5.3-bo'lim) filtr `children` ustuni bo'yicha emas, shu aloqa bo'yicha
        ishlaydi.
        """
        by_role: set[uuid.UUID] | None = None
        if not self.is_manager_or_owner(user):
            by_role = set()
            if user.has_any_role(Role.TEACHER):
                group_ids = await self._groups.group_ids_for_teacher(user.id)
                by_role.update(await self._enrollments.child_ids_in_groups(group_ids))
            if user.has_any_role(Role.PARENT):
                by_role.update(await self._children.child_ids_for_guardian(user.id))

        if branch_id is None:
            return None if by_role is None else list(by_role)

        in_branch = set(await self._enrollments.child_ids_in_branches([branch_id]))
        return list(in_branch if by_role is None else in_branch & by_role)

    async def can_view_child(self, user: CurrentUser, child_id: uuid.UUID) -> bool:
        if self.is_manager_or_owner(user):
            return True
        visible = await self.visible_child_ids(user)
        return visible is not None and child_id in set(visible)

    async def can_mark_attendance_for_child(
        self, user: CurrentUser, child_id: uuid.UUID, branch_id: uuid.UUID
    ) -> bool:
        """Davomatni faqat OWNER, filial MANAGER'i yoki bolaning TEACHER'i belgilaydi."""
        if user.is_owner:
            return True
        if user.has_any_role(Role.MANAGER) and branch_id in user.branches_for(
            Role.MANAGER
        ):
            return True
        if user.has_any_role(Role.TEACHER):
            group_ids = await self._groups.group_ids_for_teacher(user.id)
            teacher_children = set(
                await self._enrollments.child_ids_in_groups(group_ids)
            )
            if child_id in teacher_children:
                return True
        return False

    def can_manage_branch(self, user: CurrentUser, branch_id: uuid.UUID) -> bool:
        """OWNER yoki shu filialning MANAGER'i (filialga tegishli yozuv amallari)."""
        return user.can_access_branch(branch_id, Role.MANAGER)

    def can_view_branch(self, user: CurrentUser, branch_id: uuid.UUID) -> bool:
        """Filial kesimida ro'yxat so'rash huquqi (o'qish amallari).

        `can_manage_branch`dan farqi — TEACHER ham o'z filialini so'ray oladi;
        u baribir faqat o'z guruhlaridagi bolalarni ko'radi, filial parametri
        shunchaki ro'yxatni yanada toraytiradi.
        """
        return user.can_access_branch(branch_id, Role.MANAGER, Role.TEACHER)

    async def can_view_group(
        self, user: CurrentUser, group_branch_id: uuid.UUID, group_id: uuid.UUID
    ) -> bool:
        if user.can_access_branch(group_branch_id, Role.MANAGER):
            return True
        # Tarbiyachi o'ziga biriktirilgan guruhni ko'radi.
        if user.has_any_role(Role.TEACHER):
            return await self._groups.teacher_link_exists(group_id, user.id)
        return False
