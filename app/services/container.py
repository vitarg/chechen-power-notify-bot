from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    bot: Bot

