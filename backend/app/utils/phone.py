"""Telefon raqamlarini normallashtirish (O'zbekiston formati, 5.2-bo'lim).

Barcha raqamlar `+998XXXXXXXXX` (E.164) ko'rinishiga keltiriladi. Bu unique
constraint to'g'ri ishlashini ta'minlaydi.
"""

from __future__ import annotations

import re

_NON_DIGIT = re.compile(r"\D")
_UZ_CODE = "998"
_NATIONAL_LENGTH = 9  # kod'siz raqam uzunligi (masalan 90 123 45 67)


class InvalidPhoneError(ValueError):
    """Telefon raqami noto'g'ri formatda."""


def normalize_phone(raw: str | None) -> str | None:
    """Telefon raqamini `+998XXXXXXXXX` ko'rinishiga keltiradi.

    None yoki bo'sh qiymat uchun None qaytaradi. Noto'g'ri raqamda
    `InvalidPhoneError` ko'taradi.
    """
    if raw is None:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    digits = _NON_DIGIT.sub("", stripped)

    if len(digits) == _NATIONAL_LENGTH:
        # Faqat milliy raqam berilgan: 901234567
        digits = _UZ_CODE + digits
    elif len(digits) == len(_UZ_CODE) + _NATIONAL_LENGTH and digits.startswith(
        _UZ_CODE
    ):
        # To'liq raqam: 998901234567
        pass
    else:
        raise InvalidPhoneError(
            "Telefon raqami O'zbekiston formatida bo'lishi kerak (+998XXXXXXXXX)."
        )

    return "+" + digits
