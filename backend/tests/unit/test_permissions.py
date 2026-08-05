"""RBAC va filial izolyatsiyasi qoidalari uchun unit testlar (2.3-bo'lim)."""

from __future__ import annotations

import uuid

from app.core.permissions import CurrentUser, RoleGrant
from app.models.enums import Role

BRANCH_A = uuid.uuid4()
BRANCH_B = uuid.uuid4()


def _user(*grants: RoleGrant) -> CurrentUser:
    return CurrentUser(id=uuid.uuid4(), full_name="Test", grants=grants)


def test_owner_can_access_any_branch() -> None:
    owner = _user(RoleGrant(role=Role.OWNER, branch_id=None))

    assert owner.is_owner is True
    assert owner.can_access_branch(BRANCH_A, Role.MANAGER) is True
    assert owner.can_access_branch(BRANCH_B, Role.MANAGER) is True


def test_manager_only_own_branch() -> None:
    manager = _user(RoleGrant(role=Role.MANAGER, branch_id=BRANCH_A))

    assert manager.is_owner is False
    assert manager.can_access_branch(BRANCH_A, Role.MANAGER) is True
    # Boshqa filialga kirisha olmaydi.
    assert manager.can_access_branch(BRANCH_B, Role.MANAGER) is False


def test_role_mismatch_denies_access() -> None:
    teacher = _user(RoleGrant(role=Role.TEACHER, branch_id=BRANCH_A))

    # Faqat MANAGER roli ruxsat etilgan bo'lsa, TEACHER kira olmaydi.
    assert teacher.can_access_branch(BRANCH_A, Role.MANAGER) is False
    assert teacher.can_access_branch(BRANCH_A, Role.TEACHER) is True


def test_has_any_role_and_branches_for() -> None:
    user = _user(
        RoleGrant(role=Role.MANAGER, branch_id=BRANCH_A),
        RoleGrant(role=Role.TEACHER, branch_id=BRANCH_B),
    )

    assert user.has_any_role(Role.MANAGER) is True
    assert user.has_any_role(Role.OWNER) is False
    assert user.branches_for(Role.MANAGER) == {BRANCH_A}
    assert user.branches_for(Role.MANAGER, Role.TEACHER) == {BRANCH_A, BRANCH_B}
