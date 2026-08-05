"""Dastlabki sozlash xizmati (4.1-bo'lim).

Setup faqat baza hali sozlanmagan bo'lsa ishlaydi, bir martalik SETUP_TOKEN ni
talab qiladi va bitta transaction ichida OWNER + birinchi filialni yaratadi.
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    InvalidSetupTokenError,
    SetupAlreadyCompletedError,
)
from app.core.security import hash_password
from app.models.enums import Role
from app.models.organization import Branch, KindergartenSettings
from app.models.user import User, UserRoleAssignment
from app.repositories.branch_repository import BranchRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.setup import SetupRequest, SetupResponse
from app.services.audit_service import AuditService


class SetupService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings_repo = SettingsRepository(session)
        self._branch_repo = BranchRepository(session)
        self._user_repo = UserRepository(session)
        self._audit = AuditService(session)

    async def run(
        self,
        data: SetupRequest,
        provided_token: str,
        expected_token: str,
    ) -> SetupResponse:
        # 1. Token tekshiruvi (doimiy vaqtli solishtirish).
        if not hmac.compare_digest(provided_token, expected_token):
            raise InvalidSetupTokenError()

        # 2. Baza allaqachon sozlanganmi? (setup faqat bir marta ishlaydi)
        if await self._settings_repo.exists():
            raise SetupAlreadyCompletedError()

        # 3. Sozlamalar.
        settings = KindergartenSettings(
            name=data.kindergarten.name,
            legal_name=data.kindergarten.legal_name,
            address=data.kindergarten.address,
            phone=data.kindergarten.phone,
            timezone=data.timezone,
            default_language=data.default_language,
            currency=data.currency,
            setup_completed_at=datetime.now(UTC),
        )
        self._settings_repo.add(settings)

        # 4. Birinchi filial.
        branch = Branch(
            name=data.branch.name,
            address=data.branch.address,
            phone=data.branch.phone,
            capacity=data.branch.capacity,
        )
        self._branch_repo.add(branch)

        # 5. OWNER hisobi.
        if await self._user_repo.username_exists(data.owner.username):
            raise ConflictError("Bu login allaqachon band.")
        owner = User(
            full_name=data.owner.full_name,
            username=data.owner.username,
            phone=data.owner.phone,
            email=data.owner.email,
            password_hash=hash_password(data.owner.password),
            preferred_language=data.default_language,
        )
        self._user_repo.add(owner)
        await self._session.flush()  # id larni olish uchun

        # 6. OWNER roli (branch_id yo'q — global).
        assignment = UserRoleAssignment(
            user_id=owner.id,
            role=Role.OWNER.value,
            branch_id=None,
        )
        self._user_repo.add_role_assignment(assignment)

        # 7. Audit.
        self._audit.record(
            action="SETUP_COMPLETED",
            entity_type="kindergarten_settings",
            entity_id=settings.id,
            actor_user_id=owner.id,
        )

        return SetupResponse(
            settings_id=settings.id,
            branch_id=branch.id,
            owner_id=owner.id,
        )
