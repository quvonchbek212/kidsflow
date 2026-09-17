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


async def test_payroll_summary_scoped_to_manager_branch(client: AsyncClient) -> None:
    """Menejer ish haqi fondini ko'radi — lekin faqat o'z filiali bo'yicha.

    Ish haqini hisoblash (`/payroll/runs`) menejerga ochiq, shuning uchun fond
    raqami ham unga ko'rinishi kerak; aks holda u nima to'layotganini bilmay
    turib to'lardi. Chegara — boshqa filialning xodimlari va bog'cha egasi
    (u yollanma xodim emas) bu raqamga kirmaydi.
    """
    owner, branch_a = await _owner(client)
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Ikkinchi filial", "capacity": 20},
        )
    ).json()["id"]

    for phone, username, name, branch, salary in (
        ("+998900000015", "u998900000015", "Menejer B", branch_a, "3000000.00"),
        ("+998900000016", "u998900000016", "Begona xodim", branch_b, "9000000.00"),
    ):
        created = await client.post(
            "/api/v1/users",
            headers=auth_header(owner),
            json={
                "full_name": name,
                "username": username,
                "phone": phone,
                "password": "parol12345",
                "role": "MANAGER" if branch == branch_a else "TEACHER",
                "branch_id": branch,
                "monthly_salary": salary,
            },
        )
        assert created.status_code == 201, created.text

    manager = (await login(client, "+998900000015", "parol12345"))["access_token"]

    resp = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(manager)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Faqat o'z filialidagi menejerning o'zi — begona filial xodimi yo'q.
    assert [row["full_name"] for row in body["staff"]] == ["Menejer B"]
    assert Decimal(body["total_fund"]) == Decimal("3000000.00")

    # Begona filialni ochiq so'rasa ham rad etiladi.
    foreign = await client.get(
        f"/api/v1/users/payroll-summary?branch_id={branch_b}",
        headers=auth_header(manager),
    )
    assert foreign.status_code == 403


async def test_payroll_summary_denied_for_teacher(client: AsyncClient) -> None:
    """Tarbiyachi ish haqi fondiga umuman kira olmaydi."""
    owner, branch_id = await _owner(client)
    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Tarbiyachi",
            "username": "u998900000017",
            "phone": "+998900000017",
            "password": "parol12345",
            "role": "TEACHER",
            "branch_id": branch_id,
        },
    )
    teacher = (await login(client, "+998900000017", "parol12345"))["access_token"]

    resp = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(teacher)
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


async def test_owner_excluded_from_staff_list_and_payroll(
    client: AsyncClient,
) -> None:
    """Bog'cha egasi yollanma xodim emas — ro'yxatda ham, fondda ham chiqmaydi.

    Ilgari OWNER xodimlar ro'yxatiga tushib qolardi (faqat PARENT chiqarib
    tashlanardi) va lavozimi sifatida tasodifiy qiymat ko'rinardi. Bundan ham
    yomoni: unga maosh qo'yilsa, `total_fund` uni qo'shib hisoblardi, jadvalda
    esa qator ko'rinmasdi — yuqoridagi raqam qatorlar yig'indisiga mos kelmasdi.
    """
    owner, branch_id = await _owner(client)

    me = await client.get("/api/v1/auth/me", headers=auth_header(owner))
    owner_id = me.json()["id"]

    # Egaga maosh belgilaymiz — aynan shu holat nomuvofiqlikni keltirib chiqargan.
    await client.patch(
        f"/api/v1/users/{owner_id}/salary",
        headers=auth_header(owner),
        json={"monthly_salary": "20000000"},
    )

    await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Oshpaz S",
            "username": "u998900000031",
            "phone": "+998900000031",
            "password": "parol12345",
            "role": "TEACHER",
            "position": "COOK",
            "branch_id": branch_id,
            "monthly_salary": "4000000",
        },
    )

    staff = await client.get("/api/v1/users", headers=auth_header(owner))
    assert staff.status_code == 200
    names = [u["full_name"] for u in staff.json()]
    assert names == ["Oshpaz S"], names

    summary = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(owner)
    )
    body = summary.json()
    # Fond faqat yollanma xodimlar bo'yicha — eganing 20 mln'i kirmaydi.
    assert Decimal(body["total_fund"]) == Decimal("4000000.00")
    # Va fond jadvaldagi qatorlar yig'indisiga aynan teng.
    assert Decimal(body["total_fund"]) == sum(
        Decimal(r["monthly_salary"]) for r in body["staff"]
    )
