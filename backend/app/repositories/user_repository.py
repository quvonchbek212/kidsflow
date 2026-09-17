"""Foydalanuvchi va rol biriktirmalari uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Collection

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

    async def roles_for(self, user_id: uuid.UUID) -> set[str]:
        """Foydalanuvchiga berilgan rol nomlari (muddatidan qat'i nazar)."""
        stmt = select(UserRoleAssignment.role).where(
            UserRoleAssignment.user_id == user_id
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def branch_ids_for(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        """Foydalanuvchi biriktirilgan filiallar (global rollar hisobga olinmaydi)."""
        stmt = select(UserRoleAssignment.branch_id).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.branch_id.is_not(None),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        # `is_not(None)` filtri tufayli None qolmaydi, lekin ustun turi
        # ixtiyoriy — mypy uchun aniqlashtiramiz.
        return {branch_id for branch_id in rows if branch_id is not None}

    async def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_staff(
        self, branch_ids: Collection[uuid.UUID] | None = None
    ) -> list[User]:
        """Yollanma xodimlar ro'yxati.

        Ikki toifa chiqarib tashlanadi:

        - **PARENT** (vasiylar) — ular `children/parents` bo'limida ko'rsatiladi;
          bu yerda chiqsa ularga oylik hisoblash kabi xodimga xos amallar taklif
          qilinardi.
        - **OWNER** (bog'cha egasi) — u yollanma xodim emas, balki tizim egasi.
          Ilgari u ro'yxatga tushib qolardi va lavozimi sifatida tasodifiy qiymat
          ("Menejer") ko'rinardi.

        Ish haqi fondi ham shu metoddan o'qiydi, shuning uchun jadvaldagi
        qatorlar yig'indisi doim yuqoridagi fond raqamiga teng bo'ladi.

        `branch_ids` berilsa faqat shu filiallarga biriktirilgan rolga ega
        xodimlar qaytariladi. Bo'sh to'plam — "hech bir filial", ya'ni bo'sh
        ro'yxat; `None` esa "filial bo'yicha cheklov yo'q".
        """
        excluded_ids = select(UserRoleAssignment.user_id).where(
            UserRoleAssignment.role.in_([Role.PARENT.value, Role.OWNER.value])
        )
        stmt = (
            select(User)
            .where(User.id.not_in(excluded_ids))
            .order_by(User.created_at.desc())
        )
        if branch_ids is not None:
            branch_staff_ids = select(UserRoleAssignment.user_id).where(
                UserRoleAssignment.branch_id.in_(list(branch_ids))
            )
            stmt = stmt.where(User.id.in_(branch_staff_ids))
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
