"""Bot handlerlari paketi."""

from aiogram import Router

from handlers import link_account, menu, start

router = Router()
# Tartib muhim: start va menu callbacklari avval, so'ng holat handlerlari.
router.include_router(start.router)
router.include_router(menu.router)
router.include_router(link_account.router)
