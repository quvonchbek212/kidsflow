"""Hisobni bog'lash — taklif kodi (7-bo'lim)."""

from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from api_client import BackendError
from deps import get_client
from keyboards.menus import main_menu
from locales.texts import lang_of, t
from states import LinkStates

router = Router()


@router.message(LinkStates.waiting_code)
async def handle_code(message: Message, state: FSMContext) -> None:
    lang = lang_of(message.from_user.language_code if message.from_user else None)
    if not message.text or not message.from_user:
        await message.answer(t("send_code", lang))
        return

    code = message.text.strip()
    try:
        await get_client().link_account(
            code, message.from_user.id, message.chat.id
        )
    except BackendError:
        await message.answer(t("link_failed", lang))
        return

    await state.clear()
    await message.answer(t("link_success", lang))
    await message.answer(t("welcome_linked", lang), reply_markup=main_menu(lang))
