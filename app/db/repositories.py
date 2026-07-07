from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Broadcast,
    Notification,
    Outage,
    OutageSegment,
    OutageVersion,
    SourceCheck,
    User,
    UserAddress,
)
from app.domain import NotificationType, ParsedEvent, ParsedOutageSegment, SourceCheckStatus
from app.matching.address import parse_user_address
from app.matching.matcher import match_address_to_segment


async def upsert_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    first_name: str | None,
    username: str | None,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, first_name=first_name, username=username)
        session.add(user)
        await session.flush()
        return user
    user.first_name = first_name
    user.username = username
    user.is_active = True
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def add_user_address(
    session: AsyncSession,
    *,
    user: User,
    title: str,
    raw_text: str,
) -> UserAddress:
    parsed = parse_user_address(raw_text)
    address = UserAddress(
        user_id=user.id,
        title=title,
        raw_text=parsed.raw_text,
        normalized_text=parsed.normalized_text,
        district=parsed.district,
        locality=parsed.locality,
        street=parsed.street,
        landmark=parsed.landmark,
        confidence=parsed.confidence.value,
    )
    session.add(address)
    await session.flush()
    return address


async def list_user_addresses(session: AsyncSession, telegram_id: int) -> list[UserAddress]:
    result = await session.scalars(
        select(UserAddress)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(UserAddress.created_at)
    )
    return list(result)


async def delete_user_address(session: AsyncSession, telegram_id: int, address_id: int) -> bool:
    address = await session.scalar(
        select(UserAddress).join(User).where(User.telegram_id == telegram_id, UserAddress.id == address_id)
    )
    if address is None:
        return False
    await session.delete(address)
    return True


async def delete_user(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(delete(User).where(User.telegram_id == telegram_id))
    return bool(result.rowcount)


async def get_all_active_users(session: AsyncSession) -> list[User]:
    result = await session.scalars(select(User).where(User.is_active.is_(True)))
    return list(result)


async def upsert_outage_event(session: AsyncSession, event: ParsedEvent) -> tuple[Outage, list[OutageSegment], bool]:
    outage = await session.scalar(
        select(Outage)
        .where(Outage.external_id == event.external_id)
        .options(selectinload(Outage.segments))
    )
    created = outage is None
    if outage is None:
        outage = Outage(
            external_id=event.external_id,
            title=event.title,
            source_url=event.url,
            rest_url=event.rest_url,
            event_date=event.event_date,
            published_at=event.published_at,
            modified_at=event.modified_at,
            raw_text=event.raw_text,
            content_hash=event.content_hash,
            current_version=1,
        )
        session.add(outage)
        await session.flush()
        session.add(
            OutageVersion(
                outage_id=outage.id,
                version=1,
                content_hash=event.content_hash,
                raw_text=event.raw_text,
                payload={"title": event.title, "url": event.url},
            )
        )
    elif outage.content_hash != event.content_hash:
        outage.current_version += 1
        outage.title = event.title
        outage.source_url = event.url
        outage.rest_url = event.rest_url
        outage.event_date = event.event_date
        outage.modified_at = event.modified_at
        outage.raw_text = event.raw_text
        outage.content_hash = event.content_hash
        session.add(
            OutageVersion(
                outage_id=outage.id,
                version=outage.current_version,
                content_hash=event.content_hash,
                raw_text=event.raw_text,
                payload={"title": event.title, "url": event.url},
            )
        )

    existing_by_hash = {} if created else {segment.segment_hash: segment for segment in outage.segments}
    new_or_changed_segments = []
    for parsed_segment in event.segments:
        segment = existing_by_hash.get(parsed_segment.segment_hash)
        if segment is None:
            segment = _build_segment(outage.id, parsed_segment, outage.current_version)
            session.add(segment)
            await session.flush()
            new_or_changed_segments.append(segment)
        elif created:
            new_or_changed_segments.append(segment)

    return outage, new_or_changed_segments, created


async def find_matching_addresses(
    session: AsyncSession,
    segment: OutageSegment | ParsedOutageSegment,
) -> dict[User, list[UserAddress]]:
    result = await session.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .options(selectinload(User.addresses))
    )
    matches: dict[User, list[UserAddress]] = defaultdict(list)
    parsed_segment = _segment_to_domain(segment)
    for user in result:
        for address in user.addresses:
            normalized = parse_user_address(address.raw_text)
            match = match_address_to_segment(normalized, parsed_segment)
            if match.matched:
                matches[user].append(address)
    return matches


async def create_notification(
    session: AsyncSession,
    *,
    user_id: int,
    segment_id: int,
    notification_type: NotificationType,
    segment_version: int,
    address_titles: list[str],
) -> Notification | None:
    existing = await session.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.outage_segment_id == segment_id,
            Notification.notification_type == notification_type.value,
            Notification.segment_version == segment_version,
        )
    )
    if existing:
        return None
    notification = Notification(
        user_id=user_id,
        outage_segment_id=segment_id,
        notification_type=notification_type.value,
        segment_version=segment_version,
        address_titles=address_titles,
    )
    session.add(notification)
    await session.flush()
    return notification


async def active_segments_for_date(session: AsyncSession, target_date: date) -> list[OutageSegment]:
    result = await session.scalars(
        select(OutageSegment)
        .where(OutageSegment.event_date == target_date, OutageSegment.status == "active")
        .options(selectinload(OutageSegment.outage))
    )
    return list(result)


async def future_segments(session: AsyncSession, from_date: date) -> list[OutageSegment]:
    result = await session.scalars(
        select(OutageSegment)
        .where(OutageSegment.event_date >= from_date, OutageSegment.status == "active")
        .options(selectinload(OutageSegment.outage))
        .order_by(OutageSegment.event_date, OutageSegment.starts_at)
    )
    return list(result)


async def user_history(session: AsyncSession, telegram_id: int, limit: int = 10) -> list[Notification]:
    result = await session.scalars(
        select(Notification)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Notification.sent_at.desc())
        .limit(limit)
    )
    return list(result)


async def latest_outages(session: AsyncSession, limit: int = 10) -> list[Outage]:
    result = await session.scalars(select(Outage).order_by(Outage.created_at.desc()).limit(limit))
    return list(result)


async def stats(session: AsyncSession) -> dict[str, int]:
    return {
        "users": await session.scalar(select(func.count(User.id))) or 0,
        "addresses": await session.scalar(select(func.count(UserAddress.id))) or 0,
        "outages": await session.scalar(select(func.count(Outage.id))) or 0,
        "segments": await session.scalar(select(func.count(OutageSegment.id))) or 0,
        "notifications": await session.scalar(select(func.count(Notification.id))) or 0,
    }


async def record_source_success(session: AsyncSession) -> SourceCheck:
    now = datetime.now().astimezone()
    check = SourceCheck(
        status=SourceCheckStatus.SUCCESS.value,
        checked_at=now,
        last_success_at=now,
        consecutive_errors=0,
    )
    session.add(check)
    await session.flush()
    return check


async def record_source_error(session: AsyncSession, error_message: str) -> SourceCheck:
    last = await session.scalar(select(SourceCheck).order_by(SourceCheck.checked_at.desc()).limit(1))
    consecutive_errors = (last.consecutive_errors if last else 0) + 1
    last_success_at = last.last_success_at if last else None
    check = SourceCheck(
        status=SourceCheckStatus.ERROR.value,
        checked_at=datetime.now().astimezone(),
        last_success_at=last_success_at,
        error_message=error_message[:4000],
        consecutive_errors=consecutive_errors,
    )
    session.add(check)
    await session.flush()
    return check


async def last_source_check(session: AsyncSession) -> SourceCheck | None:
    return await session.scalar(select(SourceCheck).order_by(SourceCheck.checked_at.desc()).limit(1))


async def cleanup_old_data(session: AsyncSession, older_than_days: int = 90) -> None:
    cutoff = datetime.now().astimezone() - timedelta(days=older_than_days)
    await session.execute(delete(Notification).where(Notification.created_at < cutoff))
    await session.execute(delete(OutageVersion).where(OutageVersion.created_at < cutoff))
    await session.execute(delete(SourceCheck).where(SourceCheck.created_at < cutoff))
    await session.execute(delete(Outage).where(Outage.created_at < cutoff))


async def create_broadcast(session: AsyncSession, admin_telegram_id: int, text: str) -> Broadcast:
    broadcast = Broadcast(admin_telegram_id=admin_telegram_id, text=text)
    session.add(broadcast)
    await session.flush()
    return broadcast


def _build_segment(
    outage_id: int,
    parsed_segment: ParsedOutageSegment,
    version: int,
) -> OutageSegment:
    return OutageSegment(
        outage_id=outage_id,
        event_date=parsed_segment.event_date,
        starts_at=parsed_segment.starts_at,
        ends_at=parsed_segment.ends_at,
        raw_zone=parsed_segment.raw_zone,
        normalized_zone=parsed_segment.normalized_zone,
        district=parsed_segment.district,
        locality=parsed_segment.locality,
        streets=parsed_segment.streets,
        landmarks=parsed_segment.landmarks,
        segment_hash=parsed_segment.segment_hash,
        version=version,
    )


def _segment_to_domain(segment: OutageSegment | ParsedOutageSegment) -> ParsedOutageSegment:
    if isinstance(segment, ParsedOutageSegment):
        return segment
    return ParsedOutageSegment(
        event_date=segment.event_date,
        starts_at=segment.starts_at,
        ends_at=segment.ends_at,
        raw_zone=segment.raw_zone,
        normalized_zone=segment.normalized_zone,
        district=segment.district,
        locality=segment.locality,
        streets=segment.streets,
        landmarks=segment.landmarks,
        segment_hash=segment.segment_hash,
    )
