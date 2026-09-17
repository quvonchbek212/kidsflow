"""Bolalar, vasiylar va enrollmentlar uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.child import Child, ChildGuardian
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.models.group import Group


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
        self, child_ids: Collection[uuid.UUID]
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

    async def child_names_for_guardians(
        self, guardian_ids: Collection[uuid.UUID]
    ) -> dict[uuid.UUID, list[str]]:
        """Berilgan vasiylarning farzand ismlari (yozishmalar ro'yxati uchun)."""
        if not guardian_ids:
            return {}
        stmt = (
            select(ChildGuardian.guardian_user_id, Child.full_name)
            .join(Child, Child.id == ChildGuardian.child_id)
            .where(ChildGuardian.guardian_user_id.in_(guardian_ids))
        )
        rows = (await self._session.execute(stmt)).all()
        result: dict[uuid.UUID, list[str]] = {}
        for guardian_id, child_name in rows:
            result.setdefault(guardian_id, []).append(child_name)
        return result

    async def user_profiles(
        self, user_ids: Collection[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, str | None]]:
        """Foydalanuvchi ID -> (to'liq ism, telefon)."""
        from app.models.user import User

        if not user_ids:
            return {}
        stmt = select(User.id, User.full_name, User.phone).where(User.id.in_(user_ids))
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    async def telegram_chat_id_for_user(self, user_id: uuid.UUID) -> int | None:
        """Xodim javobini yuborish uchun ota-onaning Telegram chat ID'si."""
        from app.models.user import User

        stmt = select(User.telegram_chat_id).where(User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

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

    async def has_any_for_child(self, child_id: uuid.UUID) -> bool:
        """Bolaning (istalgan holatdagi) enrollmenti bormi."""
        stmt = select(Enrollment.id).where(Enrollment.child_id == child_id).limit(1)
        return (await self._session.execute(stmt)).first() is not None

    async def open_for_child(self, child_id: uuid.UUID) -> list[Enrollment]:
        """Bolaning hali yopilmagan (faol yoki navbatdagi) enrollmentlari."""
        stmt = select(Enrollment).where(
            Enrollment.child_id == child_id,
            Enrollment.status.in_(
                [EnrollmentStatus.ACTIVE.value, EnrollmentStatus.PLANNED.value]
            ),
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def child_ids_in_branches(
        self,
        branch_ids: Sequence[uuid.UUID],
        statuses: Collection[str] | None = None,
    ) -> list[uuid.UUID]:
        """Berilgan filiallarda enrollmenti bor bolalarning ID'lari.

        `statuses` berilmasa har qanday holat (ketganlar ham) — bola
        ro'yxatidagi "Ketgan" bo'limi uchun. Xabar yuborishda esa faqat faollar.
        """
        if not branch_ids:
            return []
        stmt = select(Enrollment.child_id).where(Enrollment.branch_id.in_(branch_ids))
        if statuses is not None:
            stmt = stmt.where(Enrollment.status.in_(list(statuses)))
        return list((await self._session.execute(stmt.distinct())).scalars().all())

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

    async def list_active_in_branch(
        self, branch_id: uuid.UUID
    ) -> list[tuple[Enrollment, Decimal | None]]:
        """Filialdagi faol enrollmentlar va ular guruhining oylik tarifi.

        Tarif invoice summasi uchun kerak (5.5-bo'lim). U bir xil so'rovda
        JOIN bilan olinadi — har bir enrollment uchun alohida so'rov qilinsa
        N+1 chiqardi.
        """
        stmt = (
            select(Enrollment, Group.monthly_fee)
            .join(Group, Group.id == Enrollment.group_id)
            .where(
                Enrollment.branch_id == branch_id,
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
            )
        )
        return [(row[0], row[1]) for row in (await self._session.execute(stmt)).all()]

    async def current_for_children(
        self, child_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Enrollment]:
        """Har bir bola uchun "eng dolzarb" enrollment.

        ACTIVE enrollment mavjud bo'lsa shu ustunlik qiladi; aks holda eng
        yangi (start_date bo'yicha) enrollment olinadi. Bu Child ro'yxatida
        active/waiting/left proyeksiyasi va navbatdagi bolani qabul qilish
        uchun ishlatiladi.
        """
        if not child_ids:
            return {}
        stmt = select(Enrollment).where(Enrollment.child_id.in_(child_ids))
        rows = (await self._session.execute(stmt)).scalars().all()

        best: dict[uuid.UUID, Enrollment] = {}
        for enrollment in rows:
            current = best.get(enrollment.child_id)
            if current is None:
                best[enrollment.child_id] = enrollment
                continue
            is_active = enrollment.status == EnrollmentStatus.ACTIVE.value
            cur_is_active = current.status == EnrollmentStatus.ACTIVE.value
            if (is_active and not cur_is_active) or (
                is_active == cur_is_active
                and enrollment.start_date > current.start_date
            ):
                best[enrollment.child_id] = enrollment
        return best

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

    async def branch_for_child(self, child_id: uuid.UUID) -> uuid.UUID | None:
        """Bolaning filiali (eng so'nggi ro'yxatga olish bo'yicha).

        Outbox hodisalarining ko'pchiligi payload'ida faqat `child_id` olib
        yuradi (`CHILD_CHECKED_IN`, `DAILY_REPORT`, `PAYMENT_RECEIVED`,
        `BIRTHDAY_GREETING`). Bildirishnoma kalitlari endi filial kesimida
        bo'lgani uchun `OutboxProcessor` filialni shu orqali aniqlaydi —
        hodisa yaratuvchi xizmatlarni o'zgartirish shart bo'lmaydi.
        """
        stmt = (
            select(Enrollment.branch_id)
            .where(Enrollment.child_id == child_id)
            .order_by(Enrollment.start_date.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
