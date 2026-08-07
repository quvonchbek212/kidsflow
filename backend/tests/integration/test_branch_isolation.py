"""Filial izolyatsiyasi: ro'yxat endpointlarining `branch_id` kesimi.

Ma'lumotlar bazada `branch_id` orqali ajratilgan (2.1-bo'lim), lekin ro'yxat
endpointlari uzoq vaqt faqat *rol* bo'yicha cheklanardi — OWNER uchun bu
"barcha filiallar" degani edi. Natijada web panelda filial almashtirilganda
ekranning bir qismi o'zgarmasdi, moliyaviy raqamlar esa ikkala filialning
yig'indisi bo'lib ko'rinardi.

Bu yerda tekshiriladi:
- `branch_id` berilganda faqat shu filial ma'lumoti qaytadi;
- `branch_id` berilmaganda eski xulq saqlanadi (orqaga moslik);
- begona filial so'ralganda 403.

Eslatma: bola `children` jadvalida filialga bog'lanmagan (5.3-bo'lim), u
filialga enrollment orqali tegishli — shu sabab bolalar filtri enrollment
aloqasi bo'yicha ishlaydi.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"
MANAGER_A_PHONE = "+998907654321"
MANAGER_A_PASSWORD = "manager-a-parol-123"


def _dec(value: object) -> Decimal:
    return Decimal(str(value))


async def _two_branch_world(client: AsyncClient) -> dict:
    """Ikkita filial, har birida guruh, bola (ACTIVE enrollment) va xarajat."""
    setup = await complete_setup(client)
    branch_a = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]

    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Ikkinchi filial", "capacity": 40},
        )
    ).json()["id"]

    category_id = (
        await client.get("/api/v1/expense-categories", headers=auth_header(owner))
    ).json()[0]["id"]

    world: dict = {"owner": owner, "branch_a": branch_a, "branch_b": branch_b}

    for key, branch_id, group_name, child_name, amount in (
        ("a", branch_a, "A-guruh", "Ali Valiyev", 100000),
        ("b", branch_b, "B-guruh", "Bobur Karimov", 700000),
    ):
        group_id = (
            await client.post(
                "/api/v1/groups",
                headers=auth_header(owner),
                json={"branch_id": branch_id, "name": group_name, "capacity": 15},
            )
        ).json()["id"]

        child_id = (
            await client.post(
                "/api/v1/children",
                headers=auth_header(owner),
                json={"full_name": child_name, "birth_date": "2021-05-10"},
            )
        ).json()["id"]

        enroll = await client.post(
            f"/api/v1/children/{child_id}/enrollments",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "group_id": group_id,
                "start_date": "2026-09-01",
                "status": "ACTIVE",
            },
        )
        assert enroll.status_code == 201, enroll.text

        guardian = await client.post(
            f"/api/v1/children/{child_id}/guardians",
            headers=auth_header(owner),
            json={
                "full_name": f"{child_name} otasi",
                "phone": f"+99890111{'1' if key == 'a' else '2'}000",
                "relationship_type": "FATHER",
                "is_primary": True,
            },
        )
        assert guardian.status_code == 201, guardian.text

        expense = await client.post(
            "/api/v1/expenses",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "category_id": category_id,
                "amount": amount,
                "expense_date": "2026-09-03",
            },
        )
        assert expense.status_code == 201, expense.text

        world[f"group_{key}"] = group_id
        world[f"child_{key}"] = child_id
        world[f"expense_{key}"] = amount

    return world


# --- Guruhlar ---


async def test_groups_filtered_by_branch(client: AsyncClient) -> None:
    w = await _two_branch_world(client)

    only_a = await client.get(
        "/api/v1/groups",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_a"]},
    )
    assert only_a.status_code == 200, only_a.text
    assert [g["id"] for g in only_a.json()] == [w["group_a"]]

    only_b = await client.get(
        "/api/v1/groups",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_b"]},
    )
    assert [g["id"] for g in only_b.json()] == [w["group_b"]]


async def test_groups_without_branch_returns_all(client: AsyncClient) -> None:
    """Orqaga moslik: parametrsiz chaqiruv eski xulqni saqlaydi."""
    w = await _two_branch_world(client)

    resp = await client.get("/api/v1/groups", headers=auth_header(w["owner"]))
    assert {g["id"] for g in resp.json()} == {w["group_a"], w["group_b"]}


# --- Bolalar ---


async def test_children_filtered_by_branch_via_enrollment(
    client: AsyncClient,
) -> None:
    w = await _two_branch_world(client)

    only_a = await client.get(
        "/api/v1/children",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_a"]},
    )
    assert only_a.status_code == 200, only_a.text
    assert [c["id"] for c in only_a.json()] == [w["child_a"]]

    only_b = await client.get(
        "/api/v1/children",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_b"]},
    )
    assert [c["id"] for c in only_b.json()] == [w["child_b"]]


async def test_children_without_branch_returns_all(client: AsyncClient) -> None:
    w = await _two_branch_world(client)

    resp = await client.get("/api/v1/children", headers=auth_header(w["owner"]))
    assert {c["id"] for c in resp.json()} == {w["child_a"], w["child_b"]}


# --- Ota-onalar ---


async def test_parents_filtered_by_branch(client: AsyncClient) -> None:
    w = await _two_branch_world(client)

    resp = await client.get(
        "/api/v1/children/parents",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_a"]},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert [r["full_name"] for r in rows] == ["Ali Valiyev otasi"]
    # Farzandlar ro'yxati ham filial bilan cheklanadi.
    assert rows[0]["children_names"] == ["Ali Valiyev"]


# --- Xodimlar ---


async def test_staff_filtered_by_branch(client: AsyncClient) -> None:
    w = await _two_branch_world(client)

    await create_staff(
        client,
        w["owner"],
        role="MANAGER",
        phone=MANAGER_A_PHONE,
        password=MANAGER_A_PASSWORD,
        full_name="A menejeri",
        branch_id=w["branch_a"],
    )
    await create_staff(
        client,
        w["owner"],
        role="TEACHER",
        phone="+998931112299",
        password="teacher-parol-123",
        full_name="B tarbiyachisi",
        branch_id=w["branch_b"],
    )

    only_a = await client.get(
        "/api/v1/users",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_a"]},
    )
    assert only_a.status_code == 200, only_a.text
    assert [u["full_name"] for u in only_a.json()] == ["A menejeri"]

    only_b = await client.get(
        "/api/v1/users",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_b"]},
    )
    assert [u["full_name"] for u in only_b.json()] == ["B tarbiyachisi"]


async def test_payroll_fund_matches_branch_staff(client: AsyncClient) -> None:
    """Fond raqami xodimlar jadvali bilan bir xil kesimda bo'lishi shart.

    `list_staff` hujjatida "jadvaldagi qatorlar yig'indisi doim fond raqamiga
    teng" deb yozilgan — xodimlar filialga bo'linib, fond bo'linmay qolsa shu
    kafolat buzilardi.
    """
    w = await _two_branch_world(client)

    staff_a = await create_staff(
        client,
        w["owner"],
        role="MANAGER",
        phone=MANAGER_A_PHONE,
        password=MANAGER_A_PASSWORD,
        full_name="A menejeri",
        branch_id=w["branch_a"],
    )
    staff_b = await create_staff(
        client,
        w["owner"],
        role="TEACHER",
        phone="+998931112299",
        password="teacher-parol-123",
        full_name="B tarbiyachisi",
        branch_id=w["branch_b"],
    )
    for user_id, salary in ((staff_a, "5000000"), (staff_b, "3000000")):
        resp = await client.patch(
            f"/api/v1/users/{user_id}/salary",
            headers=auth_header(w["owner"]),
            json={"monthly_salary": salary},
        )
        assert resp.status_code == 200, resp.text

    fund_a = await client.get(
        "/api/v1/users/payroll-summary",
        headers=auth_header(w["owner"]),
        params={"branch_id": w["branch_a"]},
    )
    assert fund_a.status_code == 200, fund_a.text
    body_a = fund_a.json()
    assert _dec(body_a["total_fund"]) == _dec("5000000")
    assert [s["full_name"] for s in body_a["staff"]] == ["A menejeri"]

    both = await client.get(
        "/api/v1/users/payroll-summary", headers=auth_header(w["owner"])
    )
    assert _dec(both.json()["total_fund"]) == _dec("8000000")


# --- Moliyaviy dashboard ---


async def test_dashboard_totals_are_per_branch(client: AsyncClient) -> None:
    """Eng muhim tekshiruv: raqamlar ikki filialdan qo'shilib ketmasin."""
    w = await _two_branch_world(client)
    params = {"period_start": "2026-09-01", "period_end": "2026-09-30"}

    both = await client.get(
        "/api/v1/analytics/dashboard", headers=auth_header(w["owner"]), params=params
    )
    assert both.status_code == 200, both.text
    assert _dec(both.json()["expenses"]) == _dec(w["expense_a"] + w["expense_b"])

    only_a = await client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_header(w["owner"]),
        params={**params, "branch_id": w["branch_a"]},
    )
    body_a = only_a.json()
    assert _dec(body_a["expenses"]) == _dec(w["expense_a"])
    assert [b["branch_id"] for b in body_a["branches"]] == [w["branch_a"]]

    only_b = await client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_header(w["owner"]),
        params={**params, "branch_id": w["branch_b"]},
    )
    assert _dec(only_b.json()["expenses"]) == _dec(w["expense_b"])


# --- Huquq tekshiruvi ---


async def test_manager_cannot_read_foreign_branch(client: AsyncClient) -> None:
    """A filialining menejeri B filialini so'ray olmaydi."""
    w = await _two_branch_world(client)
    await create_staff(
        client,
        w["owner"],
        role="MANAGER",
        phone=MANAGER_A_PHONE,
        password=MANAGER_A_PASSWORD,
        branch_id=w["branch_a"],
    )
    manager = (await login(client, MANAGER_A_PHONE, MANAGER_A_PASSWORD))[
        "access_token"
    ]

    for path, params in (
        ("/api/v1/groups", {"branch_id": w["branch_b"]}),
        ("/api/v1/children", {"branch_id": w["branch_b"]}),
        ("/api/v1/children/parents", {"branch_id": w["branch_b"]}),
        (
            "/api/v1/analytics/dashboard",
            {
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "branch_id": w["branch_b"],
            },
        ),
    ):
        resp = await client.get(path, headers=auth_header(manager), params=params)
        assert resp.status_code == 403, f"{path}: {resp.status_code} {resp.text}"

    # O'z filialini esa muammosiz o'qiydi.
    own = await client.get(
        "/api/v1/groups",
        headers=auth_header(manager),
        params={"branch_id": w["branch_a"]},
    )
    assert own.status_code == 200
    assert [g["id"] for g in own.json()] == [w["group_a"]]
