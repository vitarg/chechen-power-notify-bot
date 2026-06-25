from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def address_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить так", callback_data="address:confirm"),
                InlineKeyboardButton(text="Уточнить", callback_data="address:retry"),
            ]
        ]
    )


def addresses_keyboard(address_ids: list[int]) -> InlineKeyboardMarkup | None:
    if not address_ids:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Удалить #{address_id}", callback_data=f"address:delete:{address_id}")]
            for address_id in address_ids
        ]
    )


def broadcast_confirm_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отправить", callback_data=f"broadcast:send:{broadcast_id}"),
                InlineKeyboardButton(text="Отменить", callback_data=f"broadcast:cancel:{broadcast_id}"),
            ]
        ]
    )

