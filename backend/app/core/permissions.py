"""RBAC va filial izolyatsiyasi qoidalari (2.3-bo'lim).

Bu qatlam faqat qoidalarni hisoblaydi; DB'ga bog'liq emas, shuning uchun uni
alohida (soxta foydalanuvchilar bilan) osongina test qilish mumkin.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.enums import Role


@dataclass(frozen=True)
class RoleGrant:
    """Bitta faol rol biriktirmasi."""

    role: Role
    branch_id: uuid.UUID | None


@dataclass(frozen=True)
class CurrentUser:
    """So'rovni bajarayotgan autentifikatsiyalangan foydalanuvchi."""

    id: uuid.UUID
    full_name: str
    grants: tuple[RoleGrant, ...]

    @property
    def roles(self) -> set[Role]:
        return {grant.role for grant in self.grants}

    @property
    def is_owner(self) -> bool:
        return Role.OWNER in self.roles

    def has_any_role(self, *roles: Role) -> bool:
        """Foydalanuvchida berilgan rollardan biri (istalgan filialda) bormi."""
        return bool(self.roles.intersection(roles))

    def branches_for(self, *roles: Role) -> set[uuid.UUID]:
        """Berilgan rollar bo'yicha foydalanuvchi kira oladigan filiallar."""
        return {
            grant.branch_id
            for grant in self.grants
            if grant.role in roles and grant.branch_id is not None
        }

    def can_access_branch(self, branch_id: uuid.UUID, *allowed_roles: Role) -> bool:
        """Foydalanuvchi shu filialga (ruxsat etilgan rol bilan) kira oladimi.

        OWNER barcha filiallarni ko'radi (3-bo'lim). Boshqa rollar faqat o'ziga
        biriktirilgan filialga kira oladi.
        """
        if self.is_owner:
            return True
        return branch_id in self.branches_for(*allowed_roles)
