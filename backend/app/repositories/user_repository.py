"""Foydalanuvchi va rol biriktirmalari uchun DB so'rovlari."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Role
from app.models.user import User, UserRoleAssignment


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_login(
        self,
        username: str | None,
        phone: str | None,
        email: str | None,
    ) -> User | None:
        """Username, telefon yoki email bo'yicha foydalanuvchini topadi."""
        conditions = []
        if username is not None:
            conditions.append(User.username == username)
        if phone is not None:
            conditions.append(User.phone == phone)
        if email is not None:
            conditions.append(User.email == email)
        if not conditions:
            return None

        stmt = select(User).where(or_(*conditions)).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def username_exists(self, username: str) -> bool:
        stmt = select(User.id).where(User.username == username).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def phone_exists(self, phone: str) -> bool:
        stmt = select(User.id).where(User.phone == phone).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(User.email == email).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    def add(self, user: User) -> None:
        self._session.add(user)

    def add_role_assignment(self, assignment: UserRoleAssignment) -> None:
        self._session.add(assignment)

    async def role_assignment_exists(self, user_id: uuid.UUID, role: str) -> bool:
        stmt = (
            select(UserRoleAssignment.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role == role,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_staff(self) -> list[User]:
        """Faqat xodimlar — roli PARENT bo'lganlar (vasiylar) chiqarib tashlanadi.

        Vasiylar `children/parents` bo'limida ko'rsatiladi; "Xodimlar" ro'yxatida
        ular chiqmasligi kerak (aks holda ularga oylik hisoblash kabi xodimga
        xos amallar taklif qilinadi).
        """
        parent_ids = select(UserRoleAssignment.user_id).where(
            UserRoleAssignment.role == Role.PARENT.value
        )
        stmt = (
            select(User)
            .where(User.id.not_in(parent_ids))
            .order_by(User.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_parents(self) -> list[User]:
        """PARENT roliga ega barcha foydalanuvchilar (Ota-onalar bo'limi)."""
        stmt = (
            select(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(UserRoleAssignment.role == Role.PARENT.value)
            .distinct()
            .order_by(User.full_name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def names_by_ids(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """Foydalanuvchi ID → to'liq ism xaritasi (vasiy nomlari uchun)."""
        if not user_ids:
            return {}
        stmt = select(User.id, User.full_name).where(User.id.in_(user_ids))
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}
