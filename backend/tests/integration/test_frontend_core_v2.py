"""7-bosqich A: yangi frontend uchun asosiy qism integratsiya testlari.

Guruh tarifi/xonasi, xodim profili, bola holati proyeksiyasi, guruh
o'zgartirish (transfer), doimiy chegirma, xarajat kategoriyasi CRUD +
is_recurring, davomat bulk-mark/trend, va analytics kengaytmasi (aging,
revenue-by-group, expenses-by-category, break-even).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


def _dec(value: object) -> Decimal:
    return Decimal(str(value))


async def _owner(client: AsyncClient) -> tuple[str, str]:
    setup = await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    return owner, setup["branch_id"]


# --- Guruh: tarif + xona ---


async def test_group_monthly_fee_and_room_number(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)

    resp = await client.post(
        "/api/v1/groups",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "name": "Kapalaklar",
            "capacity": 18,
            "monthly_fee": "1600000",
            "room_number": "2",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert _dec(body["monthly_fee"]) == _dec("1600000")
    assert body["room_number"] == "2"

    patch = await client.patch(
        f"/api/v1/groups/{body['id']}",
        headers=auth_header(owner),
        json={"monthly_fee": "1700000"},
    )
    assert patch.status_code == 200
    assert _dec(patch.json()["monthly_fee"]) == _dec("1700000")


# --- Xodim profili ---


async def test_staff_profile_update(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    staff = (
        await client.post(
            "/api/v1/users",
            headers=auth_header(owner),
            json={
                "full_name": "Zebo Tursunova",
                "username": "u998900000020",
                "phone": "+998900000020",
                "password": "parol12345",
                "role": "TEACHER",
                "position": "NURSE",
                "branch_id": branch_id,
            },
        )
    ).json()
    assert staff["position"] == "NURSE"

    patch = await client.patch(
        f"/api/v1/users/{staff['id']}",
        headers=auth_header(owner),
        json={
            "birth_date": "1990-05-01",
            "passport_number": "AA1234567",
            "hire_date": "2022-11-01",
            "employment_type": "FULL_TIME",
        },
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["birth_date"] == "1990-05-01"
    assert body["passport_number"] == "AA1234567"
    assert body["hire_date"] == "2022-11-01"
    assert body["employment_type"] == "FULL_TIME"


async def test_manager_updates_staff_in_own_branch(client: AsyncClient) -> None:
    """MANAGER o'z filialidagi xodim profilini tahrirlaydi.

    Menejer filialning kundalik ishini olib boradi, shuning uchun xodim
    ma'lumotini ham o'zi yangilaydi. Chegara — filial: begona filialdagi
    xodimga va bog'cha egasining hisobiga tegib bo'lmaydi (quyidagi testlar).
    """
    owner, branch_id = await _owner(client)
    staff_id = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000021",
        password="parol12345",
        branch_id=branch_id,
    )
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000022",
        password="parol12345",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000022", "parol12345"))["access_token"]

    resp = await client.patch(
        f"/api/v1/users/{staff_id}",
        headers=auth_header(manager),
        json={"employment_type": "PART_TIME"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["employment_type"] == "PART_TIME"


async def test_manager_cannot_touch_other_branch_staff(client: AsyncClient) -> None:
    """Menejer boshqa filial xodimini tahrirlay olmaydi."""
    owner, branch_a = await _owner(client)
    branch_b = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Ikkinchi filial", "capacity": 20},
        )
    ).json()["id"]

    foreign_staff = await create_staff(
        client,
        owner,
        role="TEACHER",
        phone="+998900000023",
        password="parol12345",
        branch_id=branch_b,
    )
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000024",
        password="parol12345",
        branch_id=branch_a,
    )
    manager = (await login(client, "+998900000024", "parol12345"))["access_token"]

    resp = await client.patch(
        f"/api/v1/users/{foreign_staff}",
        headers=auth_header(manager),
        json={"employment_type": "PART_TIME"},
    )
    assert resp.status_code == 403

    # Ro'yxat ham o'z filiali bilan cheklanadi.
    listed = await client.get("/api/v1/users", headers=auth_header(manager))
    assert listed.status_code == 200
    assert foreign_staff not in [u["id"] for u in listed.json()]


async def test_staff_created_without_phone_or_email(client: AsyncClient) -> None:
    """Xodim faqat login va parol bilan yaratiladi.

    Ilgari "telefon yoki email majburiy" qoidasi bor edi — o'shanda kirish
    aynan shular orqali bo'lardi. Endi login `username`, shuning uchun aloqa
    ma'lumotisiz ham hisob ochiladi va u ishlaydi.
    """
    owner, branch_id = await _owner(client)

    created = await client.post(
        "/api/v1/users",
        headers=auth_header(owner),
        json={
            "full_name": "Aloqasiz Tarbiyachi",
            "username": "aloqasiz",
            "password": "parol12345",
            "role": "TEACHER",
            "branch_id": branch_id,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["phone"] is None
    assert body["email"] is None

    # Va shu hisob bilan kirib bo'ladi.
    signed_in = await client.post(
        "/api/v1/auth/login",
        json={"login": "aloqasiz", "password": "parol12345"},
    )
    assert signed_in.status_code == 200, signed_in.text


async def test_manager_cannot_create_owner(client: AsyncClient) -> None:
    """Menejer o'ziga yoki boshqasiga OWNER rolini bera olmaydi.

    Aks holda filial cheklovidan chiqib ketish yo'li ochilardi.
    """
    owner, branch_id = await _owner(client)
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000025",
        password="parol12345",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000025", "parol12345"))["access_token"]

    resp = await client.post(
        "/api/v1/users",
        headers=auth_header(manager),
        json={
            "full_name": "Yangi egasi",
            "username": "yangi_egasi",
            "phone": "+998900000026",
            "password": "parol12345",
            "role": "OWNER",
        },
    )
    assert resp.status_code == 403

    # O'z filialiga tarbiyachi qo'shish esa ishlaydi.
    ok = await client.post(
        "/api/v1/users",
        headers=auth_header(manager),
        json={
            "full_name": "Yangi tarbiyachi",
            "username": "yangi_tarbiyachi",
            "phone": "+998900000027",
            "password": "parol12345",
            "role": "TEACHER",
            "branch_id": branch_id,
        },
    )
    assert ok.status_code == 201, ok.text


# --- Bola holati proyeksiyasi + guruh o'zgartirish (transfer) ---


async def _create_group(
    client: AsyncClient, owner: str, branch_id: str, name: str
) -> str:
    resp = await client.post(
        "/api/v1/groups",
        headers=auth_header(owner),
        json={"branch_id": branch_id, "name": name, "capacity": 10},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_child_status_projection(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Loyiq Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]

    # Enrollment yo'q — "left".
    detail = await client.get(
        f"/api/v1/children/{child_id}", headers=auth_header(owner)
    )
    assert detail.json()["status"] == "left"

    group_id = await _create_group(client, owner, branch_id, "Guruh Kutish")
    enroll = (
        await client.post(
            f"/api/v1/children/{child_id}/enrollments",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "group_id": group_id,
                "start_date": "2026-09-01",
                "status": "PLANNED",
            },
        )
    ).json()

    detail = await client.get(
        f"/api/v1/children/{child_id}", headers=auth_header(owner)
    )
    assert detail.json()["status"] == "waiting"

    await client.patch(
        f"/api/v1/enrollments/{enroll['id']}",
        headers=auth_header(owner),
        json={"status": "ACTIVE"},
    )
    detail = await client.get(
        f"/api/v1/children/{child_id}", headers=auth_header(owner)
    )
    assert detail.json()["status"] == "active"


async def test_child_transfer_between_groups(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "O'tkaziladigan Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_a = await _create_group(client, owner, branch_id, "Guruh A")
    group_b = await _create_group(client, owner, branch_id, "Guruh B")

    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_a,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
            "discount_type": "SIBLING",
            "discount_percent": "10",
        },
    )

    transfer = await client.post(
        f"/api/v1/children/{child_id}/transfer",
        headers=auth_header(owner),
        json={
            "new_group_id": group_b,
            "effective_date": "2026-10-01",
            "reason": "Yosh guruhi o'zgardi",
        },
    )
    assert transfer.status_code == 201, transfer.text
    new_enrollment = transfer.json()
    assert new_enrollment["group_id"] == group_b
    assert new_enrollment["status"] == "ACTIVE"
    # Chegirma eski enrollment'dan meros olingan.
    assert new_enrollment["discount_type"] == "SIBLING"
    assert _dec(new_enrollment["discount_percent"]) == _dec("10")

    # Faqat bitta faol enrollment qoladi (eskisi COMPLETED bo'lgan).
    second_transfer_attempt = await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_a,
            "start_date": "2026-11-01",
            "status": "ACTIVE",
        },
    )
    assert second_transfer_attempt.status_code == 409


async def test_standing_discount_applied_on_invoice_generation(
    client: AsyncClient,
) -> None:
    owner, branch_id = await _owner(client)
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Chegirmali Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    group_id = await _create_group(client, owner, branch_id, "Chegirma Guruhi")
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
            "discount_type": "SIBLING",
            "discount_percent": "10",
        },
    )
    fee = await client.patch(
        f"/api/v1/groups/{group_id}",
        headers=auth_header(owner),
        json={"monthly_fee": 1000000},
    )
    assert fee.status_code == 200, fee.text

    gen = await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "billing_period": "2026-09-15",
        },
    )
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] == 1

    invoices = (
        await client.get(
            f"/api/v1/children/{child_id}/invoices", headers=auth_header(owner)
        )
    ).json()
    assert len(invoices) == 1
    invoice = invoices[0]
    assert _dec(invoice["original_amount"]) == _dec("1000000")
    assert _dec(invoice["discount_amount"]) == _dec("100000")
    assert _dec(invoice["adjusted_amount"]) == _dec("900000")
    assert _dec(invoice["outstanding_amount"]) == _dec("900000")


# --- Xarajat kategoriyasi CRUD + is_recurring ---


async def test_expense_category_seed_has_split_equipment_and_repairs(
    client: AsyncClient,
) -> None:
    owner, _branch = await _owner(client)
    resp = await client.get("/api/v1/expense-categories", headers=auth_header(owner))
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert "Jihoz" in names
    assert "Ta'mirlash" in names
    variable_flags = {c["name"]: c["is_variable"] for c in resp.json()}
    assert variable_flags["Oziq-ovqat"] is True
    assert variable_flags["Ijara"] is False


async def test_expense_category_create_and_update(client: AsyncClient) -> None:
    owner, _branch = await _owner(client)
    create = await client.post(
        "/api/v1/expense-categories",
        headers=auth_header(owner),
        json={"name": "Marketing", "is_variable": False},
    )
    assert create.status_code == 201, create.text
    category_id = create.json()["id"]

    update = await client.patch(
        f"/api/v1/expense-categories/{category_id}",
        headers=auth_header(owner),
        json={"is_variable": True},
    )
    assert update.status_code == 200
    assert update.json()["is_variable"] is True

    duplicate = await client.post(
        "/api/v1/expense-categories",
        headers=auth_header(owner),
        json={"name": "Marketing"},
    )
    assert duplicate.status_code == 409


async def test_expense_is_recurring_flag(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    category_id = (
        await client.get("/api/v1/expense-categories", headers=auth_header(owner))
    ).json()[0]["id"]

    resp = await client.post(
        "/api/v1/expenses",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "category_id": category_id,
            "amount": "1200000",
            "expense_date": "2026-09-15",
            "is_recurring": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_recurring"] is True


# --- Davomat: bulk-mark + trend ---


async def _bulk_attendance_scenario(client: AsyncClient) -> dict:
    owner, branch_id = await _owner(client)
    group_id = await _create_group(client, owner, branch_id, "Bulk Guruh")

    child_ids = []
    for i in range(2):
        child_id = (
            await client.post(
                "/api/v1/children",
                headers=auth_header(owner),
                json={"full_name": f"Bulk Bola {i}", "birth_date": "2021-01-01"},
            )
        ).json()["id"]
        await client.post(
            f"/api/v1/children/{child_id}/enrollments",
            headers=auth_header(owner),
            json={
                "branch_id": branch_id,
                "group_id": group_id,
                "start_date": "2026-01-01",
                "status": "ACTIVE",
            },
        )
        child_ids.append(child_id)

    return {
        "owner": owner,
        "branch_id": branch_id,
        "group_id": group_id,
        "children": child_ids,
    }


async def test_attendance_bulk_mark_creates_and_updates(client: AsyncClient) -> None:
    s = await _bulk_attendance_scenario(client)

    first = await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(s["owner"]),
        json={
            "group_id": s["group_id"],
            "attendance_date": "2026-07-28",
            "entries": [
                {"child_id": s["children"][0], "status": "PRESENT"},
                {"child_id": s["children"][1], "status": "SICK"},
            ],
        },
    )
    assert first.status_code == 201, first.text
    rows = first.json()
    assert len(rows) == 2
    statuses = {r["child_id"]: r["status"] for r in rows}
    assert statuses[s["children"][0]] == "PRESENT"
    assert statuses[s["children"][1]] == "SICK"

    # Qayta yuborilganda yangilanadi (dublikat qator yaratilmaydi).
    second = await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(s["owner"]),
        json={
            "group_id": s["group_id"],
            "attendance_date": "2026-07-28",
            "entries": [
                {"child_id": s["children"][0], "status": "ABSENT"},
                {"child_id": s["children"][1], "status": "PRESENT"},
            ],
        },
    )
    assert second.status_code == 201
    statuses2 = {r["child_id"]: r["status"] for r in second.json()}
    assert statuses2[s["children"][0]] == "ABSENT"
    assert statuses2[s["children"][1]] == "PRESENT"

    roster = await client.get(
        "/api/v1/attendance/roster",
        headers=auth_header(s["owner"]),
        params={"group_id": s["group_id"], "date": "2026-07-28"},
    )
    assert len(roster.json()) == 2


async def test_attendance_bulk_mark_rejects_child_outside_group(
    client: AsyncClient,
) -> None:
    s = await _bulk_attendance_scenario(client)
    other_group = await _create_group(
        client, s["owner"], s["branch_id"], "Boshqa guruh"
    )
    outsider = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(s["owner"]),
            json={"full_name": "Begona Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{outsider}/enrollments",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "group_id": other_group,
            "start_date": "2026-01-01",
            "status": "ACTIVE",
        },
    )

    resp = await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(s["owner"]),
        json={
            "group_id": s["group_id"],
            "attendance_date": "2026-07-28",
            "entries": [{"child_id": outsider, "status": "PRESENT"}],
        },
    )
    assert resp.status_code == 409


async def test_attendance_trend(client: AsyncClient) -> None:
    s = await _bulk_attendance_scenario(client)
    # Trend oynasi `date.today()`ga nisbatan hisoblanadi, shuning uchun sana
    # qotib qolmasligi kerak — aks holda test ertasiga yiqiladi.
    today = date.today()
    await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(s["owner"]),
        json={
            "group_id": s["group_id"],
            "attendance_date": today.isoformat(),
            "entries": [
                {"child_id": s["children"][0], "status": "PRESENT"},
                {"child_id": s["children"][1], "status": "ABSENT"},
            ],
        },
    )

    resp = await client.get(
        "/api/v1/attendance/trend",
        headers=auth_header(s["owner"]),
        params={"group_id": s["group_id"], "days": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_id"] == s["group_id"]
    assert len(body["points"]) == 3
    last_point = body["points"][-1]
    assert last_point["total_count"] == 2
    assert last_point["present_count"] == 1


# --- Analytics: aging, revenue-by-group, expenses-by-category, break-even ---


async def test_dashboard_extended_analytics(client: AsyncClient) -> None:
    owner, branch_id = await _owner(client)
    group_id = await _create_group(client, owner, branch_id, "Analytics Guruhi")
    child_id = (
        await client.post(
            "/api/v1/children",
            headers=auth_header(owner),
            json={"full_name": "Analitika Bola", "birth_date": "2021-01-01"},
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/children/{child_id}/enrollments",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "group_id": group_id,
            "start_date": "2026-09-01",
            "status": "ACTIVE",
        },
    )
    fee = await client.patch(
        f"/api/v1/groups/{group_id}",
        headers=auth_header(owner),
        json={"monthly_fee": 500000},
    )
    assert fee.status_code == 200, fee.text
    await client.post(
        "/api/v1/invoices/generate",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "billing_period": "2026-09-15",
        },
    )

    categories = (
        await client.get("/api/v1/expense-categories", headers=auth_header(owner))
    ).json()
    food_category = next(c for c in categories if c["name"] == "Oziq-ovqat")
    rent_category = next(c for c in categories if c["name"] == "Ijara")

    await client.post(
        "/api/v1/expenses",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "category_id": food_category["id"],
            "amount": "100000",
            "expense_date": "2026-09-05",
        },
    )
    await client.post(
        "/api/v1/expenses",
        headers=auth_header(owner),
        json={
            "branch_id": branch_id,
            "category_id": rent_category["id"],
            "amount": "200000",
            "expense_date": "2026-09-05",
        },
    )

    dash = await client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_header(owner),
        params={"period_start": "2026-09-01", "period_end": "2026-09-30"},
    )
    assert dash.status_code == 200, dash.text
    body = dash.json()

    # Qarz qaysi kechikish guruhiga tushishi haqiqiy tizim sanasiga bog'liq
    # (muddat 2026-09-10) — shuning uchun guruhlar yig'indisi tekshiriladi.
    # Ilgari `not_due` tekshirilardi va test 10-sentabrdan keyin yiqilardi.
    aging = {row["label"]: _dec(row["total"]) for row in body["aging"]}
    assert sum(aging.values()) == _dec("500000")

    revenue = {row["group_id"]: _dec(row["total"]) for row in body["revenue_by_group"]}
    assert revenue[group_id] == _dec("500000")

    by_cat = {row["category_name"]: row for row in body["expenses_by_category"]}
    assert _dec(by_cat["Oziq-ovqat"]["total"]) == _dec("100000")
    assert by_cat["Oziq-ovqat"]["is_variable"] is True
    assert _dec(by_cat["Ijara"]["total"]) == _dec("200000")
    assert by_cat["Ijara"]["is_variable"] is False

    be = body["break_even"]
    assert be is not None
    assert be["active_children"] == 1
    assert _dec(be["fixed_costs"]) == _dec("200000")
    assert _dec(be["variable_costs"]) == _dec("100000")
    assert _dec(be["fee_per_child"]) == _dec("500000")
    assert _dec(be["contribution_margin"]) == _dec("400000")
    assert be["breakeven_children"] == 1
    assert _dec(be["breakeven_revenue"]) == _dec("250000")
