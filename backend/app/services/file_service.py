"""Fayl yuklash va yuklab olish xizmati (11-bo'lim)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import FileScanStatus, Role
from app.models.file import File
from app.repositories.daily_report_repository import DailyReportRepository
from app.repositories.file_repository import FileRepository
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils import file_storage


@dataclass(frozen=True)
class FileDownload:
    content: bytes
    content_type: str
    original_name: str


class FileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._files = FileRepository(session)
        self._reports = DailyReportRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def upload(
        self,
        content: bytes,
        content_type: str,
        original_name: str,
        current_user: CurrentUser,
    ) -> File:
        # Faqat xodimlar (OWNER/MANAGER/TEACHER) fayl yuklaydi.
        if not (
            self._access.is_manager_or_owner(current_user)
            or current_user.has_any_role(Role.TEACHER)
        ):
            raise PermissionDeniedError("Fayl yuklash uchun ruxsat yo'q.")

        stored = file_storage.save_file(content, content_type)
        record = File(
            storage_key=stored.storage_key,
            original_name=original_name[:255],
            content_type=content_type,
            size_bytes=stored.size_bytes,
            checksum=stored.checksum,
            uploaded_by=current_user.id,
            # Haqiqiy AV skani 5-bosqichda; hozircha imzo tekshirildi → CLEAN.
            scan_status=FileScanStatus.CLEAN.value,
        )
        self._files.add(record)
        await self._session.flush()
        self._audit.record(
            action="FILE_UPLOADED",
            entity_type="file",
            entity_id=record.id,
            actor_user_id=current_user.id,
        )
        return record

    async def download(
        self, file_id: uuid.UUID, current_user: CurrentUser
    ) -> FileDownload:
        record = await self._files.get_by_id(file_id)
        if record is None:
            raise NotFoundError("Fayl topilmadi.")

        if not await self._can_access(record, current_user):
            raise PermissionDeniedError("Bu faylga kirish huquqi yo'q.")

        try:
            content = file_storage.read_file(record.storage_key)
        except FileNotFoundError as exc:
            raise NotFoundError("Fayl mazmuni topilmadi.") from exc

        return FileDownload(
            content=content,
            content_type=record.content_type,
            original_name=record.original_name,
        )

    async def _can_access(self, record: File, current_user: CurrentUser) -> bool:
        # Yuklagan foydalanuvchi doimo kira oladi.
        if record.uploaded_by == current_user.id:
            return True
        # Aks holda: fayl biriktirilgan hisobotning bolasini ko'ra olsa.
        child_ids = await self._reports.child_ids_for_file(record.id)
        for child_id in child_ids:
            if await self._access.can_view_child(current_user, child_id):
                return True
        return False
