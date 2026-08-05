"""Fayl yuklash va yuklab olish endpointlari (11-bo'lim).

Fayllar maxfiy — faqat vakolatli foydalanuvchi backend orqali oladi. To'g'ridan
ochiq URL berilmaydi.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi import File as FastFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user, get_settings
from app.schemas.file import FileResponse
from app.services.file_service import FileService
from app.utils.file_storage import FileValidationError

router = APIRouter(prefix="/files", tags=["files"])


class _UploadError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


@router.post(
    "",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fayl yuklash (xodimlar)",
)
async def upload_file(
    upload: UploadFile = FastFile(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    content = await upload.read()
    content_type = upload.content_type or "application/octet-stream"
    try:
        record = await FileService(session).upload(
            content, content_type, upload.filename or "file", current_user
        )
    except FileValidationError as exc:
        raise _UploadError(str(exc)) from exc
    return FileResponse(
        id=record.id,
        original_name=record.original_name,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        scan_status=record.scan_status,
        created_at=record.created_at,
    )


@router.get(
    "/{file_id}",
    summary="Faylni yuklab olish (kirish huquqiga ega foydalanuvchi)",
    dependencies=[Depends(get_settings)],
)
async def download_file(
    file_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    result = await FileService(session).download(file_id, current_user)
    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={"Content-Disposition": f'inline; filename="{result.original_name}"'},
    )
