"""Inline klaviaturalar."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from locales.texts import t


def main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_children", lang), callback_data="children")],
            [InlineKeyboardButton(text=t("btn_ask", lang), callback_data="ask")],
        ]
    )


def children_kb(children: list[dict], lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=c["full_name"], callback_data=f"child:{c['id']}")]
        for c in children
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def child_menu_kb(child_id: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_attendance", lang),
                    callback_data=f"act:attendance:{child_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_reports", lang),
                    callback_data=f"act:reports:{child_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_invoices", lang),
                    callback_data=f"act:invoices:{child_id}",
                )
            ],
            [InlineKeyboardButton(text=t("btn_back", lang), callback_data="children")],
        ]
    )
