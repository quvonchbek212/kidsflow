"""Invoice summalarini qayta hisoblash (adjustment/to'lov o'zgargach).

Adjustmentlar va bekor qilinmagan to'lov taqsimotlari asosida invoice'ning
discount/adjusted/paid/outstanding/status maydonlarini yangilaydi.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InvoiceStatus
from app.models.finance import Invoice
from app.repositories.finance_repository import InvoiceRepository
from app.services.invoice_math import compute_totals
from app.utils.money import money


async def recompute_invoice(
    session: AsyncSession,
    invoice: Invoice,
    *,
    cancelled: bool | None = None,
) -> None:
    repo = InvoiceRepository(session)
    adjustments = await repo.adjustments_for(invoice.id)
    paid = await repo.paid_for(invoice.id)

    is_cancelled = (
        cancelled
        if cancelled is not None
        else invoice.status == InvoiceStatus.CANCELLED.value
    )
    totals = compute_totals(
        money(Decimal(str(invoice.original_amount))),
        adjustments,
        paid,
        cancelled=is_cancelled,
    )

    invoice.discount_amount = totals.discount_amount
    invoice.adjusted_amount = totals.adjusted_amount
    invoice.paid_amount = money(paid)
    invoice.outstanding_amount = totals.outstanding_amount
    invoice.status = totals.status
