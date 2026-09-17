"""Autentifikatsiya endpointlari: login, refresh, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import CurrentUser
from app.core.rate_limit import login_rate_limit, refresh_rate_limit
from app.database import get_session
from app.dependencies import client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    ResetPasswordRequest,
    RoleGrantOut,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Tizimga kirish",
    dependencies=[Depends(login_rate_limit)],
)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    ip: str | None = Depends(client_ip),
) -> TokenResponse:
    service = AuthService(session)
    return await service.login(
        payload.login,
        payload.password,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Tokenni yangilash",
    dependencies=[Depends(refresh_rate_limit)],
)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    service = AuthService(session)
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Chiqish (refresh tokenni bekor qilish)",
)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = AuthService(session)
    await service.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CurrentUserResponse, summary="Joriy foydalanuvchi")
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CurrentUserResponse:
    stmt = (
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.role_assignments))
    )
    user = (await session.execute(stmt)).scalar_one()
    return _to_current_user(user)


@router.patch(
    "/me",
    response_model=CurrentUserResponse,
    summary="O'z profilini tahrirlash (ism, telefon, til)",
)
async def update_me(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CurrentUserResponse:
    """Har qanday rol o'z profilini tahrirlaydi.

    `PATCH /users/{id}` faqat OWNER uchun — u boshqa xodimning profilini
    (rol, maosh, faollik) o'zgartiradi. Bu esa foydalanuvchining o'ziga tegishli
    va cheklangan maydonlar bilan ishlaydi.
    """
    service = AuthService(session)
    await service.update_own_profile(current_user.id, payload)

    stmt = (
        select(User)
        .where(User.id == current_user.id)
        .options(selectinload(User.role_assignments))
    )
    user = (await session.execute(stmt)).scalar_one()
    return _to_current_user(user)


def _to_current_user(user: User) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        phone=user.phone,
        email=user.email,
        preferred_language=user.preferred_language,
        roles=[
            RoleGrantOut(role=a.role, branch_id=a.branch_id)
            for a in user.role_assignments
        ],
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Parolni tiklash havolasini emailga yuborish",
    dependencies=[Depends(login_rate_limit)],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = AuthService(session)
    await service.request_password_reset(payload.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Token orqali yangi parol o'rnatish",
    dependencies=[Depends(login_rate_limit)],
)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = AuthService(session)
    await service.reset_password(payload.token, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
