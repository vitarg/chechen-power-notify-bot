from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddAddress(StatesGroup):
    waiting_for_title = State()
    waiting_for_address = State()
    waiting_for_confirmation = State()


class BroadcastFlow(StatesGroup):
    waiting_for_text = State()

