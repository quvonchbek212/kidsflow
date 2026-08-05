"""Bot FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LinkStates(StatesGroup):
    waiting_code = State()


class AskStates(StatesGroup):
    waiting_question = State()
