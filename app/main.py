from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.commands import setup_bot_commands
from app.bot.handlers import include_routers
from app.config import get_settings
from app.db.session import create_session_factory
from app.jobs.scheduler import create_scheduler
from app.services.container import AppContainer


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    bot = Bot(token=settings.bot_token)
    container = AppContainer(settings=settings, session_factory=session_factory, bot=bot)

    dispatcher = Dispatcher()
    dispatcher["container"] = container
    include_routers(dispatcher)
    await setup_bot_commands(bot, settings.admin_ids)

    scheduler = create_scheduler(container)
    scheduler.start()

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
