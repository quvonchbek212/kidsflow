"""Antivirus tekshiruvi (`app.utils.virus_scan`).

Ilgari har bir fayl so'zsiz CLEAN deb belgilanardi — ustun tekshirilgandek
ko'rinardi, aslida hech narsa tekshirilmasdi.
"""

from __future__ import annotations

import asyncio

import pytest
from app.config import get_settings
from app.models.enums import FileScanStatus
from app.utils.virus_scan import scan_bytes

pytestmark = pytest.mark.asyncio


async def test_disabled_scanner_reports_pending() -> None:
    """Skaner sozlanmagan bo'lsa "toza" emas, "tekshirilmagan" deyiladi."""
    assert get_settings().file_scan_enabled is False
    assert await scan_bytes(b"salom") is FileScanStatus.PENDING


async def test_unreachable_scanner_rejects_file(monkeypatch) -> None:
    """Skaner o'chgan bo'lsa fayl o'tkazib yuborilmaydi.

    "Tekshira olmadim, demak toza" xavfli xulosa — nosozlik jimgina
    o'tib ketmasligi kerak.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "file_scan_enabled", True)
    monkeypatch.setattr(settings, "clamav_host", "127.0.0.1")
    # Hech kim tinglamaydigan port.
    monkeypatch.setattr(settings, "clamav_port", 1)

    assert await scan_bytes(b"salom") is FileScanStatus.INFECTED


async def test_timeout_rejects_file(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "file_scan_enabled", True)
    monkeypatch.setattr(settings, "file_scan_timeout_seconds", 0.01)

    async def _hang(*_args, **_kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr("app.utils.virus_scan._scan_via_clamd", _hang)
    assert await scan_bytes(b"salom") is FileScanStatus.INFECTED


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (b"stream: OK\0", FileScanStatus.CLEAN),
        (b"stream: Eicar-Test-Signature FOUND\0", FileScanStatus.INFECTED),
        (b"tushunarsiz javob\0", FileScanStatus.INFECTED),
    ],
)
async def test_clamd_replies_are_interpreted(
    monkeypatch, reply: bytes, expected: FileScanStatus
) -> None:
    """clamd javobining uch shakli to'g'ri o'qilishi kerak."""
    settings = get_settings()
    monkeypatch.setattr(settings, "file_scan_enabled", True)

    class _Reader:
        async def read(self, _n: int) -> bytes:
            return reply

    class _Writer:
        def write(self, _data: bytes) -> None: ...
        async def drain(self) -> None: ...
        def close(self) -> None: ...
        async def wait_closed(self) -> None: ...

    async def _connect(_host, _port):  # noqa: ANN001, ANN202
        return _Reader(), _Writer()

    monkeypatch.setattr("asyncio.open_connection", _connect)
    assert await scan_bytes(b"salom") is expected
