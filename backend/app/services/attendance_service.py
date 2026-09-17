"""Davomat biznes xizmati (4.3-bo'lim)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus
from app.models.messaging import OutboxEvent
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.child_repository import ChildRepository, EnrollmentRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.messaging_repository import OutboxRepository
from app.schemas.attendance import (
    AttendanceBulkMarkRequest,
    AttendanceMarkRequest,
    AttendanceRosterRow,
    AttendanceTrendPoint,
    BranchAttendanceSummary,
    BranchAttendanceTotals,
    BranchGroupRoster,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils.timezone import today_local

# Outbox hodisa turlari (7-bosqich B: xabar yuborish). `OutboxProcessor`
# shu qiymatlarni taniydi (`app/services/outbox_processor.py`).
CHILD_CHECKED_IN = "CHILD_CHECKED_IN"
CHILD_SICK = "CHILD_SICK"

_PRESENT_LIKE = (AttendanceStatus.PRESENT.value, AttendanceStatus.LATE.value)


class AttendanceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._attendance = AttendanceRepository(session)
        self._enrollments = EnrollmentRepository(session)
        self._children = ChildRepository(session)
        self._groups = GroupRepository(session)
        self._outbox = OutboxRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    def _maybe_notify_status_change(
        self,
        *,
        branch_id: uuid.UUID,
        child_id: uuid.UUID,
        new_status: str,
        previous_status: str | None,
    ) -> None:
        """Holat YANGI belgilangan/o'zgargan bo'lsagina xabar navbatga qo'yiladi
        (bir xil holatni qayta saqlashda takroriy xabar yuborilmasin)."""
        if new_status in _PRESENT_LIKE and previous_status not in _PRESENT_LIKE:
            self._outbox.add(
                OutboxEvent(
                    event_type=CHILD_CHECKED_IN,
                    payload={"child_id": str(child_id), "branch_id": str(branch_id)},
                )
            )
        elif (
            new_status == AttendanceStatus.SICK.value
            and previous_status != AttendanceStatus.SICK.value
        ):
            self._outbox.add(
                OutboxEvent(
                    event_type=CHILD_SICK,
                    payload={"child_id": str(child_id), "branch_id": str(branch_id)},
                )
            )

    async def mark(
        self, data: AttendanceMarkRequest, current_user: CurrentUser
    ) -> Attendance:
        # Davomat filiali bolaning faol enrollmentidan olinadi.
        enrollment = await self._enrollments.get_active_for_child(data.child_id)
        if enrollment is None:
            raise ConflictError(
                "Bolaning faol enrollmenti yo'q — davomat belgilab bo'lmaydi."
            )
        branch_id = enrollment.branch_id

        if not await self._access.can_mark_attendance_for_child(
            current_user, data.child_id, branch_id
        ):
            raise PermissionDeniedError("Bu bola davomatini belgilash huquqi yo'q.")

        # Bir bola, bir sana uchun bitta yozuv — mavjud bo'lsa yangilanadi.
        existing = await self._attendance.get_for_child_date(
            data.child_id, data.attendance_date
        )
        previous_status = existing.status if existing is not None else None
        if existing is not None:
            existing.status = data.status.value
            existing.check_in_at = data.check_in_at
            existing.check_out_at = data.check_out_at
            existing.note = data.note
            existing.marked_by = current_user.id
            record = existing
            action = "ATTENDANCE_UPDATED"
        else:
            record = Attendance(
                branch_id=branch_id,
                child_id=data.child_id,
                attendance_date=data.attendance_date,
                status=data.status.value,
                check_in_at=data.check_in_at,
                check_out_at=data.check_out_at,
                note=data.note,
                marked_by=current_user.id,
            )
            self._attendance.add(record)
            action = "ATTENDANCE_MARKED"

        self._maybe_notify_status_change(
            branch_id=branch_id,
            child_id=data.child_id,
            new_status=data.status.value,
            previous_status=previous_status,
        )
        await self._session.flush()
        self._audit.record(
            action=action,
            entity_type="attendance",
            entity_id=record.id,
            actor_user_id=current_user.id,
            branch_id=branch_id,
            after_data={"status": record.status},
        )
        return record

    async def list_for_child(
        self, child_id: uuid.UUID, current_user: CurrentUser
    ) -> list[Attendance]:
        if not await self._access.can_view_child(current_user, child_id):
            raise PermissionDeniedError("Bu bola davomatiga kirish huquqi yo'q.")
        return await self._attendance.list_for_child(child_id)

    async def roster_for_group(
        self,
        group_id: uuid.UUID,
        roster_date: date,
        current_user: CurrentUser,
    ) -> list[AttendanceRosterRow]:
        """Guruhdagi barcha bolalar va ularning shu sanadagi davomati."""
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not await self._access.can_view_group(
            current_user, group.branch_id, group.id
        ):
            raise PermissionDeniedError("Bu guruh davomatiga kirish huquqi yo'q.")

        child_ids = await self._enrollments.child_ids_in_groups([group_id])
        children = await self._children.list_by_ids(child_ids)
        attendance_map = await self._attendance.map_for_children_date(
            child_ids, roster_date
        )

        rows = []
        for child in children:
            record = attendance_map.get(child.id)
            rows.append(
                AttendanceRosterRow(
                    child_id=child.id,
                    child_name=child.full_name,
                    status=record.status if record else None,
                    check_in_at=record.check_in_at if record else None,
                    check_out_at=record.check_out_at if record else None,
                )
            )
        return rows

    async def mark_bulk(
        self,
        data: AttendanceBulkMarkRequest,
        current_user: CurrentUser,
    ) -> list[Attendance]:
        """Bir guruh, bir kun uchun bir nechta bolani birdaniga belgilaydi.

        Guruh rosterini ko'ra oladigan har kim (o'z guruhi TEACHER'i yoki
        filial MANAGER/OWNER) belgilay ham oladi — `roster_for_group` bilan
        bir xil ruxsat qoidasi (4.3-bo'lim).
        """
        group = await self._groups.get_by_id(data.group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not await self._access.can_view_group(
            current_user, group.branch_id, group.id
        ):
            raise PermissionDeniedError("Bu guruh davomatini belgilash huquqi yo'q.")

        group_child_ids = set(
            await self._enrollments.child_ids_in_groups([data.group_id])
        )

        if any(entry.child_id not in group_child_ids for entry in data.entries):
            raise ConflictError("Bola shu guruhga tegishli emas.")
        # Bitta so'rov: ilgari har bir bola uchun alohida SELECT ketardi.
        existing_by_child = await self._attendance.map_for_children_date(
            [entry.child_id for entry in data.entries], data.attendance_date
        )

        records: list[Attendance] = []
        for entry in data.entries:
            existing = existing_by_child.get(entry.child_id)
            previous_status = existing.status if existing is not None else None
            if existing is not None:
                existing.status = entry.status.value
                existing.note = entry.note
                existing.marked_by = current_user.id
                records.append(existing)
            else:
                record = Attendance(
                    branch_id=group.branch_id,
                    child_id=entry.child_id,
                    attendance_date=data.attendance_date,
                    status=entry.status.value,
                    note=entry.note,
                    marked_by=current_user.id,
                )
                self._attendance.add(record)
                records.append(record)

            self._maybe_notify_status_change(
                branch_id=group.branch_id,
                child_id=entry.child_id,
                new_status=entry.status.value,
                previous_status=previous_status,
            )

        await self._session.flush()
        self._audit.record(
            action="ATTENDANCE_BULK_MARKED",
            entity_type="attendance_batch",
            entity_id=str(data.group_id),
            actor_user_id=current_user.id,
            branch_id=group.branch_id,
            after_data={
                "count": len(records),
                "date": data.attendance_date.isoformat(),
            },
        )
        return records

    async def trend_for_group(
        self,
        group_id: uuid.UUID,
        days: int,
        current_user: CurrentUser,
    ) -> list[AttendanceTrendPoint]:
        """Guruhning so'nggi N kunlik davomat trendi (sparkline uchun)."""
        group = await self._groups.get_by_id(group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        if not await self._access.can_view_group(
            current_user, group.branch_id, group.id
        ):
            raise PermissionDeniedError("Bu guruh davomatiga kirish huquqi yo'q.")

        child_ids = await self._enrollments.child_ids_in_groups([group_id])
        total = len(child_ids)
        end_date = today_local()
        start_date = end_date - timedelta(days=days - 1)
        counts = await self._attendance.counts_by_date(child_ids, start_date, end_date)

        points: list[AttendanceTrendPoint] = []
        current_date = start_date
        while current_date <= end_date:
            points.append(
                AttendanceTrendPoint(
                    attendance_date=current_date,
                    present_count=counts.get(current_date, 0),
                    total_count=total,
                )
            )
            current_date += timedelta(days=1)
        return points

    async def branch_summary(
        self,
        branch_id: uuid.UUID,
        summary_date: date,
        trend_days: int,
        current_user: CurrentUser,
    ) -> BranchAttendanceSummary:
        """Filialdagi barcha guruhlarning kunlik davomati va umumiy trendi.

        Ilgari frontend har bir guruh uchun `roster` va `trend` ni alohida
        chaqirardi — 10 guruhda bu 20 dan ortiq HTTP so'rov edi. Bu yerda
        hammasi to'rtta SQL so'rovga jamlanadi: guruhlar, guruh→bolalar,
        bolalar, davomat.
        """
        if not self._access.can_view_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filialga kirish huquqi yo'q.")

        groups = await self._groups.list_by_branches([branch_id])
        groups = [g for g in groups if g.is_active]
        # TEACHER faqat o'ziga biriktirilgan guruhlarni ko'radi.
        if not self._access.is_manager_or_owner(current_user):
            allowed = set(await self._groups.group_ids_for_teacher(current_user.id))
            groups = [g for g in groups if g.id in allowed]

        group_ids = [g.id for g in groups]
        by_group = await self._enrollments.child_ids_by_group(group_ids)
        all_child_ids = [cid for ids in by_group.values() for cid in ids]

        children = {c.id: c for c in await self._children.list_by_ids(all_child_ids)}
        attendance_map = await self._attendance.map_for_children_date(
            all_child_ids, summary_date
        )

        counters = dict.fromkeys(("PRESENT", "LATE", "ABSENT", "SICK"), 0)
        unmarked = 0
        group_rosters: list[BranchGroupRoster] = []
        for group in groups:
            rows: list[AttendanceRosterRow] = []
            for child_id in by_group.get(group.id, []):
                child = children.get(child_id)
                if child is None:
                    continue
                record = attendance_map.get(child_id)
                if record is None:
                    unmarked += 1
                elif record.status in counters:
                    counters[record.status] += 1
                rows.append(
                    AttendanceRosterRow(
                        child_id=child.id,
                        child_name=child.full_name,
                        status=record.status if record else None,
                        check_in_at=record.check_in_at if record else None,
                        check_out_at=record.check_out_at if record else None,
                    )
                )
            rows.sort(key=lambda r: r.child_name)
            group_rosters.append(
                BranchGroupRoster(group_id=group.id, group_name=group.name, rows=rows)
            )

        end_date = today_local()
        start_date = end_date - timedelta(days=trend_days - 1)
        counts = await self._attendance.counts_by_date(
            all_child_ids, start_date, end_date
        )
        trend: list[AttendanceTrendPoint] = []
        current_date = start_date
        while current_date <= end_date:
            trend.append(
                AttendanceTrendPoint(
                    attendance_date=current_date,
                    present_count=counts.get(current_date, 0),
                    total_count=len(all_child_ids),
                )
            )
            current_date += timedelta(days=1)

        return BranchAttendanceSummary(
            attendance_date=summary_date,
            groups=group_rosters,
            totals=BranchAttendanceTotals(
                present=counters["PRESENT"],
                late=counters["LATE"],
                absent=counters["ABSENT"],
                sick=counters["SICK"],
                unmarked=unmarked,
                total=len(all_child_ids),
            ),
            trend=trend,
        )
