"""Oldindan to'langan pulni yangi hisob-fakturalarga yozish.

To'lov qabul qilinganda u bolaning mavjud qarzlariga taqsimlanadi
(`PaymentService.record`). Lekin hisob-faktura hali yo'q bo'lsa (masalan, oy
boshida ota-ona avval pul olib kelgan) pul hech qayerga yozilmay qolardi va
keyin yaratilgan hisob uni ko'rmasdi — bola to'lagan bo'lsa ham qarzdor
bo'lib ko'rinardi. Hisob-fakturalar avtomatik yaratiladigan bo'lgach bu
holat odatiy bo'lib qoladi, shuning uchun har yangi hisobdan keyin shu
funksiya chaqiriladi.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import PaymentAllocation
from app.repositories.finance_repository import InvoiceRepository, PaymentRepository
from app.services.invoice_recompute import recompute_invoice
from app.utils.money import ZERO, money


async def apply_unallocated(session: AsyncSession, child_id: uuid.UUID) -> Decimal:
    """Bolaning bo'sh qolgan to'lovlarini to'lanmagan hisoblariga yozadi.

    Ikkala tomonda ham eng eskisi birinchi: eski to'lov eski qarzni yopadi.
    Qaytaradi: yozilgan umumiy summa.
    """
    payments = PaymentRepository(session)
    credits = await payments.unallocated_for_child(child_id)
    if not credits:
        return ZERO

    invoices = InvoiceRepository(session)
    applied = ZERO
    for invoice in await invoices.list_outstanding_for_child(child_id):
        due = money(Decimal(str(invoice.outstanding_amount)))
        touched = False
        while due > ZERO and credits:
            payment, free = credits[0]
            portion = min(due, free)
            payments.add_allocation(
                PaymentAllocation(
                    payment_transaction_id=payment.id,
                    invoice_id=invoice.id,
                    amount=portion,
                )
            )
            due -= portion
            applied += portion
            touched = True
            if free - portion > ZERO:
                credits[0] = (payment, free - portion)
            else:
                credits.pop(0)
        if touched:
            await session.flush()
            await recompute_invoice(session, invoice)
        if not credits:
            break
    return applied
