"""Xodim (foydalanuvchi) biznes xizmati."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.core.security import hash_password
from app.models.enums import Role
from app.models.user import User, UserRoleAssignment
from app.repositories.branch_repository import BranchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import SalaryUpdateRequest, StaffCreateRequest, StaffUpdateRequest
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._branches = BranchRepository(session)
        self._audit = AuditService(session)

    async def create_staff(
        self, data: StaffCreateRequest, current_user: CurrentUser
    ) -> User:
        # Filial mavjudligini tekshirish (filial talab qilinadigan rollar uchun).
        if data.branch_id is not None:
            branch = await self._branches.get_by_id(data.branch_id)
            if branch is None:
                raise NotFoundError("Ko'rsatilgan filial topilmadi.")

        # Takrorlanishni oldindan tekshirish (tushunarli xato uchun).
        if await self._users.username_exists(data.username):
            raise ConflictError("Bu login allaqachon band.")
        if data.phone and await self._users.phone_exists(data.phone):
            raise ConflictError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        if data.email and await self._users.email_exists(data.email):
            raise ConflictError("Bu email allaqachon ro'yxatdan o'tgan.")

        position = data.position.value if data.position else data.role.value
        user = User(
            full_name=data.full_name,
            username=data.username,
            phone=data.phone,
            email=data.email,
            password_hash=hash_password(data.password),
            preferred_language=data.preferred_language,
            position=position,
            monthly_salary=data.monthly_salary,
            birth_date=data.birth_date,
            passport_number=data.passport_number,
            hire_date=data.hire_date,
            employment_type=(
                data.employment_type.value if data.employment_type else None
            ),
        )
        self._users.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Unique constraint poyga holatida (race) himoya sifatida.
            raise ConflictError("Login, telefon yoki email allaqachon band.") from exc

        self._users.add_role_assignment(
            UserRoleAssignment(
                user_id=user.id,
                role=Role(data.role).value,
                branch_id=data.branch_id,
                assigned_by=current_user.id,
            )
        )
        await self._session.flush()

        self._audit.record(
            action="STAFF_CREATED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
            after_data={"role": data.role.value, "full_name": user.full_name},
        )

        # Rollarni selectin bilan to'liq yuklab qaytaramiz (lazy IO'siz).
        stmt = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.role_assignments))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def list_all(self, position: str | None = None) -> list[User]:
        """Xodimlar ro'yxati — vasiylar (PARENT) bu ro'yxatga kirmaydi."""
        users = await self._users.list_staff()
        if position is not None:
            users = [u for u in users if u.position == position]
        return users

    async def update_salary(
        self,
        user_id: uuid.UUID,
        data: SalaryUpdateRequest,
        current_user: CurrentUser,
    ) -> User:
        if not (current_user.is_owner or current_user.has_any_role(Role.MANAGER)):
            raise PermissionDeniedError("Maoshni faqat OWNER/MANAGER o'zgartiradi.")

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Xodim topilmadi.")

        before = str(user.monthly_salary) if user.monthly_salary else None
        user.monthly_salary = data.monthly_salary

        self._audit.record(
            action="SALARY_UPDATED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=current_user.id,
            before_data={"monthly_salary": before},
            after_data={"monthly_salary": str(data.monthly_salary)},
        )
        return user

    async def update_staff(
        self,
        user_id: uuid.UUID,
        data: StaffUpdateRequest,
        current_user: CurrentUser,
    ) -> User:
        if not current_user.is_owner:
            raise PermissionDeniedError("Xodim profilini faqat OWNER tahrirlaydi.")

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Xodim topilmadi.")

        fields = data.model_dump(exclude_unset=True)

        if "phone" in fields and fields["phone"] != user.phone:
            existing = fields["phone"] and await self._users.phone_exists(
                fields["phone"]
            )
            if existing:
                raise ConflictError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        if "email" in fields and fields["email"] != user.email:
            existing = fields["email"] and await self._users.email_exists(
                fields["email"]
            )
            if existing:
                raise ConflictError("Bu email allaqachon ro'yxatdan o'tgan.")

        if "position" in fields:
            position = fields.pop("position")
            user.position = position.value if position else None
        if "employment_type" in fields:
            employment_type = fields.pop("employment_type")
            user.employment_type = employment_type.value if employment_type else None
        for field, value in fields.items():
            setattr(user, field, value)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Telefon yoki email allaqachon band.") from exc

        self._audit.record(
            action="STAFF_UPDATED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=current_user.id,
        )

        stmt = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.role_assignments))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def payroll_summary(self) -> tuple[Decimal, list[User]]:
        # Ish haqi fondi faqat xodimlar bo'yicha — vasiylar hisobga olinmaydi.
        users = [u for u in await self._users.list_staff() if u.is_active]
        total = sum((u.monthly_salary for u in users if u.monthly_salary), Decimal("0"))
        return total, users
