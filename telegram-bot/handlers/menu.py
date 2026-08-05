"""Asosiy menyu: farzandlar, davomat, hisobot, to'lov va AI yordamchi."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from api_client import BackendError
from deps import get_client
from formatters import format_attendance, format_invoices, format_reports
from keyboards.menus import child_menu_kb, children_kb, main_menu
from locales.texts import lang_of, t
from states import AskStates

router = Router()


async def _token_or_prompt(user_id: int, lang: str, answer) -> str | None:
    token = await get_client().get_session_token(user_id)
    if not token:
        await answer(t("not_linked", lang))
    return token


@router.callback_query(F.data == "children")
async def show_children(callback: CallbackQuery) -> None:
    lang = lang_of(callback.from_user.language_code)
    token = await _token_or_prompt(callback.from_user.id, lang, callback.message.answer)
    if not token:
        await callback.answer()
        return
    try:
        children = await get_client().list_children(token)
    except BackendError:
        await callback.message.answer(t("error", lang))
        await callback.answer()
        return

    if not children:
        await callback.message.answer(t("no_children", lang))
    else:
        await callback.message.answer(
            t("choose_child", lang), reply_markup=children_kb(children, lang)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("child:"))
async def show_child_menu(callback: CallbackQuery) -> None:
    lang = lang_of(callback.from_user.language_code)
    child_id = callback.data.split(":", 1)[1]
    await callback.message.answer(
        t("choose_child", lang), reply_markup=child_menu_kb(child_id, lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("act:"))
async def child_action(callback: CallbackQuery) -> None:
    lang = lang_of(callback.from_user.language_code)
    _, action, child_id = callback.data.split(":", 2)
    token = await _token_or_prompt(callback.from_user.id, lang, callback.message.answer)
    if not token:
        await callback.answer()
        return

    client = get_client()
    try:
        if action == "attendance":
            text = format_attendance(await client.child_attendance(token, child_id))
        elif action == "reports":
            text = format_reports(await client.child_reports(token, child_id))
        elif action == "invoices":
            text = format_invoices(await client.child_invoices(token, child_id))
        else:
            text = t("no_data", lang)
    except BackendError:
        text = t("error", lang)

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "ask")
async def start_ask(callback: CallbackQuery, state: FSMContext) -> None:
    lang = lang_of(callback.from_user.language_code)
    await state.set_state(AskStates.waiting_question)
    await callback.message.answer(t("ask_prompt", lang))
    await callback.answer()


@router.message(AskStates.waiting_question)
async def handle_question(message: Message, state: FSMContext) -> None:
    lang = lang_of(message.from_user.language_code if message.from_user else None)
    await state.clear()
    if not message.text or not message.from_user:
        return

    token = await get_client().get_session_token(message.from_user.id)
    if not token:
        await message.answer(t("not_linked", lang))
        return

    try:
        result = await get_client().ask_assistant(token, message.text.strip())
    except BackendError:
        await message.answer(t("error", lang))
        return

    answer = result.get("answer", t("no_data", lang))
    sources = result.get("sources") or []
    if sources:
        answer += f"\n\n📚 {t('sources', lang)}: " + ", ".join(sources)
    await message.answer(answer, reply_markup=main_menu(lang))
