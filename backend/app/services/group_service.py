"""Guruh va guruh tarbiyachisi biznes xizmati."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import Role
from app.models.group import Group, GroupTeacher
from app.repositories.branch_repository import BranchRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.schemas.group import (
    GroupCreateRequest,
    GroupTeacherAssignRequest,
    GroupUpdateRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService


class GroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._groups = GroupRepository(session)
        self._branches = BranchRepository(session)
        self._users = UserRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self, data: GroupCreateRequest, current_user: CurrentUser
    ) -> Group:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda guruh yaratish huquqi yo'q.")
        if await self._branches.get_by_id(data.branch_id) is None:
            raise NotFoundError("Filial topilmadi.")

        group = Group(
            branch_id=data.branch_id,
            name=data.name,
            min_age_months=data.min_age_months,
            max_age_months=data.max_age_months,
            capacity=data.capacity,
            monthly_fee=data.monthly_fee,
            room_number=data.room_number,
        )
        self._groups.add(group)
        await self._session.flush()
        self._audit.record(
            action="GROUP_CREATED",
            entity_type="group",
            entity_id=group.id,
            actor_user_id=current_user.id,
            branch_id=group.branch_id,
            after_data={"name": group.name},
        )
        return await self._reload(group.id)

    async def list_visible(
        self, current_user: CurrentUser, branch_id: uuid.UUID | None = None
    ) -> list[Group]:
        if branch_id is not None and not self._access.can_view_branch(
            current_user, branch_id
        ):
            raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")

        if current_user.is_owner:
            if branch_id is None:
                return await self._groups.list_all()
            return await self._groups.list_by_branches([branch_id])
        if current_user.has_any_role(Role.MANAGER):
            branches = current_user.branches_for(Role.MANAGER)
            if branch_id is not None:
                branches = branches & {branch_id}
            return await self._groups.list_by_branches(list(branches))
        # TEACHER — faqat biriktirilgan guruhlar.
        group_ids = await self._groups.group_ids_for_teacher(current_user.id)
        if not group_ids:
            return []
        stmt = (
            select(Group)
            .where(Group.id.in_(group_ids))
            .order_by(Group.name)
            .options(selectinload(Group.teachers))
        )
        if branch_id is not None:
            stmt = stmt.where(Group.branch_id == branch_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get(self, group_id: uuid.UUID, current_user: CurrentUser) -> Group:
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not await self._access.can_view_group(
            current_user, group.branch_id, group.id
        ):
            raise PermissionDeniedError("Bu guruhga kirish huquqi yo'q.")
        return group

    async def update(
        self,
        group_id: uuid.UUID,
        data: GroupUpdateRequest,
        current_user: CurrentUser,
    ) -> Group:
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not self._access.can_manage_branch(current_user, group.branch_id):
            raise PermissionDeniedError("Bu guruhni tahrirlash huquqi yo'q.")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(group, field, value)
        self._audit.record(
            action="GROUP_UPDATED",
            entity_type="group",
            entity_id=group.id,
            actor_user_id=current_user.id,
            branch_id=group.branch_id,
        )
        return await self._reload(group.id)

    async def assign_teacher(
        self,
        group_id: uuid.UUID,
        data: GroupTeacherAssignRequest,
        current_user: CurrentUser,
    ) -> GroupTeacher:
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not self._access.can_manage_branch(current_user, group.branch_id):
            raise PermissionDeniedError(
                "Bu guruhga tarbiyachi biriktirish huquqi yo'q."
            )

        teacher = await self._users.get_by_id(data.teacher_user_id)
        if teacher is None:
            raise NotFoundError("Tarbiyachi (foydalanuvchi) topilmadi.")
        if not await self._users.role_assignment_exists(teacher.id, Role.TEACHER.value):
            raise ConflictError("Foydalanuvchida TEACHER roli yo'q.")
        if await self._groups.teacher_link_exists(group_id, teacher.id):
            raise ConflictError("Tarbiyachi allaqachon biriktirilgan.")

        link = GroupTeacher(
            group_id=group_id,
            teacher_user_id=teacher.id,
            is_primary=data.is_primary,
        )
        self._groups.add_teacher(link)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Tarbiyachi allaqachon biriktirilgan.") from exc

        self._audit.record(
            action="GROUP_TEACHER_ASSIGNED",
            entity_type="group_teacher",
            entity_id=link.id,
            actor_user_id=current_user.id,
            branch_id=group.branch_id,
        )
        return link

    async def _reload(self, group_id: uuid.UUID) -> Group:
        stmt = (
            select(Group)
            .where(Group.id == group_id)
            .options(selectinload(Group.teachers))
        )
        return (await self._session.execute(stmt)).scalar_one()
