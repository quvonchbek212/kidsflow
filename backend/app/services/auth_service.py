"""Autentifikatsiya xizmati: login, refresh (rotation), logout (11-bo'lim)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_reset_token_expiry,
    refresh_token_expiry,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.services.audit_service import AuditService
from app.services.email_sender import EmailSender, get_default_email_sender
from app.utils.phone import InvalidPhoneError, normalize_phone
from app.utils.validators import normalize_email


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender | None = None,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._password_resets = PasswordResetRepository(session)
        self._audit = AuditService(session)
        self._email_sender = email_sender or get_default_email_sender()

    async def login(
        self,
        login: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        user = await self._find_user_by_login(login)

        if (
            user is None
            or user.password_hash is None
            or not verify_password(password, user.password_hash)
        ):
            # Muvaffaqiyatsiz login auditga yoziladi (11-bo'lim). Xato ko'tarilgach
            # so'rov tranzaksiyasi rollback qilinadi, shuning uchun yozuvni shu
            # yerda commit qilamiz — aks holda u yo'qolib ketardi va brute-force
            # urinishlari jurnalda ko'rinmasdi.
            self._audit.record(
                action="LOGIN_FAILED",
                entity_type="user",
                entity_id=user.id if user else None,
                actor_user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self._session.commit()
            raise AuthenticationError("Login yoki parol noto'g'ri.")

        if not user.is_active:
            raise AuthenticationError("Hisob faol emas.")

        user.last_login_at = datetime.now(UTC)
        self._audit.record(
            action="LOGIN_SUCCESS",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return self._issue_tokens(user)

    async def refresh(self, raw_token: str) -> TokenResponse:
        """Refresh token rotation: eski token bekor qilinib, yangisi beriladi."""
        token_hash = hash_opaque_token(raw_token)
        stored = await self._refresh_tokens.get_active_by_hash(token_hash)
        if stored is None:
            raise AuthenticationError("Refresh token yaroqsiz yoki muddati o'tgan.")

        # Rotation — eski token darhol bekor qilinadi.
        self._refresh_tokens.revoke(stored)

        user = await self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Hisob mavjud emas yoki faol emas.")

        return self._issue_tokens(user)

    async def issue_for_telegram(self, telegram_user_id: int) -> TokenResponse:
        """Bot ota-ona nomidan token oladi (7-bo'lim).

        Ota-ona parol bilan emas, bog'langan Telegram hisobi orqali kiradi.
        """
        user = await self._users.get_by_telegram_id(telegram_user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Telegram hisobi bog'lanmagan yoki faol emas.")
        return self._issue_tokens(user)

    async def logout(self, raw_token: str) -> None:
        """Refresh tokenni bekor qiladi."""
        token_hash = hash_opaque_token(raw_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is not None:
            self._refresh_tokens.revoke(stored)

    async def request_password_reset(self, email: str) -> None:
        """Email orqali parolni tiklash havolasini yuboradi.

        Xavfsizlik uchun email ro'yxatdan o'tganmi yoki yo'qmi — bir xil javob
        qaytadi (foydalanuvchi mavjudligini oshkor qilmaslik).
        """
        normalized = normalize_email(email)
        if normalized is None:
            return
        user = await self._users.get_by_email(normalized)
        if user is None or not user.is_active:
            return

        raw_token = generate_opaque_token()
        self._password_resets.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw_token),
                expires_at=password_reset_token_expiry(),
            )
        )
        await self._session.flush()

        settings = get_settings()
        reset_link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
        await self._email_sender.send(
            to=user.email or normalized,
            subject="KIDSFLOW — parolni tiklash",
            body=(
                f"Salom, {user.full_name}!\n\n"
                "Parolingizni tiklash uchun quyidagi havolani oching "
                f"({settings.password_reset_ttl_minutes} daqiqa amal qiladi):\n"
                f"{reset_link}\n\n"
                "Agar bu so'rovni siz yubormagan bo'lsangiz, xatni e'tiborsiz "
                "qoldiring."
            ),
        )

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        """Token orqali yangi parol o'rnatadi va barcha sessiyalarni yopadi."""
        token_hash = hash_opaque_token(raw_token)
        stored = await self._password_resets.get_active_by_hash(token_hash)
        if stored is None:
            raise AuthenticationError("Havola yaroqsiz yoki muddati o'tgan.")

        user = await self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Hisob mavjud emas yoki faol emas.")

        user.password_hash = hash_password(new_password)
        self._password_resets.mark_used(stored)

        self._audit.record(
            action="PASSWORD_RESET",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
        )

    # --- ichki yordamchilar ---

    async def _find_user_by_login(self, login: str) -> User | None:
        # Login birinchi navbatda username sifatida sinaladi (asosiy oqim).
        # Orqaga moslik uchun telefon/email bilan kirish ham qo'llab-quvvatlanadi.
        username_candidate = login.strip().lower() or None
        phone_candidate: str | None
        try:
            phone_candidate = normalize_phone(login)
        except InvalidPhoneError:
            phone_candidate = None
        email_candidate = normalize_email(login) if "@" in login else None
        return await self._users.get_by_login(
            username_candidate, phone_candidate, email_candidate
        )

    def _issue_tokens(self, user: User) -> TokenResponse:
        settings = get_settings()
        access_token = create_access_token(user.id)

        raw_refresh = generate_opaque_token()
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw_refresh),
                expires_at=refresh_token_expiry(),
            )
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_ttl_minutes * 60,
        )
