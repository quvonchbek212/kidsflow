"""Excel/CSV orqali bolalarni ommaviy import qilish testlari (7-bosqich B)."""

from __future__ import annotations

import io

import openpyxl
import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, complete_setup, create_staff, login

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"

_CSV_CONTENT = (
    "F.I.O.,Tug'ilgan sana,Ota-ona,Telefon\n"
    "Aliyev Ali,2020-05-01,Aliyev Vali,+998901234567\n"
    ",2020-06-01,,\n"  # ism yo'q — xato
    "Karimova Nilufar,not-a-date,,\n"  # sana formati noto'g'ri — xato
    "Yusupov Sardor,2021-03-15,,912345678\n"  # vasiy yo'q, faqat telefon (nomsiz)
)


async def _scenario(client: AsyncClient) -> dict:
    setup = await complete_setup(client)
    branch_id = setup["branch_id"]
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    await create_staff(
        client,
        owner,
        role="MANAGER",
        phone="+998900000301",
        password="mgr-123-456",
        branch_id=branch_id,
    )
    manager = (await login(client, "+998900000301", "mgr-123-456"))["access_token"]
    group_id = (
        await client.post(
            "/api/v1/groups",
            headers=auth_header(manager),
            json={"branch_id": branch_id, "name": "Import guruhi", "capacity": 20},
        )
    ).json()["id"]
    return {"manager": manager, "branch_id": branch_id, "group_id": group_id}


async def test_dry_run_preview_reports_errors_without_saving(
    client: AsyncClient,
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/children/import",
        headers=auth_header(s["manager"]),
        data={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "dry_run": "true",
        },
        files={"upload": ("children.csv", _CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is True
    assert body["total_rows"] == 4
    assert body["valid_rows"] == 2
    assert body["imported"] == 0

    invalid_rows = [r for r in body["rows"] if not r["valid"]]
    assert len(invalid_rows) == 2
    assert any("Ism" in e for r in invalid_rows for e in r["errors"])
    assert any("sana" in e.lower() for r in invalid_rows for e in r["errors"])

    # Hech narsa saqlanmagan bo'lishi kerak.
    children = await client.get("/api/v1/children", headers=auth_header(s["manager"]))
    assert children.json() == []


async def test_real_import_creates_children_with_enrollment_and_guardian(
    client: AsyncClient,
) -> None:
    s = await _scenario(client)
    resp = await client.post(
        "/api/v1/children/import",
        headers=auth_header(s["manager"]),
        data={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "dry_run": "false",
        },
        files={"upload": ("children.csv", _CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is False
    assert body["imported"] == 2

    children = (
        await client.get("/api/v1/children", headers=auth_header(s["manager"]))
    ).json()
    assert len(children) == 2
    names = {c["full_name"] for c in children}
    assert names == {"Aliyev Ali", "Yusupov Sardor"}

    with_guardian = next(c for c in children if c["full_name"] == "Aliyev Ali")
    assert len(with_guardian["guardians"]) == 1
    assert with_guardian["guardians"][0]["full_name"] == "Aliyev Vali"

    without_guardian = next(c for c in children if c["full_name"] == "Yusupov Sardor")
    assert without_guardian["guardians"] == []

    for child in children:
        assert child["status"] == "active"  # enrollment yaratilgan


async def test_xlsx_upload_is_parsed(client: AsyncClient) -> None:
    s = await _scenario(client)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Full name", "Birth date", "Guardian", "Phone"])
    sheet.append(["Excel Bola", "2022-01-10", "Excel Vasiy", "+998907654321"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    resp = await client.post(
        "/api/v1/children/import",
        headers=auth_header(s["manager"]),
        data={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "dry_run": "false",
        },
        files={
            "upload": (
                "children.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["imported"] == 1
    assert body["rows"][0]["full_name"] == "Excel Bola"


async def test_manager_without_branch_access_forbidden(client: AsyncClient) -> None:
    s = await _scenario(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    # Manager biriktirilmagan ikkinchi filial — shu filialga import qilish
    # huquqi bo'lmasligi kerak (bir xil bog'cha ichida, /setup emas).
    other_branch_id = (
        await client.post(
            "/api/v1/branches",
            headers=auth_header(owner),
            json={"name": "Boshqa filial", "capacity": 30},
        )
    ).json()["id"]
    resp = await client.post(
        "/api/v1/children/import",
        headers=auth_header(s["manager"]),
        data={
            "branch_id": other_branch_id,
            "group_id": s["group_id"],
            "dry_run": "true",
        },
        files={"upload": ("children.csv", _CSV_CONTENT.encode("utf-8"), "text/csv")},
    )
    assert resp.status_code == 403
