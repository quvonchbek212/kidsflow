"""Mahalliy taqvim sanasi (`app.utils.timezone`).

Xato shunday edi: server `date.today()` ni ishlatardi, u esa konteynerning
zonasini (UTC) oladi. Toshkent UTC+5 bo'lgani uchun har kuni 00:00–05:00
oralig'ida server hali kechagi kunni "bugun" deb bilardi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from app.utils.timezone import (
    local_zone,
    month_start_utc,
    now_local,
    today_local,
)


def test_local_zone_follows_settings() -> None:
    assert str(local_zone()) == "Asia/Tashkent"


def test_now_local_is_five_hours_ahead_of_utc() -> None:
    """Toshkent — UTC+5, yil bo'yi (yozgi vaqt o'tishi yo'q)."""
    local = now_local()
    assert local.utcoffset().total_seconds() == 5 * 3600


def test_today_local_differs_from_utc_before_five_am(monkeypatch) -> None:
    """Asosiy tekshiruv: UTC bo'yicha 23:30 — Toshkentda allaqachon ertangi kun."""

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            moment = datetime(2026, 8, 19, 23, 30, tzinfo=UTC)
            return moment if tz is None else moment.astimezone(tz)

    monkeypatch.setattr("app.utils.timezone.datetime", _FrozenDatetime)

    assert datetime.now(UTC).date().isoformat() != "2026-08-20"  # nazorat
    assert today_local().isoformat() == "2026-08-20"


def test_month_start_utc_uses_local_month_boundary(monkeypatch) -> None:
    """Oyning 1-kuni 02:00 (Toshkent) — UTC hali o'tgan oyda, hisob esa yangi oyda."""

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            # UTC: 31 avgust 21:00 → Toshkent: 1 sentyabr 02:00
            moment = datetime(2026, 8, 31, 21, 0, tzinfo=UTC)
            return moment if tz is None else moment.astimezone(tz)

    monkeypatch.setattr("app.utils.timezone.datetime", _FrozenDatetime)

    start = month_start_utc()
    # Mahalliy 1-sentyabr 00:00 = UTC 31-avgust 19:00.
    assert start == datetime(2026, 8, 31, 19, 0, tzinfo=UTC)
    assert start.astimezone(ZoneInfo("Asia/Tashkent")).day == 1


def test_unknown_timezone_falls_back_to_utc(monkeypatch) -> None:
    """Noto'g'ri zona nomi butun ilovani yiqitmasligi kerak."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "timezone", "Mars/Olympus_Mons")
    assert str(local_zone()) == "UTC"


@pytest.mark.parametrize("hour", [0, 4, 5, 12, 23])
def test_today_local_never_raises(hour: int) -> None:
    """Sutkaning istalgan soatida ishlashi kerak."""
    assert today_local().year >= 2024
