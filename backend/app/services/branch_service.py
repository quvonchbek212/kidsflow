"""Filial biznes xizmati."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import Role
from app.models.organization import Branch
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import BranchCreateRequest, BranchUpdateRequest
from app.services.audit_service import AuditService

# Filialga kirish huquqiga ega bo'lgan rollar (OWNER doimo hammasini ko'radi).
_BRANCH_VIEW_ROLES = (Role.MANAGER, Role.TEACHER)


class BranchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BranchRepository(session)
        self._audit = AuditService(session)

    async def list_for(self, current_user: CurrentUser) -> list[Branch]:
        """OWNER barcha filiallarni, boshqalar faqat biriktirilganini ko'radi."""
        if current_user.is_owner:
            return await self._repo.list_all()
        branch_ids = current_user.branches_for(*_BRANCH_VIEW_ROLES)
        return await self._repo.list_by_ids(list(branch_ids))

    async def get_accessible(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> Branch:
        """Filialni qaytaradi, ammo avval kirish huquqini tekshiradi."""
        if not current_user.can_access_branch(branch_id, *_BRANCH_VIEW_ROLES):
            # Ma'lumot borligini oshkor qilmaslik uchun 403.
            raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")
        branch = await self._repo.get_by_id(branch_id)
        if branch is None:
            raise NotFoundError("Filial topilmadi.")
        return branch

    async def create(
        self, data: BranchCreateRequest, current_user: CurrentUser
    ) -> Branch:
        branch = Branch(
            name=data.name,
            address=data.address,
            phone=data.phone,
            capacity=data.capacity,
        )
        self._repo.add(branch)
        await self._session.flush()
        self._audit.record(
            action="BRANCH_CREATED",
            entity_type="branch",
            entity_id=branch.id,
            actor_user_id=current_user.id,
            branch_id=branch.id,
            after_data={"name": branch.name},
        )
        return branch

    async def update(
        self,
        branch_id: uuid.UUID,
        data: BranchUpdateRequest,
        current_user: CurrentUser,
    ) -> Branch:
        branch = await self._repo.get_by_id(branch_id)
        if branch is None:
            raise NotFoundError("Filial topilmadi.")

        before = {
            "name": branch.name,
            "is_active": branch.is_active,
        }
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(branch, field, value)

        self._audit.record(
            action="BRANCH_UPDATED",
            entity_type="branch",
            entity_id=branch.id,
            actor_user_id=current_user.id,
            branch_id=branch.id,
            before_data=before,
            after_data={"name": branch.name, "is_active": branch.is_active},
        )
        return branch
