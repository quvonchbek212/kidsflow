"""Telegram bot kirish nuqtasi (7-bo'lim).

Bot faqat backend API bilan ishlaydi (bazaga to'g'ridan-to'g'ri ulanmaydi).
Ota-onalar taklif kodi orqali hisobni bog'lab, farzand ma'lumotlarini ko'radi.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import get_bot_settings
from deps import close_client
from handlers import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_bot_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN sozlanmagan. .env faylini tekshiring.")

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)

    logger.info("Telegram bot ishga tushdi")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await close_client()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
