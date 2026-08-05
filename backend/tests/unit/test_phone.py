"""Telefon normalizatsiyasi uchun unit testlar (13-bo'lim: telefon normalizatsiyasi)."""

from __future__ import annotations

import pytest
from app.utils.phone import InvalidPhoneError, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("901234567", "+998901234567"),
        ("90 123 45 67", "+998901234567"),
        ("+998 90 123 45 67", "+998901234567"),
        ("998901234567", "+998901234567"),
        ("(90) 123-45-67", "+998901234567"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_phone(raw: str | None, expected: str | None) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["123", "12345", "8901234567890", "abc"])
def test_normalize_phone_invalid(raw: str) -> None:
    with pytest.raises(InvalidPhoneError):
        normalize_phone(raw)
