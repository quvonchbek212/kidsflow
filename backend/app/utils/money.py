"""Pul qiymatlari bilan ishlash yordamchilari.

Pul har doim `Decimal` sifatida, ikki xona aniqlik bilan hisoblanadi (5-bo'lim:
NUMERIC(18,2)). Float ishlatilmaydi — yaxlitlash xatolarini oldini olish uchun.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    """Qiymatni ikki xonali pul Decimal'iga keltiradi."""
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def is_positive(value: Decimal) -> bool:
    return value > ZERO
