"""Invoice va tuzatma endpointlari (5.5-bo'lim).

Tarif guruhning oylik tarifidan olinadi — alohida tarif rejalari
(`/fee-plans`) interfeysda hech qachon ishlatilmagani uchun olib tashlandi.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.finance import Invoice
from app.schemas.finance import (
    AdjustmentCreateRequest,
    InvoiceGenerateRequest,
    InvoiceGenerateResponse,
    InvoiceResponse,
)
from app.services.billing_service import BillingService

router = APIRouter(tags=["billing"])


def _invoice_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        branch_id=invoice.branch_id,
        child_id=invoice.child_id,
        billing_period=invoice.billing_period,
        due_date=invoice.due_date,
        original_amount=invoice.original_amount,
        discount_amount=invoice.discount_amount,
        adjusted_amount=invoice.adjusted_amount,
        paid_amount=invoice.paid_amount,
        outstanding_amount=invoice.outstanding_amount,
        status=invoice.status,
    )


@router.post(
    "/invoices/generate",
    response_model=InvoiceGenerateResponse,
    summary="Oylik invoice'larni yaratish (MANAGER/OWNER)",
)
async def generate_invoices(
    payload: InvoiceGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvoiceGenerateResponse:
    created, skipped, period = await BillingService(session).generate_invoices(
        payload, current_user
    )
    return InvoiceGenerateResponse(
        created=created, skipped=skipped, billing_period=period
    )


@router.get(
    "/children/{child_id}/invoices",
    response_model=list[InvoiceResponse],
    summary="Bola invoice'lari",
)
async def list_child_invoices(
    child_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvoiceResponse]:
    invoices = await BillingService(session).list_invoices_for_child(
        child_id, current_user
    )
    return [_invoice_response(i) for i in invoices]


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
    summary="Filialning bir oylik barcha invoice'lari (MANAGER/OWNER)",
)
async def list_branch_invoices(
    branch_id: uuid.UUID = Query(...),
    billing_period: date = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvoiceResponse]:
    invoices = await BillingService(session).list_invoices_for_branch_period(
        branch_id, billing_period, current_user
    )
    return [_invoice_response(i) for i in invoices]


@router.post(
    "/invoices/{invoice_id}/adjustments",
    response_model=InvoiceResponse,
    summary="Invoice tuzatmasi (chegirma/qo'shimcha/qarz kechirish)",
)
async def adjust_invoice(
    invoice_id: uuid.UUID,
    payload: AdjustmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvoiceResponse:
    invoice = await BillingService(session).add_adjustment(
        invoice_id, payload, current_user
    )
    return _invoice_response(invoice)


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    summary="Invoice'ni bekor qilish (to'lovsiz bo'lsa)",
)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvoiceResponse:
    invoice = await BillingService(session).cancel_invoice(invoice_id, current_user)
    return _invoice_response(invoice)
