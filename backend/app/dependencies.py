"""Umumiy FastAPI dependencylar: autentifikatsiya, RBAC va DB sessiya.

So'rov zanjiri (2.3-bo'lim):
    get_current_user → check_user_is_active → (endpointda) branch/role tekshiruvi
"""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.permissions import CurrentUser, RoleGrant
from app.core.security import decode_access_token
from app.database import get_session
from app.models.enums import Role
from app.models.user import User, UserRoleAssignment

__all__ = [
    "Settings",
    "get_settings",
    "get_session",
    "get_current_user",
    "require_roles",
    "require_bot_token",
    "client_ip",
]

_bearer = HTTPBearer(auto_error=False)


def _is_active_grant(assignment: UserRoleAssignment, now: datetime) -> bool:
    """Rol biriktirmasi hozir amal qilayotganini tekshiradi."""
    not_started = assignment.valid_from is not None and assignment.valid_from > now
    expired = assignment.valid_until is not None and assignment.valid_until < now
    return not (not_started or expired)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    """Bearer tokendan foydalanuvchini aniqlaydi va faol rollarini yuklaydi."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Autentifikatsiya tokeni yo'q.")

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role_assignments))
    )
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None or not user.is_active:
        raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas.")

    now = datetime.now(UTC)
    grants = tuple(
        RoleGrant(role=Role(a.role), branch_id=a.branch_id)
        for a in user.role_assignments
        if _is_active_grant(a, now)
    )
    return CurrentUser(id=user.id, full_name=user.full_name, grants=grants)


def require_roles(
    *roles: Role,
) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Berilgan rollardan biriga ega foydalanuvchini talab qiluvchi dependency."""

    async def _dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_any_role(*roles):
            raise PermissionDeniedError("Bu amal uchun ruxsat yo'q.")
        return current_user

    return _dependency


async def require_bot_token(
    x_bot_token: str = Header(..., alias="X-Bot-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Telegram bot endpointlarini umumiy sir (bot API token) bilan himoyalaydi.

    Bot faqat backend API bilan ishlaydi; unga DB paroli berilmaydi (7-bo'lim).
    """
    if not hmac.compare_digest(x_bot_token, settings.bot_api_token):
        raise AuthenticationError("Bot API token noto'g'ri.")


def client_ip(request: Request) -> str | None:
    """So'rov IP manzilini qaytaradi (audit uchun)."""
    if request.client is None:
        return None
    return request.client.host
