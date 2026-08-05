"""Oziq-ovqat va oshxona ombori endpointlari.

Mahsulot/ovqat CRUD faqat MANAGER/OWNER; ovqat qaydini (meal-log) esa filialga
biriktirilgan TEACHER (masalan, oshpaz lavozimli xodim) ham kirita oladi.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_session
from app.dependencies import get_current_user
from app.models.food import FoodProduct, Meal, MealLog
from app.schemas.food import (
    MealCreateRequest,
    MealIngredientOut,
    MealLogRequest,
    MealLogResponse,
    MealResponse,
    ProductCreateRequest,
    ProductResponse,
    StockMovementRequest,
    StockMovementResponse,
    StockReportResponse,
)
from app.services.food_service import (
    FoodReportService,
    MealLogService,
    MealService,
    ProductService,
    StockService,
)

router = APIRouter(prefix="/food", tags=["food"])


def _product_response(product: FoodProduct, stock: Decimal) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        branch_id=product.branch_id,
        name=product.name,
        unit=product.unit,
        unit_cost=product.unit_cost,
        current_stock=stock,
        is_active=product.is_active,
    )


def _meal_response(meal: Meal) -> MealResponse:
    return MealResponse(
        id=meal.id,
        branch_id=meal.branch_id,
        name=meal.name,
        description=meal.description,
        is_active=meal.is_active,
        ingredients=[
            MealIngredientOut(
                product_id=ing.product_id,
                quantity_per_serving=ing.quantity_per_serving,
            )
            for ing in meal.ingredients
        ],
    )


def _meal_log_response(log: MealLog) -> MealLogResponse:
    return MealLogResponse(
        id=log.id,
        branch_id=log.branch_id,
        meal_id=log.meal_id,
        serving_date=log.serving_date,
        servings_count=log.servings_count,
    )


# --- Mahsulotlar ---


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ombor mahsuloti yaratish (MANAGER/OWNER)",
)
async def create_product(
    payload: ProductCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProductResponse:
    product = await ProductService(session).create(payload, current_user)
    return _product_response(product, Decimal("0"))


@router.get(
    "/products",
    response_model=list[ProductResponse],
    summary="Ombor mahsulotlari va joriy qoldiq (MANAGER/OWNER)",
)
async def list_products(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProductResponse]:
    rows = await ProductService(session).list_for_branch(branch_id, current_user)
    return [_product_response(p, stock) for p, stock in rows]


@router.post(
    "/stock-movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ombor harakati kiritish: kirim/chiqim (MANAGER/OWNER)",
)
async def record_stock_movement(
    payload: StockMovementRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StockMovementResponse:
    movement = await StockService(session).record(payload, current_user)
    return StockMovementResponse(
        id=movement.id,
        branch_id=movement.branch_id,
        product_id=movement.product_id,
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        reason=movement.reason,
        unit_cost=movement.unit_cost,
        note=movement.note,
        occurred_at=movement.occurred_at,
    )


# --- Ovqatlar (menyu) ---


@router.post(
    "/meals",
    response_model=MealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ovqat (retsept) yaratish (MANAGER/OWNER)",
)
async def create_meal(
    payload: MealCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealResponse:
    meal = await MealService(session).create(payload, current_user)
    return _meal_response(meal)


@router.get(
    "/meals",
    response_model=list[MealResponse],
    summary="Ovqatlar (menyu) ro'yxati (MANAGER/OWNER)",
)
async def list_meals(
    branch_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MealResponse]:
    meals = await MealService(session).list_for_branch(branch_id, current_user)
    return [_meal_response(m) for m in meals]


@router.post(
    "/meal-logs",
    response_model=MealLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ovqat berilganini qayd etish (mahsulot sarfini avtomatik hisoblaydi)",
)
async def log_meal(
    payload: MealLogRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealLogResponse:
    log = await MealLogService(session).log(payload, current_user)
    return _meal_log_response(log)


# --- Hisob-kitob ---


@router.get(
    "/stock-report",
    response_model=StockReportResponse,
    summary="Ombor hisob-kitobi: kirim/chiqim/qoldiq (MANAGER/OWNER)",
)
async def stock_report(
    branch_id: uuid.UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StockReportResponse:
    return await FoodReportService(session).stock_report(
        branch_id, period_start, period_end, current_user
    )
