"""Umumiy normalizatsiya yordamchilari."""

from __future__ import annotations

import re

_USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,64}$")


def normalize_email(raw: str | None) -> str | None:
    """Email'ni kichik harflarga o'tkazadi va bo'sh joylarni olib tashlaydi."""
    if raw is None:
        return None
    cleaned = raw.strip().lower()
    return cleaned or None


class InvalidUsernameError(ValueError):
    pass


def normalize_username(raw: str) -> str:
    """Username'ni kichik harfga o'tkazadi va formatni tekshiradi.

    Login sifatida ishlatiladi (masalan "Quvonchbek" -> "quvonchbek"):
    faqat lotin harflari, raqam, nuqta va pastki chiziq, 3-64 belgi.
    """
    cleaned = raw.strip().lower()
    if not _USERNAME_RE.match(cleaned):
        raise InvalidUsernameError(
            "Login faqat lotin harflari, raqam, '_' va '.' belgilaridan "
            "iborat bo'lishi, 3-64 belgi bo'lishi kerak."
        )
    return cleaned
