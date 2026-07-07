from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

logger = logging.getLogger(__name__)

USER_COMMANDS = [
    BotCommand(command="start", description="Начать работу"),
    BotCommand(command="addresses", description="Мои адреса"),
    BotCommand(command="add_address", description="Добавить адрес"),
    BotCommand(command="history", description="Последние уведомления"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="delete_me", description="Удалить мои данные"),
]

ADMIN_COMMANDS = [
    BotCommand(command="sync", description="Запустить синхронизацию"),
    BotCommand(command="sync_dry_run", description="Проверить синхронизацию без рассылки"),
    BotCommand(command="latest", description="Последние отключения"),
    BotCommand(command="stats", description="Статистика"),
    BotCommand(command="sources", description="Статус источника"),
    BotCommand(command="broadcast", description="Рассылка пользователям"),
]


async def setup_bot_commands(bot: Bot, admin_ids: list[int]) -> None:
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                USER_COMMANDS + ADMIN_COMMANDS,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except TelegramAPIError:
            logger.warning("Failed to set admin commands for chat_id=%s", admin_id, exc_info=True)
