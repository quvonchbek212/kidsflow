"""Invoice pul hisob-kitobi — sof (DB'siz) mantiq, alohida test qilinadi.

Formulalar aniq va SQL/Decimal orqali (4.7-bo'lim: AI raqamlarni o'ylab topmaydi).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import AdjustmentType, InvoiceStatus
from app.utils.money import ZERO, money


@dataclass(frozen=True)
class InvoiceTotals:
    discount_amount: Decimal  # umumiy kamaytirishlar (DISCOUNT + WRITE_OFF)
    adjusted_amount: Decimal  # to'lanishi kerak bo'lgan sof summa
    outstanding_amount: Decimal  # qolgan qarz
    status: str


def compute_adjusted(
    original_amount: Decimal,
    adjustments: list[tuple[str, Decimal]],
) -> tuple[Decimal, Decimal]:
    """(discount_amount, adjusted_amount) ni hisoblaydi.

    DISCOUNT va WRITE_OFF summani kamaytiradi; SURCHARGE oshiradi. Natija manfiy
    bo'lmaydi (0 dan pastga tushmaydi).
    """
    reductions = ZERO
    surcharges = ZERO
    for atype, amount in adjustments:
        if atype in (AdjustmentType.DISCOUNT.value, AdjustmentType.WRITE_OFF.value):
            reductions += amount
        elif atype == AdjustmentType.SURCHARGE.value:
            surcharges += amount

    adjusted = original_amount - reductions + surcharges
    if adjusted < ZERO:
        adjusted = ZERO
    return money(reductions), money(adjusted)


def compute_status(
    adjusted_amount: Decimal,
    paid_amount: Decimal,
    *,
    cancelled: bool = False,
) -> str:
    """Invoice holatini aniqlaydi.

    OVERDUE bu yerda hisoblanmaydi — u alohida `mark_overdue` amali orqali
    (muddati o'tgan invoice'larni belgilash, 9-bo'lim) qo'yiladi.
    """
    if cancelled:
        return InvoiceStatus.CANCELLED.value
    outstanding = adjusted_amount - paid_amount
    if outstanding <= ZERO:
        return InvoiceStatus.PAID.value
    if paid_amount > ZERO:
        return InvoiceStatus.PARTIALLY_PAID.value
    return InvoiceStatus.OPEN.value


def compute_totals(
    original_amount: Decimal,
    adjustments: list[tuple[str, Decimal]],
    paid_amount: Decimal,
    *,
    cancelled: bool = False,
) -> InvoiceTotals:
    """Barcha invoice summalarini va holatini bir joyda hisoblaydi."""
    discount, adjusted = compute_adjusted(original_amount, adjustments)
    paid = money(paid_amount)
    outstanding = money(max(adjusted - paid, ZERO))
    status = compute_status(adjusted, paid, cancelled=cancelled)
    return InvoiceTotals(
        discount_amount=discount,
        adjusted_amount=adjusted,
        outstanding_amount=outstanding,
        status=status,
    )
