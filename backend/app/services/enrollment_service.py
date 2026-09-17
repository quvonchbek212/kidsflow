"""Enrollment biznes xizmati (5.3-bo'lim)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.repositories.child_repository import (
    ChildRepository,
    EnrollmentRepository,
)
from app.repositories.group_repository import GroupRepository
from app.schemas.enrollment import (
    ChildTransferRequest,
    EnrollmentCreateRequest,
    EnrollmentUpdateRequest,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.services.billing_service import BillingService
from app.utils.timezone import today_local


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._enrollments = EnrollmentRepository(session)
        self._children = ChildRepository(session)
        self._groups = GroupRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self,
        child_id: uuid.UUID,
        data: EnrollmentCreateRequest,
        current_user: CurrentUser,
    ) -> Enrollment:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda enrollment yaratish huquqi yo'q.")

        child = await self._children.get_by_id(child_id)
        if child is None:
            raise NotFoundError("Bola topilmadi.")

        group = await self._groups.get_by_id(data.group_id)
        if group is None:
            raise NotFoundError("Guruh topilmadi.")
        # Guruh va enrollment bir filialga tegishli bo'lishi kerak (5.9-bo'lim).
        if group.branch_id != data.branch_id:
            raise ConflictError("Guruh ko'rsatilgan filialga tegishli emas.")

        # Bir bolada bir vaqtda faqat bitta ACTIVE enrollment (16-bo'lim).
        if data.status == EnrollmentStatus.ACTIVE:
            existing = await self._enrollments.get_active_for_child(child_id)
            if existing is not None:
                raise ConflictError("Bolada allaqachon faol enrollment mavjud.")

        enrollment = Enrollment(
            child_id=child_id,
            branch_id=data.branch_id,
            group_id=data.group_id,
            start_date=data.start_date,
            status=data.status.value,
            notes=data.notes,
            discount_type=data.discount_type.value if data.discount_type else None,
            discount_percent=data.discount_percent,
        )
        self._enrollments.add(enrollment)

        # Faolsizlantirilgan bolani guruhga qayta yozish — uni qayta qabul
        # qilish degani. Bola shu yerning o'zida faollashadi: aks holda ikki
        # alohida so'rov orasida "guruhda, lekin nofaol" holat qolishi (va
        # nofaol bolaga hisob yozilishi) mumkin edi.
        if not child.is_active and data.status in (
            EnrollmentStatus.ACTIVE,
            EnrollmentStatus.PLANNED,
        ):
            child.is_active = True
            self._audit.record(
                action="CHILD_UPDATED",
                entity_type="child",
                entity_id=child.id,
                actor_user_id=current_user.id,
                branch_id=data.branch_id,
                after_data={"is_active": True, "reason": "re_enrolled"},
            )

        await self._session.flush()
        self._audit.record(
            action="ENROLLMENT_CREATED",
            entity_type="enrollment",
            entity_id=enrollment.id,
            actor_user_id=current_user.id,
            branch_id=enrollment.branch_id,
            after_data={"child_id": str(child_id), "status": enrollment.status},
        )
        if enrollment.status == EnrollmentStatus.ACTIVE.value:
            await self._bill_current_month(enrollment)
        return enrollment

    async def update(
        self,
        enrollment_id: uuid.UUID,
        data: EnrollmentUpdateRequest,
        current_user: CurrentUser,
    ) -> Enrollment:
        enrollment = await self._enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment topilmadi.")
        if not self._access.can_manage_branch(current_user, enrollment.branch_id):
            raise PermissionDeniedError("Bu enrollment'ni tahrirlash huquqi yo'q.")

        before_status = enrollment.status

        # ACTIVE ga o'tkazishda boshqa faol enrollment bo'lmasligi kerak.
        if (
            data.status == EnrollmentStatus.ACTIVE
            and before_status != EnrollmentStatus.ACTIVE.value
        ):
            existing = await self._enrollments.get_active_for_child(enrollment.child_id)
            if existing is not None and existing.id != enrollment.id:
                raise ConflictError("Bolada allaqachon faol enrollment mavjud.")

        # Boshlanish sanasi faqat navbatdagi bola uchun o'zgaradi: faol
        # enrollmentda u hisob-faktura va davomat tarixiga bog'langan.
        if data.start_date is not None:
            if before_status != EnrollmentStatus.PLANNED.value:
                raise ConflictError(
                    "Boshlanish sanasini faqat navbatdagi bola uchun "
                    "o'zgartirish mumkin."
                )
            enrollment.start_date = data.start_date

        if data.status is not None:
            enrollment.status = data.status.value
        if data.end_date is not None:
            enrollment.end_date = data.end_date
        if data.group_id is not None:
            group = await self._groups.get_by_id(data.group_id)
            if group is None or group.branch_id != enrollment.branch_id:
                raise ConflictError("Guruh enrollment filialiga tegishli emas.")
            enrollment.group_id = data.group_id
        if data.notes is not None:
            enrollment.notes = data.notes
        if data.discount_type is not None:
            enrollment.discount_type = data.discount_type.value
        if data.discount_percent is not None:
            enrollment.discount_percent = data.discount_percent

        self._audit.record(
            action="ENROLLMENT_UPDATED",
            entity_type="enrollment",
            entity_id=enrollment.id,
            actor_user_id=current_user.id,
            branch_id=enrollment.branch_id,
            before_data={"status": before_status},
            after_data={"status": enrollment.status},
        )
        # Kutish ro'yxatidan faol bo'lganda ham hisob darhol ochiladi.
        if (
            enrollment.status == EnrollmentStatus.ACTIVE.value
            and before_status != EnrollmentStatus.ACTIVE.value
        ):
            await self._session.flush()
            await self._bill_current_month(enrollment)
        return enrollment

    async def transfer(
        self,
        child_id: uuid.UUID,
        data: ChildTransferRequest,
        current_user: CurrentUser,
    ) -> Enrollment:
        """Bolani boshqa guruhga ko'chiradi — eski enrollment yopiladi, yangisi
        ochiladi (bitta transactionda), shu bilan guruh tarixi saqlanadi.
        """
        current = await self._enrollments.get_active_for_child(child_id)
        if current is None:
            raise ConflictError(
                "Bolaning faol enrollmenti yo'q — guruhini o'zgartirib bo'lmaydi."
            )
        if not self._access.can_manage_branch(current_user, current.branch_id):
            raise PermissionDeniedError(
                "Bu bolani boshqa guruhga o'tkazish huquqi yo'q."
            )

        new_group = await self._groups.get_by_id(data.new_group_id)
        if new_group is None:
            raise NotFoundError("Yangi guruh topilmadi.")
        if new_group.branch_id != current.branch_id:
            raise ConflictError("Yangi guruh joriy filialga tegishli emas.")
        if data.effective_date < current.start_date:
            raise ConflictError(
                "O'tkazish sanasi joriy enrollment boshlanishidan oldin bo'lmasligi kerak."
            )

        discount_type = (
            data.discount_type.value if data.discount_type else current.discount_type
        )
        discount_percent = (
            data.discount_percent
            if data.discount_percent is not None
            else current.discount_percent
        )

        current.status = EnrollmentStatus.COMPLETED.value
        current.end_date = data.effective_date
        await self._session.flush()

        new_enrollment = Enrollment(
            child_id=child_id,
            branch_id=current.branch_id,
            group_id=data.new_group_id,
            start_date=data.effective_date,
            status=EnrollmentStatus.ACTIVE.value,
            notes=data.reason,
            discount_type=discount_type,
            discount_percent=discount_percent,
        )
        self._enrollments.add(new_enrollment)
        await self._session.flush()

        self._audit.record(
            action="CHILD_TRANSFERRED",
            entity_type="enrollment",
            entity_id=new_enrollment.id,
            actor_user_id=current_user.id,
            branch_id=current.branch_id,
            before_data={"group_id": str(current.group_id)},
            after_data={
                "group_id": str(data.new_group_id),
                "effective_date": data.effective_date.isoformat(),
            },
        )
        return new_enrollment

    async def _bill_current_month(self, enrollment: Enrollment) -> None:
        """Faol bo'lgan bolaga joriy oy hisobini darhol yaratadi.

        Kunlik worker ertasi kuni baribir yaratardi, lekin unda birinchi kuni
        bola "qarz yo'q" bo'lib ko'rinardi va to'lov formasi summani bilmasdi.
        """
        today = today_local()
        billing = BillingService(self._session)
        await billing.generate_for_branch(
            enrollment.branch_id,
            today,
            await billing.due_day_for(enrollment.branch_id),
            child_id=enrollment.child_id,
            not_before=today,
        )
