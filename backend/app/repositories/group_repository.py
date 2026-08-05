"""Guruhlar va guruh tarbiyachilari uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupTeacher


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, group: Group) -> None:
        self._session.add(group)

    def add_teacher(self, link: GroupTeacher) -> None:
        self._session.add(link)

    async def get_by_id(self, group_id: uuid.UUID) -> Group | None:
        return await self._session.get(Group, group_id)

    async def list_by_branches(self, branch_ids: Sequence[uuid.UUID]) -> list[Group]:
        if not branch_ids:
            return []
        stmt = select(Group).where(Group.branch_id.in_(branch_ids)).order_by(Group.name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_all(self) -> list[Group]:
        stmt = select(Group).order_by(Group.name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def group_ids_for_teacher(
        self, teacher_user_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Tarbiyachi biriktirilgan guruhlar (2.3-bo'lim: group_teachers aloqasi)."""
        stmt = select(GroupTeacher.group_id).where(
            GroupTeacher.teacher_user_id == teacher_user_id
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def teacher_link_exists(
        self, group_id: uuid.UUID, teacher_user_id: uuid.UUID
    ) -> bool:
        stmt = (
            select(GroupTeacher.id)
            .where(
                GroupTeacher.group_id == group_id,
                GroupTeacher.teacher_user_id == teacher_user_id,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None
