"""Oziq-ovqat va oshxona ombori integratsiya testlari."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


async def _owner(client: AsyncClient) -> tuple[str, str]:
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    return owner, setup["branch_id"]


async def _create_product(
    client: AsyncClient, owner: str, branch_id: str, name: str = "Guruch"
) -> str:
    resp = await client.post(
        "/api/v1/food/products",
        headers=auth_header(owner),
        json={"branch_id": branch_id, "name": name, "unit": "kg", "unit_cost": "15000"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_product_starts_with_zero_stock(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    await _create_product(client, owner, branch_id)

    resp = await client.get(
        "/api/v1/food/products",
        headers=auth_header(owner),
        params={"branch_id": branch_id},
    )
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) == 1
    assert Decimal(products[0]["current_stock"]) == Decimal("0")


async def test_stock_in_increases_balance(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    product_id = await _create_product(client, owner, branch_id)

    resp = await client.post(
        "/api/v1/food/stock-movements",
        headers=auth_header(owner),
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": "50",
            "reason": "PURCHASE",
        },
    )
    assert resp.status_code == 201, resp.text

    products = (
        await client.get(
            "/api/v1/food/products",
            headers=auth_header(owner),
            params={"branch_id": branch_id},
        )
    ).json()
    assert Decimal(products[0]["current_stock"]) == Decimal("50")


async def test_stock_out_without_sufficient_balance_fails(
    client: AsyncClient,
) -> None:
    owner, branch_id = await _owner(client)
    product_id = await _create_product(client, owner, branch_id)

    resp = await client.post(
        "/api/v1/food/stock-movements",
        headers=auth_header(owner),
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": "5",
            "reason": "WASTE",
        },
    )
    assert resp.status_code == 409


async def test_meal_log_consumes_ingredients(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    rice_id = await _create_product(client, owner, branch_id, "Guruch")
    oil_id = await _create_product(client, owner, branch_id, "Yog'")

    for product_id, qty in ((rice_id, "20"), (oil_id, "5")):
        await client.post(
            "/api/v1/food/stock-movements",
            headers=auth_header(owner),
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": qty,
                "reason": "PURCHASE",
            },
        )

    meal_resp = await client.post(
        "/api/v1/food/meals",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "name": "Osh",
            "ingredients": [
                {"product_id": rice_id, "quantity_per_serving": "0.2"},
                {"product_id": oil_id, "quantity_per_serving": "0.05"},
            ],
        },
    )
    assert meal_resp.status_code == 201, meal_resp.text
    meal_id = meal_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/food/meal-logs",
        headers=auth_header(owner),
        json={"meal_id": meal_id, "serving_date": "2026-09-02", "servings_count": 10},
    )
    assert log_resp.status_code == 201, log_resp.text

    products = {
        p["id"]: p
        for p in (
            await client.get(
                "/api/v1/food/products",
                headers=auth_header(owner),
                params={"branch_id": branch_id},
            )
        ).json()
    }
    # 20 - (0.2 * 10) = 18; 5 - (0.05 * 10) = 4.5
    assert Decimal(products[rice_id]["current_stock"]) == Decimal("18.000")
    assert Decimal(products[oil_id]["current_stock"]) == Decimal("4.500")


async def test_meal_log_insufficient_stock_aborts_transaction(
    client: AsyncClient,
) -> None:
    owner, branch_id = await _owner(client)
    rice_id = await _create_product(client, owner, branch_id, "Guruch")
    oil_id = await _create_product(client, owner, branch_id, "Yog'")

    # Faqat guruchdan yetarli, yog'dan yetarli emas.
    await client.post(
        "/api/v1/food/stock-movements",
        headers=auth_header(owner),
        json={
            "product_id": rice_id,
            "movement_type": "IN",
            "quantity": "100",
            "reason": "PURCHASE",
        },
    )

    meal_resp = await client.post(
        "/api/v1/food/meals",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "name": "Osh",
            "ingredients": [
                {"product_id": rice_id, "quantity_per_serving": "0.2"},
                {"product_id": oil_id, "quantity_per_serving": "0.05"},
            ],
        },
    )
    meal_id = meal_resp.json()["id"]

    log_resp = await client.post(
        "/api/v1/food/meal-logs",
        headers=auth_header(owner),
        json={"meal_id": meal_id, "serving_date": "2026-09-02", "servings_count": 10},
    )
    assert log_resp.status_code == 409

    # Guruch sarflanib qolmasligi kerak — butun amal bekor bo'ldi (atomiklik).
    products = {
        p["id"]: p
        for p in (
            await client.get(
                "/api/v1/food/products",
                headers=auth_header(owner),
                params={"branch_id": branch_id},
            )
        ).json()
    }
    assert Decimal(products[rice_id]["current_stock"]) == Decimal("100")


async def test_stock_report_computes_opening_and_closing(
    client: AsyncClient,
) -> None:
    owner, branch_id = await _owner(client)
    product_id = await _create_product(client, owner, branch_id)

    await client.post(
        "/api/v1/food/stock-movements",
        headers=auth_header(owner),
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": "30",
            "reason": "PURCHASE",
            "occurred_at": "2026-09-01T08:00:00Z",
        },
    )
    await client.post(
        "/api/v1/food/stock-movements",
        headers=auth_header(owner),
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": "10",
            "reason": "WASTE",
            "occurred_at": "2026-09-05T08:00:00Z",
        },
    )

    resp = await client.get(
        "/api/v1/food/stock-report",
        headers=auth_header(owner),
        params={
            "branch_id": branch_id,
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
        },
    )
    assert resp.status_code == 200
    row = resp.json()["rows"][0]
    assert Decimal(row["opening_stock"]) == Decimal("0")
    assert Decimal(row["stock_in"]) == Decimal("30")
    assert Decimal(row["stock_out"]) == Decimal("10")
    assert Decimal(row["closing_stock"]) == Decimal("20")
    assert Decimal(row["closing_value"]) == Decimal("300000.000")


async def test_manager_cannot_access_food_of_other_branch(
    client: AsyncClient,
) -> None:
    owner, branch_a = await _owner(client)
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Filial B"},
        )
    ).json()["id"]
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Menejer B",
            "username": "menejer.b",
            "phone": "+998900000040",
            "password": "parol12345",
            "role": "MANAGER",
            "branch_id": branch_b,
        },
    )
    manager_b = (await login(client, "+998900000040", "parol12345"))["access_token"]

    resp = await client.post(
        "/api/v1/food/products",
        headers=auth_header(manager_b),
        json={"branch_id": branch_a, "name": "Non", "unit": "dona"},
    )
    assert resp.status_code == 403
