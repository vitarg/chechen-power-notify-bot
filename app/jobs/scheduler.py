from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.container import AppContainer
from app.services.sync import SyncService

logger = logging.getLogger(__name__)


def create_scheduler(container: AppContainer) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=container.settings.timezone)
    sync_service = SyncService(
        settings=container.settings,
        session_factory=container.session_factory,
        bot=container.bot,
    )
    scheduler.add_job(
        sync_service.sync,
        CronTrigger(day_of_week="mon-fri", hour="10-18", minute=0, timezone=container.settings.timezone),
        kwargs={"dry_run": False},
        id="source_sync",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        sync_service.send_today_reminders,
        CronTrigger(hour=8, minute=0, timezone=container.settings.timezone),
        id="daily_reminders",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        _cleanup,
        CronTrigger(hour=3, minute=15, timezone=container.settings.timezone),
        args=[container],
        id="cleanup",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler


async def _cleanup(container: AppContainer) -> None:
    from app.db import repositories as repo

    async with container.session_factory() as session:
        await repo.cleanup_old_data(session, older_than_days=90)
        await session.commit()
    logger.info("Old data cleanup completed")

