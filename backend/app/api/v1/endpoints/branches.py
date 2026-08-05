"""Filial endpointlari.

OWNER barcha filiallarni boshqaradi; MANAGER faqat biriktirilgan filialni ko'radi
(3-bo'lim). Ruxsatlar backend darajasida tekshiriladi (2.3-bo'lim).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, require_roles
from app.models.enums import Role
from app.schemas.branch import (
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
)
from app.services.branch_service import BranchService

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=list[BranchResponse], summary="Filiallar ro'yxati")
async def list_branches(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BranchResponse]:
    branches = await BranchService(session).list_for(current_user)
    return [BranchResponse.model_validate(b) for b in branches]


@router.post(
    "",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Filial yaratish (faqat OWNER)",
)
async def create_branch(
    payload: BranchCreateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> BranchResponse:
    branch = await BranchService(session).create(payload, current_user)
    return BranchResponse.model_validate(branch)


@router.get("/{branch_id}", response_model=BranchResponse, summary="Filial ma'lumoti")
async def get_branch(
    branch_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BranchResponse:
    branch = await BranchService(session).get_accessible(branch_id, current_user)
    return BranchResponse.model_validate(branch)


@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
    summary="Filialni tahrirlash (faqat OWNER)",
)
async def update_branch(
    branch_id: uuid.UUID,
    payload: BranchUpdateRequest,
    current_user: CurrentUser = Depends(require_roles(Role.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> BranchResponse:
    branch = await BranchService(session).update(branch_id, payload, current_user)
    return BranchResponse.model_validate(branch)
