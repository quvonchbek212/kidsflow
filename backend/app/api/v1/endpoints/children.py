"""Bolalar va vasiylar endpointlari (4.2-bo'lim).

Kirish huquqlari service/access qatlamida tekshiriladi: OWNER/MANAGER to'liq,
TEACHER o'z guruhidagi bolalar, PARENT o'z bolalari (2.3, 3-bo'lim).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi import File as FastFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FileRejectedError
from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.schemas.child import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    GuardianCreateRequest,
    GuardianCreateResponse,
    ImportResultResponse,
)
from app.schemas.user import ParentRow
from app.services.child_service import ChildService
from app.services.import_service import MAX_IMPORT_BYTES, ImportService

router = APIRouter(prefix="/children", tags=["children"])


@router.get("", response_model=list[ChildResponse], summary="Bolalar ro'yxati")
async def list_children(
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha ko'rinadigan"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChildResponse]:
    service = ChildService(session)
    children = await service.list_visible(current_user, branch_id)
    return await service.to_responses(children, current_user)


@router.get(
    "/parents",
    response_model=list[ParentRow],
    summary="Ota-onalar ro'yxati (MANAGER/OWNER)",
)
async def list_parents(
    branch_id: uuid.UUID | None = Query(
        default=None, description="Filial kesimi; berilmasa — barcha ko'rinadigan"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ParentRow]:
    rows = await ChildService(session).list_parents(current_user, branch_id)
    return [ParentRow(**row) for row in rows]


@router.post(
    "",
    response_model=ChildResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bola yaratish (MANAGER/OWNER)",
)
async def create_child(
    payload: ChildCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChildResponse:
    service = ChildService(session)
    child = await service.create(payload, current_user)
    return await service.to_response(child, current_user)


@router.get("/{child_id}", response_model=ChildResponse, summary="Bola ma'lumoti")
async def get_child(
    child_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChildResponse:
    service = ChildService(session)
    child = await service.get(child_id, current_user)
    return await service.to_response(child, current_user)


@router.patch("/{child_id}", response_model=ChildResponse, summary="Bolani tahrirlash")
async def update_child(
    child_id: uuid.UUID,
    payload: ChildUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChildResponse:
    service = ChildService(session)
    child = await service.update(child_id, payload, current_user)
    return await service.to_response(child, current_user)


@router.post(
    "/{child_id}/guardians",
    response_model=GuardianCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bolaga vasiy biriktirish (MANAGER/OWNER)",
)
async def add_guardian(
    child_id: uuid.UUID,
    payload: GuardianCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GuardianCreateResponse:
    link = await ChildService(session).add_guardian(child_id, payload, current_user)
    return GuardianCreateResponse(
        guardian_user_id=link.guardian_user_id,
        child_id=link.child_id,
        relationship_type=link.relationship_type,
    )


@router.post(
    "/import",
    response_model=ImportResultResponse,
    summary="Excel/CSV orqali bolalarni ommaviy import qilish (MANAGER/OWNER)",
)
async def import_children(
    branch_id: uuid.UUID = Form(...),
    group_id: uuid.UUID = Form(...),
    dry_run: bool = Form(default=True),
    upload: UploadFile = FastFile(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ImportResultResponse:
    # Bir baytga ortiq o'qiladi — shunda limitdan oshganini bilamiz, lekin
    # katta faylni to'liq xotiraga yuklamaymiz.
    content = await upload.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise FileRejectedError(
            f"Import fayli {MAX_IMPORT_BYTES // (1024 * 1024)} MB dan oshmasligi kerak."
        )
    return await ImportService(session).run(
        content,
        upload.filename or "import.csv",
        branch_id,
        group_id,
        dry_run,
        current_user,
    )
