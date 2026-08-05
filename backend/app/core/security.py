"""Parol hash (Argon2id) va JWT / refresh token yordamchilari (11-bo'lim)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import get_settings

# Argon2id — argon2-cffi ning standart turi.
_password_hasher = PasswordHasher()

TokenType = Literal["access"]


# --- Parol ---


def hash_password(password: str) -> str:
    """Parolni Argon2id bilan hash qiladi."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Parolni hash bilan solishtiradi."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Hash parametrlari eskirganini tekshiradi (kelajakda rehash uchun)."""
    return _password_hasher.check_needs_rehash(password_hash)


# --- Access token (JWT) ---


def create_access_token(user_id: uuid.UUID) -> str:
    """Qisqa muddatli access JWT yaratadi."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()
        ),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Access tokenni tekshiradi va foydalanuvchi ID sini qaytaradi.

    Xatolik yoki noto'g'ri tur bo'lsa `ValueError` ko'taradi.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Token yaroqsiz yoki muddati o'tgan") from exc

    if payload.get("type") != "access":
        raise ValueError("Token turi noto'g'ri")

    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token subyekti yo'q")

    try:
        return uuid.UUID(subject)
    except (ValueError, TypeError) as exc:
        raise ValueError("Token subyekti noto'g'ri") from exc


# --- Opaque tokenlar (refresh token, parolni tiklash) ---


def generate_opaque_token() -> str:
    """Kriptografik tasodifiy token qiymati (ochiq matn)."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    """Opaque tokenni bazada saqlash uchun SHA-256 hash qiladi."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Orqaga moslik uchun eski nomlar (refresh token ishlatadigan joylar).
generate_refresh_token = generate_opaque_token
hash_refresh_token = hash_opaque_token


def refresh_token_expiry() -> datetime:
    """Refresh token amal qilish muddati (UTC)."""
    settings = get_settings()
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)


def password_reset_token_expiry() -> datetime:
    """Parolni tiklash tokeni amal qilish muddati (UTC)."""
    settings = get_settings()
    return datetime.now(UTC) + timedelta(minutes=settings.password_reset_ttl_minutes)
