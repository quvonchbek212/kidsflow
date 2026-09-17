"""Auditda topilgan barqarorlik va funksional xatolar qaytmasligi uchun testlar."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.exceptions import register_exception_handlers
from app.models.messaging import Notification
from app.models.user import RefreshToken, User
from argon2 import PasswordHasher
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from tests.conftest import (
    TINY_PNG,
    FakeTelegramSender,
    auth_header,
    bot_header,
    complete_setup,
    login,
    run_outbox,
)
from tests.integration.test_daily_reports import _scenario as report_scenario
from tests.integration.test_notifications_v2 import _scenario as parent_scenario

pytestmark = pytest.mark.asyncio

OWNER_PHONE = "+998901112233"
OWNER_PASSWORD = "owner-parol-123"


# --- Bildirishnoma navbati ------------------------------------------------------


async def test_undeliverable_notifications_do_not_block_the_queue(
    client: AsyncClient, session_factory
) -> None:
    await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    user_id = uuid.UUID(
        (await client.get("/api/v1/auth/me", headers=auth_header(owner))).json()["id"]
    )

    async with session_factory() as session:
        for _ in range(50):
            session.add(
                Notification(
                    user_id=user_id,
                    channel="TELEGRAM",
                    notification_type="BROADCAST",
                    payload={"text": "eski"},
                    target_chat_id=None,
                    status="PENDING",
                )
            )
        await session.commit()
        session.add(
            Notification(
                user_id=user_id,
                channel="TELEGRAM",
                notification_type="BROADCAST",
                payload={"text": "YANGI"},
                target_chat_id=777,
                status="PENDING",
            )
        )
        await session.commit()

    sender = FakeTelegramSender(succeed=True)
    for _ in range(3):
        await run_outbox(session_factory, sender)
    assert sender.sent == [(777, "YANGI")]

    async with session_factory() as session:
        failed = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.status == "FAILED")
        )
    assert failed == 50


async def test_notification_fails_after_max_retries(
    client: AsyncClient, session_factory, monkeypatch
) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "outbox_max_retries", 2)
    await complete_setup(client)
    owner = (await login(client, OWNER_PHONE, OWNER_PASSWORD))["access_token"]
    user_id = uuid.UUID(
        (await client.get("/api/v1/auth/me", headers=auth_header(owner))).json()["id"]
    )
    async with session_factory() as session:
        session.add(
            Notification(
                user_id=user_id,
                channel="TELEGRAM",
                notification_type="BROADCAST",
                payload={"text": "bloklangan"},
                target_chat_id=555,
                status="PENDING",
            )
        )
        await session.commit()

    sender = FakeTelegramSender(succeed=False)
    for _ in range(4):
        await run_outbox(session_factory, sender)
    # Faqat 2 marta urinildi, keyin FAILED.
    assert len(sender.sent) == 2
    async with session_factory() as session:
        status = await session.scalar(select(Notification.status))
    assert status == "FAILED"


# --- Validatsiya va 409 ---------------------------------------------------------


async def test_bulk_attendance_rejects_duplicate_children(client: AsyncClient) -> None:
    s = await parent_scenario(client)
    entry = {"child_id": s["child_id"], "status": "PRESENT"}
    resp = await client.post(
        "/api/v1/attendance/bulk",
        headers=auth_header(s["manager"]),
        json={
            "group_id": s["group_id"],
            "attendance_date": "2026-09-16",
            "entries": [entry, entry],
        },
    )
    assert resp.status_code == 422, resp.text


async def test_integrity_error_becomes_409() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed"))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as local:
        resp = await local.get("/boom")
    assert resp.status_code == 409
    # Jadval/ustun nomlari javobga chiqmaydi.
    assert "UNIQUE" not in resp.text


# --- Bot sessiyasi --------------------------------------------------------------


async def test_telegram_session_does_not_create_refresh_tokens(
    client: AsyncClient, session_factory
) -> None:
    await parent_scenario(client)

    async def count_tokens() -> int:
        async with session_factory() as session:
            return int(
                await session.scalar(select(func.count()).select_from(RefreshToken))
                or 0
            )

    before = await count_tokens()
    for _ in range(5):
        resp = await client.post(
            "/api/v1/telegram/session",
            headers=bot_header(),
            json={"telegram_user_id": 990199},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"]
    assert await count_tokens() == before


# --- Ommaviy xabar ----------------------------------------------------------------


async def test_broadcast_skips_families_who_left(client: AsyncClient) -> None:
    s = await parent_scenario(client)
    body = {"branch_id": s["branch_id"], "audience": "all", "text": "Salom"}

    first = await client.post(
        "/api/v1/messages/broadcast", headers=auth_header(s["manager"]), json=body
    )
    assert first.json()["queued_count"] == 1

    await client.patch(
        f"/api/v1/children/{s['child_id']}",
        headers=auth_header(s["manager"]),
        json={"is_active": False},
    )
    second = await client.post(
        "/api/v1/messages/broadcast", headers=auth_header(s["manager"]), json=body
    )
    assert second.json()["queued_count"] == 0


# --- Import ---------------------------------------------------------------------


async def _import(client: AsyncClient, s: dict, name: str, content: bytes):
    return await client.post(
        "/api/v1/children/import",
        headers=auth_header(s["manager"]),
        data={
            "branch_id": s["branch_id"],
            "group_id": s["group_id"],
            "dry_run": "true",
        },
        files={"upload": (name, content, "text/csv")},
    )


async def test_import_accepts_windows_1251_csv(client: AsyncClient) -> None:
    s = await parent_scenario(client)
    csv_text = "ФИО,Дата рождения\nИванов Иван,01.02.2021\n"
    resp = await _import(client, s, "bolalar.csv", csv_text.encode("cp1251"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows"][0]["full_name"] == "Иванов Иван"


async def test_import_rejects_too_many_rows(client: AsyncClient) -> None:
    from app.services.import_service import MAX_IMPORT_ROWS

    s = await parent_scenario(client)
    lines = ["FIO,Tug'ilgan sana"] + [
        f"Bola {i},01.02.2021" for i in range(MAX_IMPORT_ROWS + 5)
    ]
    resp = await _import(client, s, "katta.csv", "\n".join(lines).encode())
    assert resp.status_code == 400, resp.text


# --- Rate limit va login ----------------------------------------------------------


async def test_refresh_has_its_own_rate_limit_bucket(
    client: AsyncClient, monkeypatch
) -> None:
    from app.config import get_settings
    from app.core.rate_limit import get_rate_limiter

    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "login_rate_limit_max", 2)
    get_rate_limiter().reset()
    await complete_setup(client)

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "yaroqsiz-token"}
        )
        assert resp.status_code == 401
    # Refresh urinishlari login limitini sarflamagan.
    ok = await client.post(
        "/api/v1/auth/login",
        json={"login": OWNER_PHONE, "password": OWNER_PASSWORD},
    )
    assert ok.status_code == 200, ok.text


async def test_unknown_login_still_runs_password_hashing(
    client: AsyncClient, monkeypatch
) -> None:
    from app.services import auth_service

    calls: list[str] = []
    monkeypatch.setattr(
        auth_service, "burn_password_check", lambda password: calls.append(password)
    )
    await complete_setup(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"login": "yoq-foydalanuvchi", "password": "x" * 10}
    )
    assert resp.status_code == 401
    assert calls == ["x" * 10]


async def test_outdated_password_hash_is_upgraded_on_login(
    client: AsyncClient, session_factory
) -> None:
    await complete_setup(client)
    weak = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    async with session_factory() as session:
        owner = (
            await session.execute(select(User).where(User.phone == OWNER_PHONE))
        ).scalar_one()
        owner.password_hash = weak.hash(OWNER_PASSWORD)
        old_hash = owner.password_hash
        await session.commit()

    await login(client, OWNER_PHONE, OWNER_PASSWORD)

    async with session_factory() as session:
        new_hash = await session.scalar(
            select(User.password_hash).where(User.phone == OWNER_PHONE)
        )
    assert new_hash != old_hash
    assert "t=1," not in (new_hash or "")


# --- Hisobot fayllari -------------------------------------------------------------


async def test_report_cannot_attach_file_uploaded_by_someone_else(
    client: AsyncClient,
) -> None:
    s = await report_scenario(client)
    uploaded = await client.post(
        "/api/v1/files",
        headers=auth_header(s["manager"]),
        files={"upload": ("chek.png", TINY_PNG, "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text

    resp = await client.post(
        "/api/v1/daily-reports",
        headers=auth_header(s["teacher"]),
        json={
            "child_id": s["child_id"],
            "report_date": "2026-09-10",
            "activities_text": "O'ynadi",
            "file_ids": [uploaded.json()["id"]],
        },
    )
    assert resp.status_code == 403, resp.text


async def test_manager_can_edit_report_keeping_teacher_files(
    client: AsyncClient,
) -> None:
    s = await report_scenario(client)
    photo = await client.post(
        "/api/v1/files",
        headers=auth_header(s["teacher"]),
        files={"upload": ("rasm.png", TINY_PNG, "image/png")},
    )
    file_id = photo.json()["id"]
    report = await client.post(
        "/api/v1/daily-reports",
        headers=auth_header(s["teacher"]),
        json={
            "child_id": s["child_id"],
            "report_date": "2026-09-11",
            "activities_text": "Rasm chizdi",
            "file_ids": [file_id],
        },
    )
    assert report.status_code == 201, report.text

    edited = await client.patch(
        f"/api/v1/daily-reports/{report.json()['id']}",
        headers=auth_header(s["manager"]),
        json={"final_summary": "Yaxshi kun", "file_ids": [file_id]},
    )
    assert edited.status_code == 200, edited.text


# --- Oylik xarajati sanasi ----------------------------------------------------------


async def test_payroll_expense_uses_local_date(client: AsyncClient) -> None:
    from tests.integration.test_payroll_run import _scenario as payroll_scenario

    s = await payroll_scenario(client)
    # 2026-09-30 20:30 UTC = Toshkentda 1-oktabr 01:30.
    run = await client.post(
        "/api/v1/payroll/runs",
        headers=auth_header(s["owner"]),
        json={
            "branch_id": s["branch_id"],
            "user_id": s["staff_id"],
            "period": "2026-09-01",
            "paid_at": "2026-09-30T20:30:00Z",
        },
    )
    assert run.status_code == 201, run.text
    expenses = await client.get(
        "/api/v1/expenses",
        headers=auth_header(s["owner"]),
        params={"branch_id": s["branch_id"]},
    )
    expense = next(e for e in expenses.json() if e["id"] == run.json()["expense_id"])
    assert expense["expense_date"] == "2026-10-01"


# --- Worker ---------------------------------------------------------------------


async def test_failing_billing_stage_does_not_stop_notifications(
    client: AsyncClient, session_factory, monkeypatch
) -> None:
    from app.services import auto_billing
    from app.workers import main as worker

    s = await parent_scenario(client)
    await client.post(
        "/api/v1/messages/broadcast",
        headers=auth_header(s["manager"]),
        json={"branch_id": s["branch_id"], "audience": "all", "text": "Salom"},
    )

    async def broken(session, today=None):  # noqa: ARG001
        raise RuntimeError("hisob-faktura bosqichi yiqildi")

    monkeypatch.setattr(auto_billing, "run_daily", broken)
    sender = FakeTelegramSender(succeed=True)
    _, dispatched = await worker.process_cycle(session_factory, sender)
    assert dispatched == 1
    assert sender.sent


async def test_maintenance_removes_stale_tokens(
    client: AsyncClient, session_factory
) -> None:
    from app.services import maintenance

    await complete_setup(client)
    await login(client, OWNER_PHONE, OWNER_PASSWORD)  # amaldagi token
    async with session_factory() as session:
        user_id = await session.scalar(select(User.id).where(User.phone == OWNER_PHONE))
        now = datetime.now(UTC)
        session.add(
            RefreshToken(
                user_id=user_id, token_hash="a" * 64, expires_at=now - timedelta(days=1)
            )
        )
        session.add(
            RefreshToken(
                user_id=user_id,
                token_hash="b" * 64,
                expires_at=now + timedelta(days=5),
                revoked_at=now,
            )
        )
        await session.commit()

    async with session_factory() as session:
        removed = await maintenance.run_daily(session)
        await session.commit()
    assert removed == 2

    async with session_factory() as session:
        left = await session.scalar(select(func.count()).select_from(RefreshToken))
    assert left == 1


# --- To'lovlar tarixi ---------------------------------------------------------------


async def test_child_payments_list_and_reverse_restores_debt(
    client: AsyncClient,
) -> None:
    from tests.integration.test_finance import _generate_invoice
    from tests.integration.test_finance import _scenario as finance_scenario

    s = await finance_scenario(client)
    await _generate_invoice(client, s)
    headers = auth_header(s["manager"])
    paid = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "child_id": s["child_id"],
            "amount": "200000",
            "payment_method": "CASH",
            "paid_at": "2026-09-05T10:00:00Z",
        },
    )
    assert paid.status_code == 201, paid.text

    listed = await client.get(
        "/api/v1/payments", headers=headers, params={"child_id": s["child_id"]}
    )
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()] == [paid.json()["id"]]

    before = (
        await client.get(f"/api/v1/children/{s['child_id']}/invoices", headers=headers)
    ).json()
    rev = await client.post(
        f"/api/v1/payments/{paid.json()['id']}/reverse", headers=headers
    )
    assert rev.status_code == 200, rev.text
    after = (
        await client.get(f"/api/v1/children/{s['child_id']}/invoices", headers=headers)
    ).json()
    assert (
        sum(float(i["outstanding_amount"]) for i in after)
        == sum(float(i["outstanding_amount"]) for i in before) + 200000
    )


async def test_maintenance_applies_retention_periods(
    client: AsyncClient, session_factory
) -> None:
    """Bildirishnoma/outbox 90 kun, audit 365 kun; kutayotganlarga tegilmaydi."""
    from app.models.audit import AuditLog
    from app.models.messaging import OutboxEvent
    from app.services import maintenance

    await complete_setup(client)
    now = datetime.now(UTC)
    old = now - timedelta(days=120)
    very_old = now - timedelta(days=400)

    async with session_factory() as session:
        user_id = await session.scalar(select(User.id).where(User.phone == OWNER_PHONE))
        for status, created in [
            ("SENT", old),  # o'chadi
            ("FAILED", old),  # o'chadi
            ("PENDING", old),  # qoladi — hali yuborilmagan
            ("SENT", now),  # qoladi — yangi
        ]:
            session.add(
                Notification(
                    user_id=user_id,
                    channel="TELEGRAM",
                    notification_type="BROADCAST",
                    payload={"text": status},
                    status=status,
                    created_at=created,
                )
            )
        session.add(
            OutboxEvent(event_type="X", payload={}, status="PROCESSED", created_at=old)
        )
        session.add(
            OutboxEvent(event_type="X", payload={}, status="PENDING", created_at=old)
        )
        session.add(AuditLog(action="ESKI", entity_type="test", created_at=very_old))
        session.add(AuditLog(action="YANGI", entity_type="test", created_at=old))
        await session.commit()

    async with session_factory() as session:
        await maintenance.run_daily(session)
        await session.commit()

    async with session_factory() as session:
        notifications = sorted(
            (await session.execute(select(Notification.status))).scalars().all()
        )
        outbox = (await session.execute(select(OutboxEvent.status))).scalars().all()
        actions = set((await session.execute(select(AuditLog.action))).scalars().all())
    assert notifications == ["PENDING", "SENT"]
    assert outbox == ["PENDING"]
    assert "ESKI" not in actions and "YANGI" in actions
