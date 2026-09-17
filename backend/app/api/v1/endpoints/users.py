"""Xodim (foydalanuvchi) endpointlari.

0-1 bosqichda xodim yaratish OWNER huquqida. Keyingi bosqichlarda MANAGER o'z
filialiga tarbiyachi qo'shishi kabi qoidalar kengaytiriladi.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, require_roles
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import (
    PayrollStaffRow,
    PayrollSummaryResponse,
    RoleGrantOut,
    SalaryUpdateRequest,
    StaffCreateRequest,
    StaffPasswordRequest,
    StaffUpdateRequest,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        phone=user.phone,
        email=user.email,
        is_active=user.is_active,
        position=user.position,
        monthly_salary=user.monthly_salary,
        birth_date=user.birth_date,
        passport_number=user.passport_number,
        hire_date=user.hire_date,
        employment_type=user.employment_type,
        roles=[
            RoleGrantOut(role=a.role, branch_id=a.branch_id)
            for a in user.role_assignments
        ],
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Xodim yaratish (OWNER; MANAGER o'z filialiga)",
)
async def create_staff(
    payload: StaffCreateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await UserService(session).create_staff(payload, current_user)
    return _to_response(user)


@router.get(
    "",
    response_model=list[UserResponse],
    summary="Xodimlar ro'yxati (OWNER; MANAGER o'z filiali, ixtiyoriy lavozim filtri)",
)
async def list_staff(
    position: str | None = Query(default=None),
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha xodimlar"
    ),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    users = await UserService(session).list_all(
        current_user, position=position, branch_id=branch_id
    )
    return [_to_response(u) for u in users]


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Xodim profilini tahrirlash (OWNER; MANAGER o'z filialida)",
)
async def update_staff(
    user_id: uuid.UUID,
    payload: StaffUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await UserService(session).update_staff(user_id, payload, current_user)
    return _to_response(user)


@router.patch(
    "/{user_id}/salary",
    response_model=UserResponse,
    summary="Xodim oylik maoshini belgilash (OWNER/MANAGER)",
)
async def update_salary(
    user_id: uuid.UUID,
    payload: SalaryUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await UserService(session).update_salary(user_id, payload, current_user)
    return _to_response(user)


@router.patch(
    "/{user_id}/password",
    response_model=UserResponse,
    summary="Xodimga yangi parol o'rnatish (OWNER; MANAGER o'z filialida)",
)
async def set_staff_password(
    user_id: uuid.UUID,
    payload: StaffPasswordRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Parolni unutgan xodimga boshqaruvchi yangi parol beradi.

    Xodimning eski sessiyalari yopiladi va kirish qulfi tozalanadi.
    """
    user = await UserService(session).set_password(
        user_id, payload.new_password, current_user
    )
    return _to_response(user)


@router.get(
    "/payroll-summary",
    response_model=PayrollSummaryResponse,
    summary="Ish haqi fondi (OWNER; MANAGER o'z filiali)",
)
async def payroll_summary(
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha xodimlar"
    ),
    current_user: CurrentUser = Depends(require_roles(Role.OWNER, Role.MANAGER)),
    session: AsyncSession = Depends(get_session),
) -> PayrollSummaryResponse:
    total, users = await UserService(session).payroll_summary(
        current_user, branch_id=branch_id
    )
    return PayrollSummaryResponse(
        total_fund=total,
        staff=[
            PayrollStaffRow(
                id=u.id,
                full_name=u.full_name,
                position=u.position,
                role=u.role_assignments[0].role if u.role_assignments else "",
                monthly_salary=u.monthly_salary or 0,
            )
            for u in users
            if u.monthly_salary is not None
        ],
    )
