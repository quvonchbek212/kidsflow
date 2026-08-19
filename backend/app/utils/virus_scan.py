"""Yuklangan fayllarni ClamAV orqali tekshirish (11-bo'lim).

Ilgari har bir fayl so'zsiz `CLEAN` deb belgilanardi — ya'ni ustun bor edi,
lekin unga yozilgan qiymat hech narsani anglatmasdi. Bu eng yomon holat:
jadval tekshirilgandek ko'rinadi, aslida tekshirilmagan.

Endi uch holat rost:
- skaner sozlanmagan bo'lsa — `PENDING` (tekshirilmagan, va shunday deyiladi);
- skaner toza desa — `CLEAN`;
- zarar topilsa yoki skaner javob bermasa — `INFECTED` (ehtiyot yuzasidan
  yuklashga ruxsat berilmaydi).

ClamAV bilan aloqa uning `INSTREAM` protokoli orqali — bu oddiy TCP almashuv,
shuning uchun qo'shimcha kutubxona kerak emas.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.models.enums import FileScanStatus

logger = logging.getLogger(__name__)

# INSTREAM har bir bo'lakni uzunligi bilan yuboradi; nol uzunlik oxirini
# bildiradi. ClamAV standart chegarasi 25 MB, bo'lak hajmi undan kichik.
_CHUNK_SIZE = 64 * 1024


async def scan_bytes(content: bytes) -> FileScanStatus:
    """Faylni tekshiradi va holatini qaytaradi."""
    settings = get_settings()
    if not settings.file_scan_enabled:
        return FileScanStatus.PENDING

    try:
        return await asyncio.wait_for(
            _scan_via_clamd(content, settings.clamav_host, settings.clamav_port),
            timeout=settings.file_scan_timeout_seconds,
        )
    except TimeoutError:
        logger.error("ClamAV javob bermadi (timeout) — fayl rad etildi")
        return FileScanStatus.INFECTED
    except OSError as exc:
        # Skaner o'chgan yoki tarmoq yo'q. Faylni "toza" deb o'tkazib yuborish
        # xavfli, shuning uchun rad etamiz — nosozlik jimgina o'tmasin.
        logger.error("ClamAV bilan bog'lanib bo'lmadi: %s", exc)
        return FileScanStatus.INFECTED


async def _scan_via_clamd(content: bytes, host: str, port: int) -> FileScanStatus:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"zINSTREAM\0")
        for start in range(0, len(content), _CHUNK_SIZE):
            chunk = content[start : start + _CHUNK_SIZE]
            writer.write(len(chunk).to_bytes(4, "big") + chunk)
        writer.write((0).to_bytes(4, "big"))
        await writer.drain()

        raw = (await reader.read(4096)).decode("utf-8", "replace").strip("\0 \n")
    finally:
        writer.close()
        await writer.wait_closed()

    # Javob shakllari: "stream: OK" yoki "stream: <nom> FOUND".
    if raw.endswith("OK"):
        return FileScanStatus.CLEAN
    if raw.endswith("FOUND"):
        logger.warning("Zararli fayl topildi: %s", raw)
        return FileScanStatus.INFECTED

    logger.error("ClamAV tushunarsiz javob qaytardi: %r", raw)
    return FileScanStatus.INFECTED
