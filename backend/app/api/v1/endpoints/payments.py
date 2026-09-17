"""To'lov endpointlari (4.5-bo'lim)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.finance import PaymentTransaction
from app.schemas.finance import (
    PaymentAllocationOut,
    PaymentRecordRequest,
    PaymentResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


async def _payment_response(
    service: PaymentService, payment: PaymentTransaction
) -> PaymentResponse:
    allocations, unallocated = await service.allocations_with_unallocated(payment)
    return PaymentResponse(
        id=payment.id,
        branch_id=payment.branch_id,
        child_id=payment.child_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        paid_at=payment.paid_at,
        status=payment.status,
        allocations=[
            PaymentAllocationOut(invoice_id=a.invoice_id, amount=a.amount)
            for a in allocations
        ],
        unallocated_amount=unallocated,
    )


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="To'lov kiritish (MANAGER/OWNER, idempotent)",
)
async def record_payment(
    payload: PaymentRecordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentResponse:
    service = PaymentService(session)
    payment = await service.record(payload, current_user)
    return await _payment_response(service, payment)


@router.get(
    "",
    response_model=list[PaymentResponse],
    summary="Bolaning oxirgi to'lovlari (MANAGER/OWNER)",
)
async def list_child_payments(
    child_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PaymentResponse]:
    service = PaymentService(session)
    payments = await service.list_for_child(child_id, current_user)
    return [await _payment_response(service, p) for p in payments]


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="To'lov ma'lumoti",
)
async def get_payment(
    payment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentResponse:
    service = PaymentService(session)
    payment = await service.get_accessible(payment_id, current_user)
    return await _payment_response(service, payment)


@router.post(
    "/{payment_id}/reverse",
    response_model=PaymentResponse,
    summary="To'lovni bekor qilish (reversal, o'chirilmaydi)",
)
async def reverse_payment(
    payment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentResponse:
    service = PaymentService(session)
    payment = await service.reverse(payment_id, current_user)
    return await _payment_response(service, payment)
