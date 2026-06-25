from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum


class AddressConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationType(StrEnum):
    INITIAL = "initial"
    REMINDER = "reminder"
    UPDATE = "update"
    BACKFILL = "backfill"


class SegmentStatus(StrEnum):
    ACTIVE = "active"


class SourceCheckStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class BroadcastStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class NormalizedAddress:
    raw_text: str
    normalized_text: str
    district: str | None
    locality: str | None
    street: str | None
    landmark: str | None
    confidence: AddressConfidence


@dataclass(frozen=True)
class ParsedEvent:
    external_id: str
    title: str
    url: str
    rest_url: str | None
    published_at: datetime | None
    modified_at: datetime | None
    event_date: date
    raw_text: str
    content_hash: str
    segments: list[ParsedOutageSegment] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedOutageSegment:
    event_date: date
    starts_at: time
    ends_at: time
    raw_zone: str
    normalized_zone: str
    district: str | None
    locality: str | None
    streets: list[str]
    landmarks: list[str]
    segment_hash: str


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    reason: str
    score: float = 0.0

