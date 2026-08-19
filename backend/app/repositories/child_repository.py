"""Bolalar, vasiylar va enrollmentlar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.child import Child, ChildGuardian
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus


class ChildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, child: Child) -> None:
        self._session.add(child)

    def add_guardian(self, link: ChildGuardian) -> None:
        self._session.add(link)

    async def get_by_id(self, child_id: uuid.UUID) -> Child | None:
        return await self._session.get(Child, child_id)

    async def get_loaded(self, child_id: uuid.UUID) -> Child | None:
        """Vasiylar bilan to'liq yuklangan bola (lazy IO'siz javob uchun)."""
        stmt = (
            select(Child)
            .where(Child.id == child_id)
            .options(selectinload(Child.guardians))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[Child]:
        stmt = select(Child).order_by(Child.full_name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_ids(self, child_ids: Sequence[uuid.UUID]) -> list[Child]:
        if not child_ids:
            return []
        stmt = select(Child).where(Child.id.in_(child_ids)).order_by(Child.full_name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def guardian_link_exists(
        self, child_id: uuid.UUID, guardian_user_id: uuid.UUID
    ) -> bool:
        stmt = (
            select(ChildGuardian.id)
            .where(
                ChildGuardian.child_id == child_id,
                ChildGuardian.guardian_user_id == guardian_user_id,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def child_ids_for_guardian(
        self, guardian_user_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """PARENT ko'ra oladigan bolalar ID'lari (4.4-bo'lim: faqat o'z bolalari)."""
        stmt = select(ChildGuardian.child_id).where(
            ChildGuardian.guardian_user_id == guardian_user_id
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def all_guardian_child_names(self) -> dict[uuid.UUID, list[str]]:
        """Har bir vasiy uchun bog'langan bolalar ismlari (Ota-onalar ro'yxati)."""
        stmt = select(ChildGuardian.guardian_user_id, Child.full_name).join(
            Child, Child.id == ChildGuardian.child_id
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[uuid.UUID, list[str]] = {}
        for guardian_id, child_name in rows:
            result.setdefault(guardian_id, []).append(child_name)
        return result

    async def guardian_child_names_for_children(
        self, child_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[str]]:
        """`all_guardian_child_names`ning berilgan bolalar bilan cheklangan varianti
        (filial kesimidagi Ota-onalar ro'yxati uchun)."""
        if not child_ids:
            return {}
        stmt = (
            select(ChildGuardian.guardian_user_id, Child.full_name)
            .join(Child, Child.id == ChildGuardian.child_id)
            .where(ChildGuardian.child_id.in_(child_ids))
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[uuid.UUID, list[str]] = {}
        for guardian_id, child_name in rows:
            result.setdefault(guardian_id, []).append(child_name)
        return result

    async def notifiable_guardian_targets(
        self, child_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, int]]:
        """Bildirishnoma oladigan vasiylar: (user_id, telegram_chat_id).

        Faqat `receives_notifications` yoqilgan va Telegram hisobi bog'langan
        vasiylar qaytariladi (9-bo'lim).
        """
        from app.models.user import User

        stmt = (
            select(User.id, User.telegram_chat_id)
            .join(ChildGuardian, ChildGuardian.guardian_user_id == User.id)
            .where(
                ChildGuardian.child_id == child_id,
                ChildGuardian.receives_notifications.is_(True),
                User.telegram_chat_id.is_not(None),
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def notifiable_guardian_targets_for_children(
        self, child_ids: Sequence[uuid.UUID]
    ) -> list[tuple[uuid.UUID, int]]:
        """Bir nechta bola uchun bildirishnoma oladigan vasiylar, dublikatsiz
        (bir vasiy bir nechta bolaga bog'langan bo'lsa, bitta xabar oladi;
        ommaviy xabar yuborish uchun, 7-bosqich B)."""
        from app.models.user import User

        if not child_ids:
            return []
        stmt = (
            select(User.id, User.telegram_chat_id)
            .join(ChildGuardian, ChildGuardian.guardian_user_id == User.id)
            .where(
                ChildGuardian.child_id.in_(child_ids),
                ChildGuardian.receives_notifications.is_(True),
                User.telegram_chat_id.is_not(None),
            )
            .distinct()
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]


class EnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, enrollment: Enrollment) -> None:
        self._session.add(enrollment)

    async def get_by_id(self, enrollment_id: uuid.UUID) -> Enrollment | None:
        return await self._session.get(Enrollment, enrollment_id)

    async def get_active_for_child(self, child_id: uuid.UUID) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .where(
                Enrollment.child_id == child_id,
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def child_ids_in_branches(
        self, branch_ids: Sequence[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Berilgan filiallarda enrollmenti bor bolalarning ID'lari."""
        if not branch_ids:
            return []
        stmt = (
            select(Enrollment.child_id)
            .where(Enrollment.branch_id.in_(branch_ids))
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def child_ids_in_groups(
        self, group_ids: Sequence[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Berilgan guruhlarda faol enrollmenti bor bolalarning ID'lari (teacher uchun)."""
        if not group_ids:
            return []
        stmt = (
            select(Enrollment.child_id)
            .where(
                Enrollment.group_id.in_(group_ids),
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
            )
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def child_ids_by_group(
        self, group_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        """Guruh ID → undagi faol bolalar ID'lari.

        `child_ids_in_groups` yassi ro'yxat qaytaradi va qaysi bola qaysi
        guruhda ekanini bilib bo'lmaydi — shu sabab filial xulosasi har bir
        guruh uchun alohida so'rov yuborishga majbur edi. Bu metod hammasini
        bitta so'rovda beradi.
        """
        if not group_ids:
            return {}
        stmt = select(Enrollment.group_id, Enrollment.child_id).where(
            Enrollment.group_id.in_(group_ids),
            Enrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[uuid.UUID, list[uuid.UUID]] = {gid: [] for gid in group_ids}
        for group_id, child_id in rows:
            result.setdefault(group_id, []).append(child_id)
        return result

    async def list_active_in_branch(self, branch_id: uuid.UUID) -> list[Enrollment]:
        """Filialdagi barcha faol enrollmentlar (invoice generatsiyasi uchun)."""
        stmt = select(Enrollment).where(
            Enrollment.branch_id == branch_id,
            Enrollment.status == EnrollmentStatus.ACTIVE.value,
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def latest_statuses_for_children(
        self, child_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """Har bir bola uchun "eng dolzarb" enrollment holati.

        ACTIVE enrollment mavjud bo'lsa shu ustunlik qiladi; aks holda eng
        yangi (start_date bo'yicha) enrollment holati olinadi. Bu Child
        ro'yxatida active/waiting/left proyeksiyasi uchun ishlatiladi.
        """
        if not child_ids:
            return {}
        stmt = select(
            Enrollment.child_id, Enrollment.status, Enrollment.start_date
        ).where(Enrollment.child_id.in_(child_ids))
        rows = (await self._session.execute(stmt)).all()

        best: dict[uuid.UUID, tuple[str, date]] = {}
        for child_id, enroll_status, start_date in rows:
            current = best.get(child_id)
            if current is None:
                best[child_id] = (enroll_status, start_date)
                continue
            cur_status, cur_start = current
            is_active = enroll_status == EnrollmentStatus.ACTIVE.value
            cur_is_active = cur_status == EnrollmentStatus.ACTIVE.value
            if (is_active and not cur_is_active) or (
                is_active == cur_is_active and start_date > cur_start
            ):
                best[child_id] = (enroll_status, start_date)
        return {child_id: status for child_id, (status, _) in best.items()}

    async def has_active_in_branches(
        self, child_id: uuid.UUID, branch_ids: Sequence[uuid.UUID]
    ) -> bool:
        if not branch_ids:
            return False
        stmt = (
            select(Enrollment.id)
            .where(
                Enrollment.child_id == child_id,
                Enrollment.branch_id.in_(branch_ids),
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None
