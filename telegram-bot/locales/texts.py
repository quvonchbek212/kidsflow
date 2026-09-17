"""Oddiy i18n — o'zbek va rus (8-bo'lim: uz/ru qo'llab-quvvatlash).

Til Telegram foydalanuvchi `language_code` sidan aniqlanadi (ru → rus, aks holda uz).
"""

from __future__ import annotations

_TEXTS: dict[str, dict[str, str]] = {
    "welcome_unlinked": {
        "uz": (
            "Assalomu alaykum! KIDSFLOW botiga xush kelibsiz.\n\n"
            "Hisobingizni bog'lash uchun menejer bergan taklif kodini yuboring."
        ),
        "ru": (
            "Здравствуйте! Добро пожаловать в бот KIDSFLOW.\n\n"
            "Отправьте код-приглашение от менеджера, чтобы привязать аккаунт."
        ),
    },
    "welcome_linked": {
        "uz": "Assalomu alaykum! Nimani ko'rmoqchisiz?",
        "ru": "Здравствуйте! Что вы хотите посмотреть?",
    },
    "link_success": {
        "uz": "✅ Hisobingiz muvaffaqiyatli bog'landi!",
        "ru": "✅ Ваш аккаунт успешно привязан!",
    },
    "link_failed": {
        "uz": "❌ Kod yaroqsiz yoki muddati o'tgan. Menejerdan yangi kod so'rang.",
        "ru": "❌ Код недействителен или истёк. Запросите новый код у менеджера.",
    },
    "send_code": {
        "uz": "Iltimos, taklif kodini yuboring.",
        "ru": "Пожалуйста, отправьте код-приглашение.",
    },
    "btn_children": {"uz": "👶 Farzandlarim", "ru": "👶 Мои дети"},
    "btn_ask": {"uz": "💬 Savol berish", "ru": "💬 Задать вопрос"},
    "btn_attendance": {"uz": "📋 Davomat", "ru": "📋 Посещаемость"},
    "btn_reports": {"uz": "📝 Kunlik hisobot", "ru": "📝 Отчёты"},
    "btn_invoices": {"uz": "💰 To'lovlar", "ru": "💰 Оплаты"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "btn_staff": {"uz": "✍️ Xodimga yozish", "ru": "✍️ Написать сотруднику"},
    "staff_prompt": {
        "uz": (
            "Savolingizni yozing — bog'cha xodimi ko'radi va javob beradi.\n"
            "Javob shu yerga keladi."
        ),
        "ru": (
            "Напишите свой вопрос — сотрудник детского сада увидит его и ответит.\n"
            "Ответ придёт сюда."
        ),
    },
    "staff_sent": {
        "uz": "✅ Xabaringiz yuborildi. Xodim javob berganda shu yerda ko'rasiz.",
        "ru": "✅ Ваше сообщение отправлено. Ответ сотрудника придёт сюда.",
    },
    "no_children": {
        "uz": "Sizga biriktirilgan farzand topilmadi.",
        "ru": "Привязанных детей не найдено.",
    },
    "choose_child": {"uz": "Farzandni tanlang:", "ru": "Выберите ребёнка:"},
    "no_data": {"uz": "Ma'lumot yo'q.", "ru": "Нет данных."},
    "ask_prompt": {
        "uz": "Savolingizni yozing (masalan: bog'cha ish vaqti).",
        "ru": "Напишите ваш вопрос (например: часы работы сада).",
    },
    "error": {
        "uz": "Xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Произошла ошибка. Попробуйте позже.",
    },
    "not_linked": {
        "uz": "Avval hisobingizni bog'lang — taklif kodini yuboring.",
        "ru": "Сначала привяжите аккаунт — отправьте код-приглашение.",
    },
    "sources": {"uz": "Manba", "ru": "Источник"},
}


def lang_of(language_code: str | None) -> str:
    return "ru" if (language_code or "").lower().startswith("ru") else "uz"


def t(key: str, lang: str) -> str:
    entry = _TEXTS.get(key, {})
    return entry.get(lang) or entry.get("uz") or key
