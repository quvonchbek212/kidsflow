"""Ilova darajasidagi xatoliklar va ularning HTTP handlerlari.

Xato javoblari izchil `{"detail": "..."}` shaklida qaytadi (8-bo'lim: tushunarli
xato xabarlari).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Barcha biznes xatoliklari uchun asosiy sinf."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "So'rovni bajarib bo'lmadi."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Ma'lumot topilmadi."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Ma'lumot allaqachon mavjud."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Autentifikatsiya talab qilinadi."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Ruxsat yo'q."


class TooManyRequestsError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "So'rovlar juda ko'p. Birozdan so'ng qayta urinib ko'ring."


class FileRejectedError(AppError):
    """Fayl xavfsizlik tekshiruvidan o'tmadi (11-bo'lim)."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Fayl qabul qilinmadi."


class SetupAlreadyCompletedError(ConflictError):
    detail = "Tizim allaqachon sozlangan."


class InvalidSetupTokenError(AuthenticationError):
    detail = "Setup token noto'g'ri."


def register_exception_handlers(app: FastAPI) -> None:
    """`AppError` va uning avlodlarini HTTP javobga aylantiradi."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Ushlanmagan istisnolar ham `{"detail": …}` shaklida qaytadi.

        Busiz ular Starlette'ning standart oddiy matnli "Internal Server Error"
        javobiga tushardi. Frontenddagi `extractDetail()` uni tahlil qila
        olmasdi va foydalanuvchi tushunarsiz xato ko'rardi.

        Xatoning o'zi (traceback bilan) faqat log'ga tushadi — javobda hech
        qanday ichki tafsilot bo'lmaydi. `request_id` esa javobga ham,
        log'ga ham yoziladi: foydalanuvchi qo'ng'iroq qilganda shu raqam
        bo'yicha aynan o'sha so'rovni topish mumkin.
        """
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        logger.exception(
            "Ushlanmagan xatolik",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Kutilmagan xatolik yuz berdi.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
