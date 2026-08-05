"""Oziq-ovqat va oshxona ombori uchun DB so'rovlari."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import StockMovementType
from app.models.food import (
    FoodProduct,
    FoodStockMovement,
    Meal,
    MealIngredient,
    MealLog,
)
from app.utils.money import ZERO


class FoodProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, product: FoodProduct) -> None:
        self._session.add(product)

    async def get_by_id(self, product_id: uuid.UUID) -> FoodProduct | None:
        return await self._session.get(FoodProduct, product_id)

    async def list_by_ids(self, product_ids: Sequence[uuid.UUID]) -> list[FoodProduct]:
        if not product_ids:
            return []
        stmt = select(FoodProduct).where(FoodProduct.id.in_(product_ids))
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_branch(self, branch_id: uuid.UUID) -> list[FoodProduct]:
        stmt = (
            select(FoodProduct)
            .where(FoodProduct.branch_id == branch_id)
            .order_by(FoodProduct.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def name_exists(self, branch_id: uuid.UUID, name: str) -> bool:
        stmt = (
            select(FoodProduct.id)
            .where(FoodProduct.branch_id == branch_id, FoodProduct.name == name)
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None


class StockMovementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, movement: FoodStockMovement) -> None:
        self._session.add(movement)

    async def current_stock(self, product_id: uuid.UUID) -> Decimal:
        """Mahsulot joriy qoldig'i — barcha harakatlardan hisoblanadi (ledger)."""
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            FoodStockMovement.movement_type
                            == StockMovementType.IN.value,
                            FoodStockMovement.quantity,
                        ),
                        else_=-FoodStockMovement.quantity,
                    )
                ),
                0,
            )
        ).where(FoodStockMovement.product_id == product_id)
        value = (await self._session.execute(stmt)).scalar_one()
        return Decimal(str(value))

    async def stock_by_products(
        self, product_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        """Bir nechta mahsulot uchun joriy qoldiqni bitta so'rovda hisoblaydi."""
        if not product_ids:
            return {}
        stmt = (
            select(
                FoodStockMovement.product_id,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                FoodStockMovement.movement_type
                                == StockMovementType.IN.value,
                                FoodStockMovement.quantity,
                            ),
                            else_=-FoodStockMovement.quantity,
                        )
                    ),
                    0,
                ),
            )
            .where(FoodStockMovement.product_id.in_(product_ids))
            .group_by(FoodStockMovement.product_id)
        )
        rows = (await self._session.execute(stmt)).all()
        result = {pid: ZERO for pid in product_ids}
        for product_id, total in rows:
            result[product_id] = Decimal(str(total))
        return result

    async def net_before(self, product_id: uuid.UUID, before: datetime) -> Decimal:
        """Berilgan vaqtdan oldingi (ochilish) qoldiq."""
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            FoodStockMovement.movement_type
                            == StockMovementType.IN.value,
                            FoodStockMovement.quantity,
                        ),
                        else_=-FoodStockMovement.quantity,
                    )
                ),
                0,
            )
        ).where(
            FoodStockMovement.product_id == product_id,
            FoodStockMovement.occurred_at < before,
        )
        value = (await self._session.execute(stmt)).scalar_one()
        return Decimal(str(value))

    async def sum_in_period(
        self,
        product_id: uuid.UUID,
        movement_type: str,
        start: datetime,
        end: datetime,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(FoodStockMovement.quantity), 0)).where(
            FoodStockMovement.product_id == product_id,
            FoodStockMovement.movement_type == movement_type,
            FoodStockMovement.occurred_at >= start,
            FoodStockMovement.occurred_at < end,
        )
        value = (await self._session.execute(stmt)).scalar_one()
        return Decimal(str(value))


class MealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, meal: Meal) -> None:
        self._session.add(meal)

    def add_ingredient(self, ingredient: MealIngredient) -> None:
        self._session.add(ingredient)

    async def get_by_id(self, meal_id: uuid.UUID) -> Meal | None:
        stmt = (
            select(Meal)
            .where(Meal.id == meal_id)
            .options(selectinload(Meal.ingredients))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_branch(self, branch_id: uuid.UUID) -> list[Meal]:
        stmt = (
            select(Meal)
            .where(Meal.branch_id == branch_id)
            .options(selectinload(Meal.ingredients))
            .order_by(Meal.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())


class MealLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, log: MealLog) -> None:
        self._session.add(log)

    async def list_by_branch(
        self, branch_id: uuid.UUID, limit: int = 100
    ) -> list[MealLog]:
        stmt = (
            select(MealLog)
            .where(MealLog.branch_id == branch_id)
            .order_by(MealLog.serving_date.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
