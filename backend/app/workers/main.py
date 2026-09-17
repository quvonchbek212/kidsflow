"""Worker kirish nuqtasi (9-bo'lim).

Worker outbox hodisalarini muntazam qayta ishlaydi: outbox → bildirishnoma →
Telegram xabar → holat yangilash.

Har bir bosqich ALOHIDA sessiya va tranzaksiyada bajariladi. Ilgari hammasi
bitta tranzaksiyada edi: hisob-faktura yaratishdagi bitta xato butun siklni
orqaga qaytarar va bildirishnomalar ham har 5 soniyada qayta-qayta yiqilib,
umuman yuborilmay qolardi.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.core.logging import configure_logging
from app.database import async_session_factory, engine
from app.services import auto_billing, maintenance, notification_scheduler
from app.services.outbox_processor import OutboxProcessor
from app.services.telegram_sender import TelegramSender, get_default_sender

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _run_stage(
    factory: async_sessionmaker[AsyncSession],
    name: str,
    stage: Callable[[AsyncSession], Awaitable[T]],
) -> T | None:
    """Bosqichni o'z tranzaksiyasida bajaradi; xatosi boshqalariga tegmaydi."""
    async with factory() as session:
        try:
            result = await stage(session)
            await session.commit()
            return result
        except Exception:  # noqa: BLE001 — bitta bosqich xatosi siklni to'xtatmaydi
            await session.rollback()
            logger.exception("Worker bosqichida xatolik", extra={"stage": name})
            return None


async def process_cycle(
    factory: async_sessionmaker[AsyncSession], sender: TelegramSender
) -> tuple[int, int]:
    """Bitta sikl. Kunlik ishlar o'zi "bugun bajarilganmi" tekshiradi."""
    # Avval hisob-fakturalar: shu kungi eslatmalar yangi hisoblarni ham ko'rsin.
    await _run_stage(factory, "auto_billing", auto_billing.run_daily)
    await _run_stage(
        factory, "notification_scheduler", notification_scheduler.run_daily
    )
    await _run_stage(factory, "maintenance", maintenance.run_daily)
    result = await _run_stage(
        factory, "outbox", lambda session: OutboxProcessor(session, sender).run_once()
    )
    return result or (0, 0)


async def run() -> None:
    settings = get_settings()
    configure_logging(debug=settings.debug)
    logger.info("Worker ishga tushdi", extra={"environment": settings.environment})

    interval = settings.worker_poll_interval_seconds
    # Yuboruvchi bir marta yaratiladi — u HTTP ulanishlarini qayta ishlatadi.
    sender = get_default_sender()
    try:
        while True:
            processed, dispatched = await process_cycle(async_session_factory, sender)
            if processed or dispatched:
                logger.info(
                    "Outbox sikli",
                    extra={"processed": processed, "dispatched": dispatched},
                )
            await asyncio.sleep(interval)
    finally:
        close = getattr(sender, "aclose", None)
        if close is not None:
            await close()
        await engine.dispose()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Worker to'xtatildi")


if __name__ == "__main__":
    main()
