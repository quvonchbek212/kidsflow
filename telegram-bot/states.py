"""Bot FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LinkStates(StatesGroup):
    waiting_code = State()


class AskStates(StatesGroup):
    waiting_question = State()


class StaffMessageStates(StatesGroup):
    """Ota-onaning xodimga yozadigan savoli.

    `AskStates` dan farqi: u AI yordamchiga boradi va darhol javob qaytaradi,
    bu esa veb-saytdagi Xabarlar bo'limiga tushadi va tirik xodim javob beradi.
    """

    waiting_message = State()
