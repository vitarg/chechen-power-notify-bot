from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db import repositories as repo
from app.db.models import OutageSegment, User, UserAddress
from app.domain import NotificationType, ParsedOutageSegment
from app.services.messages import format_segment_message
from app.sources.chechenenergo import ChechenenergoClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncResult:
    events_found: int
    segments_found: int
    notifications_sent: int
    dry_run: bool = False
    error: str | None = None


class SyncService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.bot = bot
        self.source = ChechenenergoClient(settings.source_api_url)

    async def sync(self, *, dry_run: bool = False) -> SyncResult:
        today = datetime.now(self.settings.tz).date()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=self.settings.lookahead_days)
        try:
            events = await self.source.fetch_events(start_date, end_date)
        except Exception as exc:
            logger.exception("Source sync failed")
            async with self.session_factory() as session:
                check = await repo.record_source_error(session, str(exc))
                await session.commit()
            if check.consecutive_errors >= self.settings.error_alert_threshold:
                await self._notify_admins_about_source_error(str(exc), check.consecutive_errors)
            return SyncResult(0, 0, 0, dry_run=dry_run, error=str(exc))

        if dry_run:
            async with self.session_factory() as session:
                notifications = 0
                for event in events:
                    for segment in event.segments:
                        matches = await self._find_matches_for_parsed_segment(session, segment)
                        notifications += len(matches)
            return SyncResult(
                events_found=len(events),
                segments_found=sum(len(event.segments) for event in events),
                notifications_sent=notifications,
                dry_run=True,
            )

        sent = 0
        async with self.session_factory() as session:
            for event in events:
                _outage, changed_segments, created = await repo.upsert_outage_event(session, event)
                notification_type = NotificationType.INITIAL if created else NotificationType.UPDATE
                for segment in changed_segments:
                    sent += await self._send_segment_notifications(session, segment, notification_type)
            await repo.record_source_success(session)
            await session.commit()

        return SyncResult(
            events_found=len(events),
            segments_found=sum(len(event.segments) for event in events),
            notifications_sent=sent,
        )

    async def send_today_reminders(self) -> int:
        today = datetime.now(self.settings.tz).date()
        sent = 0
        async with self.session_factory() as session:
            segments = await repo.active_segments_for_date(session, today)
            for segment in segments:
                sent += await self._send_segment_notifications(session, segment, NotificationType.REMINDER)
            await session.commit()
        return sent

    async def notify_known_segments_for_user(self, telegram_id: int) -> int:
        today = datetime.now(self.settings.tz).date()
        sent = 0
        async with self.session_factory() as session:
            user = await repo.get_user_by_telegram_id(session, telegram_id)
            if user is None:
                return 0
            segments = await repo.future_segments(session, today)
            for segment in segments:
                matches = await repo.find_matching_addresses(session, segment)
                addresses = matches.get(user, [])
                if addresses:
                    sent += await self._deliver_to_user(
                        session,
                        user,
                        segment,
                        addresses,
                        NotificationType.BACKFILL,
                    )
            await session.commit()
        return sent

    async def _send_segment_notifications(
        self,
        session: AsyncSession,
        segment: OutageSegment,
        notification_type: NotificationType,
    ) -> int:
        matches = await repo.find_matching_addresses(session, segment)
        sent = 0
        for user, addresses in matches.items():
            sent += await self._deliver_to_user(session, user, segment, addresses, notification_type)
        return sent

    async def _deliver_to_user(
        self,
        session: AsyncSession,
        user: User,
        segment: OutageSegment,
        addresses: list[UserAddress],
        notification_type: NotificationType,
    ) -> int:
        titles = [address.title for address in addresses]
        notification = await repo.create_notification(
            session,
            user_id=user.id,
            segment_id=segment.id,
            notification_type=notification_type,
            segment_version=segment.version,
            address_titles=titles,
        )
        if notification is None:
            return 0
        kind = {
            NotificationType.INITIAL: "Плановое отключение",
            NotificationType.REMINDER: "Напоминание о плановом отключении",
            NotificationType.UPDATE: "Обновление по плановому отключению",
            NotificationType.BACKFILL: "Уже известное плановое отключение",
        }[notification_type]
        await self.bot.send_message(user.telegram_id, format_segment_message(segment, titles, kind=kind))
        return 1

    async def _find_matches_for_parsed_segment(
        self,
        session: AsyncSession,
        segment: ParsedOutageSegment,
    ) -> dict[int, list[str]]:
        matches_by_user: dict[int, list[str]] = defaultdict(list)
        matches = await repo.find_matching_addresses(session, segment)
        for user, addresses in matches.items():
            matches_by_user[user.telegram_id].extend(address.title for address in addresses)
        return matches_by_user

    async def _notify_admins_about_source_error(self, error: str, consecutive_errors: int) -> None:
        text = (
            "Проблема с источником\n\n"
            "Сайт Чеченэнерго недоступен или изменилась структура страницы.\n"
            f"Ошибок подряд: {consecutive_errors}\n"
            f"Ошибка: {error[:1000]}"
        )
        for admin_id in self.settings.admin_ids:
            await self.bot.send_message(admin_id, text)
