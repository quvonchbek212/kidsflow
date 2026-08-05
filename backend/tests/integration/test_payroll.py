"""Kadrlar/Ish haqi fondi integratsiya testlari."""

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


async def test_create_staff_with_position_and_salary(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)

    resp = await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Osh Pazov",
            "username": "u998900000010",
            "phone": "+998900000010",
            "password": "parol12345",
            "role": "TEACHER",
            "position": "COOK",
            "branch_id": branch_id,
            "monthly_salary": "2500000",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["position"] == "COOK"
    assert Decimal(body["monthly_salary"]) == Decimal("2500000.00")


async def test_position_defaults_to_role_when_omitted(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)

    resp = await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Tarbiya Chi",
            "username": "u998900000011",
            "phone": "+998900000011",
            "password": "parol12345",
            "role": "TEACHER",
            "branch_id": branch_id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["position"] == "TEACHER"


async def test_list_staff_filtered_by_position(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Farrosh Bek",
            "username": "u998900000012",
            "phone": "+998900000012",
            "password": "parol12345",
            "role": "TEACHER",
            "position": "CLEANER",
            "branch_id": branch_id,
        },
    )
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Tarbiyachi Ona",
            "username": "u998900000013",
            "phone": "+998900000013",
            "password": "parol12345",
            "role": "TEACHER",
            "position": "TEACHER",
            "branch_id": branch_id,
        },
    )

    resp = await client.get(
        "/api/v1/users", headers=auth_header(owner), params={"position": "CLEANER"}
    )
    assert resp.status_code == 200
    names = [u["full_name"] for u in resp.json()]
    assert names == ["Farrosh Bek"]


async def test_update_salary_and_payroll_summary(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    staff_resp = await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Menejer A",
            "username": "u998900000014",
            "phone": "+998900000014",
            "password": "parol12345",
            "role": "MANAGER",
            "position": "MANAGER",
            "branch_id": branch_id,
            "monthly_salary": "4000000",
        },
    )
    staff_id = staff_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/users/{staff_id}/salary",
        headers=auth_header(owner),
        json={"monthly_salary": "4500000"},
    )
    assert patch_resp.status_code == 200
    assert Decimal(patch_resp.json()["monthly_salary"]) == Decimal("4500000.00")

    summary = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(owner)
    )
    assert summary.status_code == 200
    body = summary.json()
    assert Decimal(body["total_fund"]) == Decimal("4500000.00")
    assert len(body["staff"]) == 1
    assert body["staff"][0]["position"] == "MANAGER"


async def test_payroll_summary_requires_owner(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Menejer B",
            "username": "u998900000015",
            "phone": "+998900000015",
            "password": "parol12345",
            "role": "MANAGER",
            "branch_id": branch_id,
        },
    )
    manager = (await login(client, "+998900000015", "parol12345"))["access_token"]

    resp = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(manager)
    )
    assert resp.status_code == 403


async def test_staff_list_excludes_guardians(client: AsyncClient) -> None:
    """Vasiylar (PARENT) "Xodimlar" ro'yxatida ko'rinmasligi kerak.

    Aks holda ularga oylik hisoblash kabi xodimga xos amallar taklif qilinadi.
    """
    owner, branch_id = await _owner(client)
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Tarbiyachi Xodim",
            "username": "u998900000021",
            "phone": "+998900000021",
            "password": "parol12345",
            "role": "TEACHER",
            "position": "TEACHER",
            "branch_id": branch_id,
            "monthly_salary": "3000000",
        },
    )

    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Bola Test", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/guardians",
        headers=auth_header(owner),
        json={
            "full_name": "Vasiy Test",
            "phone": "+998900000022",
            "relationship_type": "MOTHER",
        },
    )

    staff = (await client.get("/api/v1/users", headers=auth_header(owner))).json()
    names = {u["full_name"] for u in staff}
    assert "Tarbiyachi Xodim" in names
    assert "Vasiy Test" not in names

    # Vasiy o'z bo'limida esa ko'rinadi.
    parents = (
        await client.get("/api/v1/children/parents", headers=auth_header(owner))
    ).json()
    assert {p["full_name"] for p in parents} == {"Vasiy Test"}

    # Ish haqi fondi ham faqat xodimlar bo'yicha.
    summary = (
        await client.get("/api/v1/users/payroll-summary", headers=auth_header(owner))
    ).json()
    assert Decimal(summary["total_fund"]) == Decimal("3000000.00")
    assert {s["full_name"] for s in summary["staff"]} == {"Tarbiyachi Xodim"}
