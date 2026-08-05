"""/start, /menu, /help handlerlari."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from deps import get_client
from keyboards.menus import main_menu
from locales.texts import lang_of, t
from states import LinkStates

router = Router()


async def _show_entry(message: Message, state: FSMContext) -> None:
    lang = lang_of(message.from_user.language_code if message.from_user else None)
    user_id = message.from_user.id if message.from_user else 0

    token = await get_client().get_session_token(user_id)
    if token:
        await state.clear()
        await message.answer(t("welcome_linked", lang), reply_markup=main_menu(lang))
    else:
        await state.set_state(LinkStates.waiting_code)
        await message.answer(t("welcome_unlinked", lang))


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await _show_entry(message, state)


@router.message(Command("menu"))
async def handle_menu(message: Message, state: FSMContext) -> None:
    await _show_entry(message, state)


@router.message(Command("help"))
async def handle_help(message: Message, state: FSMContext) -> None:
    await _show_entry(message, state)
