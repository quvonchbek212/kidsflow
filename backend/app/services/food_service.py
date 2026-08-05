"""Oziq-ovqat va oshxona ombori biznes xizmati.

Ombor qoldig'i har doim harakatlar (ledger) yig'indisidan hisoblanadi — moliya
modulidagi kabi yozuvlar o'zgartirilmaydi, faqat yangi harakat qo'shiladi
(11-bo'lim). Ovqat berilgani qayd etilganda retseptga ko'ra mahsulot sarfi
avtomatik OUT harakati sifatida yaratiladi va yetarli qoldiq tekshiriladi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import Role, StockMovementType
from app.models.food import (
    FoodProduct,
    FoodStockMovement,
    Meal,
    MealIngredient,
    MealLog,
)
from app.repositories.branch_repository import BranchRepository
from app.repositories.food_repository import (
    FoodProductRepository,
    MealLogRepository,
    MealRepository,
    StockMovementRepository,
)
from app.schemas.food import (
    MealCreateRequest,
    MealLogRequest,
    ProductCreateRequest,
    StockMovementRequest,
    StockReportResponse,
    StockReportRow,
)
from app.services.access_service import AccessService
from app.services.audit_service import AuditService
from app.utils.money import ZERO


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = FoodProductRepository(session)
        self._stock = StockMovementRepository(session)
        self._branches = BranchRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(
        self, data: ProductCreateRequest, current_user: CurrentUser
    ) -> FoodProduct:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda mahsulot yaratish huquqi yo'q.")
        if await self._branches.get_by_id(data.branch_id) is None:
            raise NotFoundError("Filial topilmadi.")
        if await self._products.name_exists(data.branch_id, data.name):
            raise ConflictError("Bu nomli mahsulot allaqachon mavjud.")

        product = FoodProduct(
            branch_id=data.branch_id,
            name=data.name,
            unit=data.unit,
            unit_cost=data.unit_cost,
        )
        self._products.add(product)
        await self._session.flush()
        self._audit.record(
            action="FOOD_PRODUCT_CREATED",
            entity_type="food_product",
            entity_id=product.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
        )
        return product

    async def list_for_branch(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> list[tuple[FoodProduct, Decimal]]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial omboriga kirish huquqi yo'q.")
        products = await self._products.list_by_branch(branch_id)
        stock_map = await self._stock.stock_by_products([p.id for p in products])
        return [(p, stock_map.get(p.id, ZERO)) for p in products]


class StockService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = FoodProductRepository(session)
        self._stock = StockMovementRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def record(
        self, data: StockMovementRequest, current_user: CurrentUser
    ) -> FoodStockMovement:
        product = await self._products.get_by_id(data.product_id)
        if product is None:
            raise NotFoundError("Mahsulot topilmadi.")
        if not self._access.can_manage_branch(current_user, product.branch_id):
            raise PermissionDeniedError("Bu ombor uchun ruxsat yo'q.")

        if data.movement_type == StockMovementType.OUT:
            current = await self._stock.current_stock(product.id)
            if current < data.quantity:
                raise ConflictError(
                    f"Omborda yetarli qoldiq yo'q ({product.name}): "
                    f"mavjud {current} {product.unit}."
                )

        movement = FoodStockMovement(
            branch_id=product.branch_id,
            product_id=product.id,
            movement_type=data.movement_type.value,
            quantity=data.quantity,
            reason=data.reason.value,
            unit_cost=data.unit_cost,
            note=data.note,
            recorded_by=current_user.id,
            occurred_at=data.occurred_at or datetime.now(UTC),
        )
        self._stock.add(movement)
        await self._session.flush()
        self._audit.record(
            action="FOOD_STOCK_MOVEMENT",
            entity_type="food_stock_movement",
            entity_id=movement.id,
            actor_user_id=current_user.id,
            branch_id=product.branch_id,
            after_data={
                "product": product.name,
                "type": movement.movement_type,
                "quantity": str(data.quantity),
            },
        )
        return movement


class MealService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._meals = MealRepository(session)
        self._products = FoodProductRepository(session)
        self._branches = BranchRepository(session)
        self._access = AccessService(session)
        self._audit = AuditService(session)

    async def create(self, data: MealCreateRequest, current_user: CurrentUser) -> Meal:
        if not self._access.can_manage_branch(current_user, data.branch_id):
            raise PermissionDeniedError("Bu filialda ovqat yaratish huquqi yo'q.")
        if await self._branches.get_by_id(data.branch_id) is None:
            raise NotFoundError("Filial topilmadi.")

        products = await self._products.list_by_ids(
            [ing.product_id for ing in data.ingredients]
        )
        found_ids = {p.id for p in products}
        for ing in data.ingredients:
            if ing.product_id not in found_ids:
                raise NotFoundError("Retseptdagi mahsulot topilmadi.")

        meal = Meal(
            branch_id=data.branch_id,
            name=data.name,
            description=data.description,
        )
        self._meals.add(meal)
        await self._session.flush()

        for ing in data.ingredients:
            self._meals.add_ingredient(
                MealIngredient(
                    meal_id=meal.id,
                    product_id=ing.product_id,
                    quantity_per_serving=ing.quantity_per_serving,
                )
            )
        await self._session.flush()

        self._audit.record(
            action="MEAL_CREATED",
            entity_type="meal",
            entity_id=meal.id,
            actor_user_id=current_user.id,
            branch_id=data.branch_id,
        )
        reloaded = await self._meals.get_by_id(meal.id)
        if reloaded is None:
            raise NotFoundError("Ovqat topilmadi.")
        return reloaded

    async def list_for_branch(
        self, branch_id: uuid.UUID, current_user: CurrentUser
    ) -> list[Meal]:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial menyusiga kirish huquqi yo'q.")
        return await self._meals.list_by_branch(branch_id)


class MealLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._meals = MealRepository(session)
        self._logs = MealLogRepository(session)
        self._products = FoodProductRepository(session)
        self._stock = StockMovementRepository(session)
        self._audit = AuditService(session)

    async def log(self, data: MealLogRequest, current_user: CurrentUser) -> MealLog:
        meal = await self._meals.get_by_id(data.meal_id)
        if meal is None:
            raise NotFoundError("Ovqat topilmadi.")

        # Oshpaz (TEACHER roli) yoki MANAGER/OWNER o'z filialida qayd etadi.
        if not current_user.can_access_branch(
            meal.branch_id, Role.MANAGER, Role.TEACHER
        ):
            raise PermissionDeniedError(
                "Bu filialda ovqat qaydini kiritish huquqi yo'q."
            )

        if not meal.ingredients:
            raise ConflictError("Bu ovqatning retsepti (ingredientlari) kiritilmagan.")

        # Yetarli qoldiqni oldindan tekshiramiz — bitta transaction ichida.
        products_by_id = {
            p.id: p
            for p in await self._products.list_by_ids(
                [ing.product_id for ing in meal.ingredients]
            )
        }
        required: dict[uuid.UUID, Decimal] = {}
        for ing in meal.ingredients:
            required[ing.product_id] = (
                Decimal(str(ing.quantity_per_serving)) * data.servings_count
            )
        for product_id, needed in required.items():
            available = await self._stock.current_stock(product_id)
            if available < needed:
                name = products_by_id[product_id].name
                raise ConflictError(
                    f"Omborda yetarli '{name}' yo'q: kerak {needed}, mavjud {available}."
                )

        log = MealLog(
            branch_id=meal.branch_id,
            meal_id=meal.id,
            serving_date=data.serving_date,
            servings_count=data.servings_count,
            recorded_by=current_user.id,
        )
        self._logs.add(log)
        await self._session.flush()

        occurred_at = _day_start(data.serving_date)
        for product_id, needed in required.items():
            self._stock.add(
                FoodStockMovement(
                    branch_id=meal.branch_id,
                    product_id=product_id,
                    movement_type=StockMovementType.OUT.value,
                    quantity=needed,
                    reason="CONSUMPTION",
                    meal_log_id=log.id,
                    recorded_by=current_user.id,
                    occurred_at=occurred_at,
                )
            )
        await self._session.flush()

        self._audit.record(
            action="MEAL_LOGGED",
            entity_type="meal_log",
            entity_id=log.id,
            actor_user_id=current_user.id,
            branch_id=meal.branch_id,
            after_data={"meal": meal.name, "servings": data.servings_count},
        )
        return log


class FoodReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._products = FoodProductRepository(session)
        self._stock = StockMovementRepository(session)
        self._access = AccessService(session)

    async def stock_report(
        self,
        branch_id: uuid.UUID,
        period_start: date,
        period_end: date,
        current_user: CurrentUser,
    ) -> StockReportResponse:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filial hisobotiga kirish huquqi yo'q.")

        products = await self._products.list_by_branch(branch_id)
        start_dt = _day_start(period_start)
        end_dt = _day_start(period_end) + timedelta(days=1)

        rows: list[StockReportRow] = []
        total_value = ZERO
        for product in products:
            opening = await self._stock.net_before(product.id, start_dt)
            stock_in = await self._stock.sum_in_period(
                product.id, StockMovementType.IN.value, start_dt, end_dt
            )
            stock_out = await self._stock.sum_in_period(
                product.id, StockMovementType.OUT.value, start_dt, end_dt
            )
            closing = opening + stock_in - stock_out
            unit_cost = product.unit_cost or ZERO
            value = closing * unit_cost
            total_value += value
            rows.append(
                StockReportRow(
                    product_id=product.id,
                    product_name=product.name,
                    unit=product.unit,
                    opening_stock=opening,
                    stock_in=stock_in,
                    stock_out=stock_out,
                    closing_stock=closing,
                    unit_cost=product.unit_cost,
                    closing_value=value,
                )
            )

        return StockReportResponse(
            branch_id=branch_id,
            period_start=period_start,
            period_end=period_end,
            rows=rows,
            total_value=total_value,
        )
