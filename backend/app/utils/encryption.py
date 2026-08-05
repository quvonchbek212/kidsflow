"""Maxfiy matnlarni (tibbiy izohlar, sog'liq yozuvlari) shifrlash (11-bo'lim).

Fernet (AES-128-CBC + HMAC) simmetrik shifrlashdan foydalaniladi. Kalit har qanday
parol-satrdan barqaror ravishda hosil qilinadi (SHA-256 → url-safe base64).
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    passphrase = get_settings().encryption_key
    digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(plaintext: str | None) -> str | None:
    """Matnni shifrlaydi. None yoki bo'sh qiymat uchun None qaytaradi."""
    if plaintext is None or plaintext == "":
        return None
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str | None) -> str | None:
    """Shifrlangan matnni ochadi. Yaroqsiz token uchun None qaytaradi."""
    if token is None or token == "":
        return None
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
