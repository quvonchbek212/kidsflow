"""Worker kirish nuqtasi (9-bo'lim).

Worker outbox hodisalarini muntazam qayta ishlaydi: outbox → bildirishnoma →
Telegram xabar → holat yangilash. Har bir sikl alohida DB sessiyasida bajariladi.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.core.logging import configure_logging
from app.database import async_session_factory, engine
from app.services import notification_scheduler
from app.services.outbox_processor import OutboxProcessor
from app.services.telegram_sender import get_default_sender

logger = logging.getLogger(__name__)


async def _process_cycle() -> tuple[int, int]:
    """Bitta qayta ishlash siklini bajaradi va commit qiladi.

    Kunlik bildirishnoma ishlari (`notification_scheduler.run_daily`) ham shu
    yerda chaqiriladi — bugun allaqachon bajarilgan bo'lsa o'zi jim o'tadi
    (`daily_job_runs` orqali himoyalangan), shuning uchun alohida interval
    kerak emas.
    """
    sender = get_default_sender()
    async with async_session_factory() as session:
        try:
            await notification_scheduler.run_daily(session)
            processor = OutboxProcessor(session, sender)
            result = await processor.run_once()
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


async def run() -> None:
    settings = get_settings()
    configure_logging(debug=settings.debug)
    logger.info("Worker ishga tushdi", extra={"environment": settings.environment})

    interval = settings.worker_poll_interval_seconds
    try:
        while True:
            try:
                processed, dispatched = await _process_cycle()
                if processed or dispatched:
                    logger.info(
                        "Outbox sikli",
                        extra={"processed": processed, "dispatched": dispatched},
                    )
            except Exception:  # noqa: BLE001 — sikl xatosi workerni to'xtatmaydi
                logger.exception("Worker siklida xatolik")
            await asyncio.sleep(interval)
    finally:
        await engine.dispose()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Worker to'xtatildi")


if __name__ == "__main__":
    main()
