"""Bilim bazasi (RAG manba) boshqaruvi (10.2-bo'lim)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.ai import KnowledgeDocument
from app.models.enums import Role
from app.repositories.ai_repository import KnowledgeRepository
from app.repositories.branch_repository import BranchRepository
from app.schemas.ai import KnowledgeDocumentCreateRequest
from app.services.access_service import AccessService
from app.services.audit_service import AuditService


class KnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._knowledge = KnowledgeRepository(session)
        self._branches = BranchRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self, data: KnowledgeDocumentCreateRequest, current_user: CurrentUser
    ) -> KnowledgeDocument:
        if not self._access.is_manager_or_owner(current_user):
            raise PermissionDeniedError("Bilim hujjati yaratish uchun ruxsat yo'q.")
        # Filialga xos hujjat bo'lsa, o'sha filialga kirish tekshiriladi.
        if data.branch_id is not None:
            if not self._access.can_manage_branch(current_user, data.branch_id):
                raise PermissionDeniedError("Bu filialga hujjat qo'shib bo'lmaydi.")
            if await self._branches.get_by_id(data.branch_id) is None:
                raise NotFoundError("Filial topilmadi.")

        doc = KnowledgeDocument(
            branch_id=data.branch_id,
            category=data.category.value,
            title=data.title,
            content=data.content,
            created_by=current_user.id,
        )
        self._knowledge.add(doc)
        await self._session.flush()
        self._audit.record(
            action="KNOWLEDGE_DOCUMENT_CREATED",
            entity_type="knowledge_document",
            entity_id=doc.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
        )
        return doc

    async def list_visible(self, current_user: CurrentUser) -> list[KnowledgeDocument]:
        if current_user.is_owner:
            branch_ids = [b.id for b in await self._branches.list_all()]
        else:
            branch_ids = list(current_user.branches_for(Role.MANAGER))
        return await self._knowledge.list_active(branch_ids)
