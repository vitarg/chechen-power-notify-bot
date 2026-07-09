from __future__ import annotations

import re
from datetime import date, datetime, time
from html import unescape
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.domain import ParsedEvent, ParsedOutageSegment
from app.utils.text import comparable_name, normalize_text, split_csv_like, stable_hash

TIME_RE = re.compile(
    r"(?:с|c)\s*(?P<start>\d{1,2})[.:](?P<start_min>\d{2})\s*"
    r"(?:до|-)\s*(?P<end>\d{1,2})[.:](?P<end_min>\d{2})",
    re.IGNORECASE,
)
DISTRICT_RE = re.compile(r"(?P<district>[А-Яа-яЁё\-\s]+?район)\b")
LOCALITY_RE = re.compile(
    r"(?:част(?:ь|ично)\s+)?(?:г\.|с\.|пос\.)\s*(?P<locality>[А-Яа-яЁё\-\s]+?)(?=[:;,)]|$)"
)
SETTLEMENT_RE = re.compile(
    r"(?:част(?:ь|ично)\s+)?(?:г\.|с\.|пос\.|п\.)\s*(?P<locality>[А-Яа-яЁё\-\s]+?)(?=[:;,)]|$)"
)
STREET_MARKER_RE = re.compile(r"(?:улицы|ул\.|пер-ки|пер\.|пр\.|б-р)", re.IGNORECASE)


class ChechenenergoClient:
    def __init__(
        self,
        api_url: str,
        *,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_url = api_url
        self.timeout = timeout
        self._client = client

    async def fetch_events(self, start_date: date, end_date: date) -> list[ParsedEvent]:
        close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
            close_client = True

        try:
            return await self._fetch_events(client, start_date, end_date)
        finally:
            if close_client:
                await client.aclose()

    async def _fetch_events(
        self,
        client: httpx.AsyncClient,
        start_date: date,
        end_date: date,
    ) -> list[ParsedEvent]:
        page = 1
        events: list[ParsedEvent] = []
        while True:
            response = await client.get(
                self.api_url,
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "per_page": 50,
                    "page": page,
                },
            )
            response.raise_for_status()
            payload = response.json()
            raw_events = payload.get("events") or []
            for raw_event in raw_events:
                if not raw_event.get("description") and raw_event.get("url"):
                    raw_event["description"] = await fetch_detail_description(client, str(raw_event["url"]))
                events.append(parse_event_payload(raw_event))

            total_pages = _safe_int(payload.get("total_pages"))
            if not raw_events or (total_pages is not None and page >= total_pages):
                break
            page += 1
        return events


def parse_event_payload(payload: dict[str, Any]) -> ParsedEvent:
    external_id = str(payload["id"])
    title = str(payload.get("title") or "")
    url = str(payload.get("url") or "")
    rest_url = payload.get("rest_url")
    raw_description = str(payload.get("description") or "")
    raw_text = html_to_text(raw_description)
    event_date = _parse_event_date(payload)
    content_hash = stable_hash(title, raw_text, event_date.isoformat())
    segments = parse_segments(event_date, raw_text)
    return ParsedEvent(
        external_id=external_id,
        title=title,
        url=url,
        rest_url=str(rest_url) if rest_url else None,
        published_at=_parse_datetime(payload.get("date_utc") or payload.get("date")),
        modified_at=_parse_datetime(payload.get("modified_utc") or payload.get("modified")),
        event_date=event_date,
        raw_text=raw_text,
        content_hash=content_hash,
        segments=segments,
    )


async def fetch_detail_description(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    description = soup.select_one(".tribe-events-single-event-description")
    if description is None:
        return ""
    return str(description)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(unescape(html), "lxml")
    paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in soup.find_all("p")]
    if paragraphs:
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)
    return soup.get_text("\n", strip=True)


def parse_segments(event_date: date, text: str) -> list[ParsedOutageSegment]:
    pieces: list[str] = []
    for paragraph in [part.strip() for part in text.splitlines() if part.strip()]:
        matches = list(TIME_RE.finditer(paragraph))
        if len(matches) <= 1:
            pieces.append(paragraph)
            continue
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(paragraph)
            pieces.append(paragraph[match.start() : end].strip(" ;"))

    segments = []
    for piece in pieces:
        match = TIME_RE.search(piece)
        if not match:
            continue
        starts_at = time(int(match.group("start")), int(match.group("start_min")))
        ends_at = time(int(match.group("end")), int(match.group("end_min")))
        zone_text = piece[match.end() :].strip(" -–—:;")
        district = _extract_district(zone_text)
        locality = _extract_locality(zone_text)
        streets = _extract_streets(zone_text)
        landmarks = _extract_landmarks(zone_text, locality)
        normalized_zone = normalize_text(zone_text)
        segments.append(
            ParsedOutageSegment(
                event_date=event_date,
                starts_at=starts_at,
                ends_at=ends_at,
                raw_zone=zone_text,
                normalized_zone=normalized_zone,
                district=comparable_name(district),
                locality=comparable_name(locality),
                streets=streets,
                landmarks=landmarks,
                segment_hash=stable_hash(
                    event_date.isoformat(),
                    starts_at.isoformat(timespec="minutes"),
                    ends_at.isoformat(timespec="minutes"),
                    normalized_zone,
                ),
            )
        )
    return segments


def _extract_district(text: str) -> str | None:
    match = DISTRICT_RE.search(text)
    return match.group("district").strip() if match else None


def _extract_locality(text: str) -> str | None:
    match = LOCALITY_RE.search(text)
    if match:
        return _normalize_locality_form(match.group("locality").strip())
    normalized = normalize_text(text)
    if "грозного" in normalized or "грозный" in normalized:
        return "Грозный"
    if "гудермеса" in normalized or "гудермес" in normalized:
        return "Гудермес"
    return None


def _extract_streets(text: str) -> list[str]:
    if not STREET_MARKER_RE.search(text):
        return []
    normalized = re.sub(r"^.*?:", "", text, count=1).replace(";", ",")
    candidates = []
    for piece in split_csv_like(normalized):
        if not STREET_MARKER_RE.search(piece):
            continue
        cleaned = re.sub(r"^.*?(улицы|ул\.|пер-ки|пер\.|пр\.|б-р\.?)\s*", "", piece, count=1, flags=re.I)
        cleaned = re.sub(r"\s+и\s+.*$", "", cleaned, count=1, flags=re.I)
        cleaned = cleaned.strip(" .;:-")
        if not cleaned:
            continue
        lowered = normalize_text(cleaned)
        if any(marker in lowered for marker in ["район", "часть г", "сзо"]):
            continue
        parenthesized = re.findall(r"\(([^)]+)\)", cleaned)
        base_name = re.sub(r"\s*\([^)]*\)", "", cleaned).strip(" .;:-")
        for value in [base_name, *parenthesized]:
            normalized_value = comparable_name(value)
            if normalized_value and normalized_value != "частично":
                candidates.append(normalized_value)
    return candidates


def _extract_landmarks(text: str, primary_locality: str | None) -> list[str]:
    primary = comparable_name(primary_locality)
    landmarks = []
    for match in SETTLEMENT_RE.finditer(text):
        locality = comparable_name(_normalize_locality_form(match.group("locality").strip()))
        if locality and locality != primary:
            landmarks.append(locality)

    for piece in split_csv_like(re.sub(r"^.*?:", "", text, count=1)):
        if STREET_MARKER_RE.search(piece):
            continue
        cleaned = piece.strip(" .;:-")
        if not cleaned:
            continue
        if "район" in normalize_text(cleaned):
            continue
        base_name = re.sub(r"\s*\([^)]*\)", "", cleaned).strip(" .;:-")
        parenthesized = re.findall(r"\(([^)]+)\)", cleaned)
        for value in [base_name, *parenthesized]:
            value = re.sub(r"^част(?:ь|ично)\s+", "", value.strip(), count=1, flags=re.I)
            normalized_value = comparable_name(value)
            if normalized_value and normalized_value not in {primary, "частично"}:
                landmarks.append(normalized_value)

    return list(dict.fromkeys(landmarks))


def _normalize_locality_form(value: str) -> str:
    comparable = comparable_name(value)
    if comparable == "грозного":
        return "Грозный"
    if comparable == "гудермеса":
        return "Гудермес"
    return value


def _parse_event_date(payload: dict[str, Any]) -> date:
    details = payload.get("start_date_details") or {}
    if details.get("year") and details.get("month") and details.get("day"):
        return date(int(details["year"]), int(details["month"]), int(details["day"]))
    start_date = str(payload.get("start_date") or "")
    return datetime.fromisoformat(start_date).date()


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
