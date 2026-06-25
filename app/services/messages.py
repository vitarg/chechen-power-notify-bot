from __future__ import annotations

from datetime import date

from app.db.models import Notification, OutageSegment, UserAddress

MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def format_segment_message(
    segment: OutageSegment,
    address_titles: list[str],
    *,
    kind: str = "Плановое отключение",
) -> str:
    addresses = ", ".join(address_titles)
    address_line = "Затронутые адреса" if len(address_titles) > 1 else "Адрес"
    return (
        f"{kind}\n\n"
        f"{address_line}: {addresses}\n"
        f"Зона: {segment.raw_zone}\n"
        f"Дата: {format_date(segment.event_date)}\n"
        f"Время: {segment.starts_at:%H:%M}-{segment.ends_at:%H:%M}\n\n"
        "Источник: Чеченэнерго"
    )


def format_address_confirmation(address: UserAddress | None, parsed_text: str, fields: dict[str, str | None]) -> str:
    del address
    lines = ["Я понял адрес так:"]
    lines.append(f"Населенный пункт: {fields.get('locality') or 'не распознан'}")
    lines.append(f"Улица: {fields.get('street') or 'не распознана'}")
    lines.append("")
    if fields.get("confidence") in {"low", "medium"}:
        lines.append("Так можно сохранить, но уведомления могут быть шире, чем ожидается.")
    lines.append(f"Исходный адрес: {parsed_text}")
    return "\n".join(lines)


def format_date(value: date) -> str:
    return f"{value.day} {MONTHS[value.month]} {value.year}"


def format_history_item(notification: Notification) -> str:
    return (
        f"{notification.sent_at:%d.%m.%Y %H:%M} - "
        f"{notification.notification_type} - адреса: {', '.join(notification.address_titles)}"
    )

