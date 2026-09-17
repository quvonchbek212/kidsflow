"""Kunlik hisobot xizmati (4.4-bo'lim, 9-bo'lim).

Hisobot yaratiladi (draft) → tahrirlanadi → e'lon qilinadi (publish). Publish
bir transaction ichida `published_at` ni belgilaydi va `outbox_event` yaratadi;
worker keyinchalik Telegram bildirishnomasini yuboradi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.daily_report import DailyReport, DailyReportFile
from app.models.messaging import OutboxEvent
from app.repositories.child_repository import ChildRepository, EnrollmentRepository
from app.repositories.daily_report_repository import DailyReportRepository
from app.repositories.file_repository import FileRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.messaging_repository import OutboxRepository
from app.schemas.daily_report import (
    DailyReportCreateRequest,
    DailyReportFileSummary,
    DailyReportResponse,
    DailyReportRosterRow,
    DailyReportUpdateRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService

DAILY_REPORT_PUBLISHED = "DAILY_REPORT_PUBLISHED"


class DailyReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reports = DailyReportRepository(session)
        self._files = FileRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._children = ChildRepository(session)
        self._groups = GroupRepository(session)
        self._outbox = OutboxRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self, data: DailyReportCreateRequest, current_user: CurrentUser
    ) -> DailyReport:
        branch_id = await self._resolve_branch(data.child_id)
        await self._require_write(current_user, data.child_id, branch_id)

        if await self._reports.get_for_child_date(data.child_id, data.report_date):
            raise ConflictError("Bu bola uchun bu sanada hisobot allaqachon mavjud.")

        await self._validate_files(data.file_ids, current_user)

        report = DailyReport(
            branch_id=branch_id,
            child_id=data.child_id,
            report_date=data.report_date,
            meal_status=data.meal_status.value if data.meal_status else None,
            nap_minutes=data.nap_minutes,
            mood=data.mood.value if data.mood else None,
            activities_text=data.activities_text,
            teacher_note=data.teacher_note,
            final_summary=data.final_summary,
            created_by=current_user.id,
        )
        self._reports.add(report)
        await self._session.flush()
        await self._attach_files(report.id, data.file_ids)

        self._audit.record(
            action="DAILY_REPORT_CREATED",
            entity_type="daily_report",
            entity_id=report.id,
            actor_user_id=current_user.id,
            branch_id=branch_id,
        )
        return await self._reload(report.id)

    async def update(
        self,
        report_id: uuid.UUID,
        data: DailyReportUpdateRequest,
        current_user: CurrentUser,
    ) -> DailyReport:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise NotFoundError("Hisobot topilmadi.")
        await self._require_write(current_user, report.child_id, report.branch_id)

        if report.published_at is not None:
            raise ConflictError("E'lon qilingan hisobotni tahrirlab bo'lmaydi.")

        fields = data.model_dump(exclude_unset=True)
        if "meal_status" in fields:
            report.meal_status = data.meal_status.value if data.meal_status else None
            fields.pop("meal_status")
        if "mood" in fields:
            report.mood = data.mood.value if data.mood else None
            fields.pop("mood")
        file_ids = fields.pop("file_ids", None)
        for field, value in fields.items():
            setattr(report, field, value)

        if file_ids is not None:
            await self._validate_files(
                file_ids,
                current_user,
                already_attached=await self._reports.file_ids_for_report(report_id),
            )
            await self._reports.clear_file_links(report_id)
            await self._session.flush()
            await self._attach_files(report_id, file_ids)

        self._audit.record(
            action="DAILY_REPORT_UPDATED",
            entity_type="daily_report",
            entity_id=report.id,
            actor_user_id=current_user.id,
            branch_id=report.branch_id,
        )
        return await self._reload(report_id)

    async def publish(
        self, report_id: uuid.UUID, current_user: CurrentUser
    ) -> DailyReport:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise NotFoundError("Hisobot topilmadi.")
        await self._require_write(current_user, report.child_id, report.branch_id)

        if report.published_at is not None:
            raise ConflictError("Hisobot allaqachon e'lon qilingan.")
        if not (report.final_summary or report.activities_text):
            raise ConflictError(
                "E'lon qilishdan oldin hisobot matni to'ldirilishi kerak."
            )

        report.published_at = datetime.now(UTC)

        # Outbox hodisasi — worker Telegram bildirishnomasini yuboradi (9-bo'lim).
        self._outbox.add(
            OutboxEvent(
                event_type=DAILY_REPORT_PUBLISHED,
                payload={
                    "daily_report_id": str(report.id),
                    "child_id": str(report.child_id),
                    "branch_id": str(report.branch_id),
                },
            )
        )
        self._audit.record(
            action="DAILY_REPORT_PUBLISHED",
            entity_type="daily_report",
            entity_id=report.id,
            actor_user_id=current_user.id,
            branch_id=report.branch_id,
        )
        return await self._reload(report_id)

    async def get(self, report_id: uuid.UUID, current_user: CurrentUser) -> DailyReport:
        report = await self._reports.get_loaded(report_id)
        if report is None:
            raise NotFoundError("Hisobot topilmadi.")
        if not await self._access.can_view_child(current_user, report.child_id):
            raise PermissionDeniedError("Bu hisobotga kirish huquqi yo'q.")
        # Qoralama (draft) faqat xodimlarga ko'rinadi; ota-ona faqat e'lon qilinganini.
        if report.published_at is None and not await self._is_staff_for(
            current_user, report.child_id, report.branch_id
        ):
            raise PermissionDeniedError("Hisobot hali e'lon qilinmagan.")
        return report

    async def roster_for_group(
        self,
        group_id: uuid.UUID,
        report_date: date,
        current_user: CurrentUser,
    ) -> list[DailyReportRosterRow]:
        """Guruhdagi barcha bolalar va ularning shu sanadagi hisoboti.

        Ruxsat qoidasi davomat rosteri bilan bir xil: o'z guruhining TEACHER'i
        yoki filial MANAGER/OWNER'i (4.3-bo'lim). Ota-ona bu ro'yxatni ko'rmaydi
        — u faqat o'z farzandining e'lon qilingan hisobotlarini oladi.
        """
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not await self._access.can_view_group(
            current_user, group.branch_id, group.id
        ):
            raise PermissionDeniedError("Bu guruh hisobotlariga kirish huquqi yo'q.")

        child_ids = await self._enrollments.child_ids_in_groups([group_id])
        children = await self._children.list_by_ids(child_ids)
        reports = await self._reports.list_for_children_date(child_ids, report_date)
        by_child = {r.child_id: r for r in reports}

        rows = []
        for child in children:
            report = by_child.get(child.id)
            rows.append(
                DailyReportRosterRow(
                    child_id=child.id,
                    child_name=child.full_name,
                    report=await self.to_response(report) if report else None,
                )
            )
        return rows

    async def list_for_child(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> list[DailyReport]:
        if not await self._access.can_view_child(current_user, child_id):
            raise PermissionDeniedError("Bu bolaga kirish huquqi yo'q.")
        reports = await self._reports.list_for_child(child_id)
        # Ota-ona faqat e'lon qilingan hisobotlarni ko'radi.
        if not await self._is_staff_generic(current_user):
            return [r for r in reports if r.published_at is not None]
        return reports

    async def to_response(self, report: DailyReport) -> DailyReportResponse:
        file_ids = [link.file_id for link in report.files]
        files = await self._files.list_by_ids(file_ids)
        file_meta = {f.id: f for f in files}
        return DailyReportResponse(
            id=report.id,
            branch_id=report.branch_id,
            child_id=report.child_id,
            report_date=report.report_date,
            meal_status=report.meal_status,
            nap_minutes=report.nap_minutes,
            mood=report.mood,
            activities_text=report.activities_text,
            teacher_note=report.teacher_note,
            final_summary=report.final_summary,
            is_published=report.published_at is not None,
            published_at=report.published_at,
            files=[
                DailyReportFileSummary(
                    file_id=link.file_id,
                    original_name=(
                        file_meta[link.file_id].original_name
                        if link.file_id in file_meta
                        else ""
                    ),
                    content_type=(
                        file_meta[link.file_id].content_type
                        if link.file_id in file_meta
                        else ""
                    ),
                )
                for link in report.files
            ],
        )

    async def to_responses(
        self, reports: list[DailyReport]
    ) -> list[DailyReportResponse]:
        return [await self.to_response(r) for r in reports]

    # --- yordamchilar ---

    async def _resolve_branch(self, child_id: uuid.UUID) -> uuid.UUID:
        enrollment = await self._enrollments.get_active_for_child(child_id)
        if enrollment is None:
            raise ConflictError(
                "Bolaning faol enrollmenti yo'q — hisobot yaratib bo'lmaydi."
            )
        return enrollment.branch_id

    async def _require_write(
        self, user: CurrentUser, child_id: uuid.UUID, branch_id: uuid.UUID
    ) -> None:
        if not await self._is_staff_for(user, child_id, branch_id):
            raise PermissionDeniedError("Bu bola hisobotini yozish huquqi yo'q.")

    async def _is_staff_for(
        self, user: CurrentUser, child_id: uuid.UUID, branch_id: uuid.UUID
    ) -> bool:
        # Hisobot yozish huquqi davomat bilan bir xil (teacher/manager/owner).
        return await self._access.can_mark_attendance_for_child(
            user, child_id, branch_id
        )

    async def _is_staff_generic(self, user: CurrentUser) -> bool:
        from app.models.enums import Role

        return self._access.is_manager_or_owner(user) or user.has_any_role(Role.TEACHER)

    async def _validate_files(
        self,
        file_ids: list[uuid.UUID],
        current_user: CurrentUser,
        already_attached: set[uuid.UUID] | None = None,
    ) -> None:
        """Faqat o'zi yuklagan (yoki shu hisobotda allaqachon turgan) fayl.

        Ilgari fayl faqat mavjudligi bo'yicha tekshirilardi: istalgan fayl ID'sini
        o'z hisobotiga biriktirib, keyin uni hisobot orqali yuklab olish mumkin
        edi (masalan, boshqa xodim yuklagan to'lov cheki).
        """
        if not file_ids:
            return
        if len(set(file_ids)) != len(file_ids):
            raise ConflictError("Bitta fayl ikki marta biriktirilgan.")
        found = await self._files.list_by_ids(file_ids)
        if len(found) != len(file_ids):
            raise NotFoundError("Ba'zi fayllar topilmadi.")
        allowed = already_attached or set()
        if any(f.uploaded_by != current_user.id and f.id not in allowed for f in found):
            raise PermissionDeniedError(
                "Faqat o'zingiz yuklagan faylni biriktirish mumkin."
            )

    async def _attach_files(
        self, report_id: uuid.UUID, file_ids: list[uuid.UUID]
    ) -> None:
        for order, file_id in enumerate(file_ids):
            self._reports.add_file_link(
                DailyReportFile(
                    daily_report_id=report_id,
                    file_id=file_id,
                    sort_order=order,
                )
            )
        if file_ids:
            await self._session.flush()

    async def _reload(self, report_id: uuid.UUID) -> DailyReport:
        report = await self._reports.get_loaded(report_id)
        if report is None:
            raise NotFoundError("Hisobot topilmadi.")
        return report
