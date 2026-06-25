from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    addresses: Mapped[list[UserAddress]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserAddress(TimestampMixin, Base):
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(80))
    raw_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(String(255), index=True)
    locality: Mapped[str | None] = mapped_column(String(255), index=True)
    street: Mapped[str | None] = mapped_column(String(255), index=True)
    landmark: Mapped[str | None] = mapped_column(String(255), index=True)
    confidence: Mapped[str] = mapped_column(String(20))

    user: Mapped[User] = relationship(back_populates="addresses")


class Outage(TimestampMixin, Base):
    __tablename__ = "outages"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), default="chechenenergo")
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(Text)
    rest_url: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    current_version: Mapped[int] = mapped_column(default=1, server_default="1")

    segments: Mapped[list[OutageSegment]] = relationship(
        back_populates="outage",
        cascade="all, delete-orphan",
    )


class OutageSegment(TimestampMixin, Base):
    __tablename__ = "outage_segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    outage_id: Mapped[int] = mapped_column(ForeignKey("outages.id", ondelete="CASCADE"), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)
    raw_zone: Mapped[str] = mapped_column(Text)
    normalized_zone: Mapped[str] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(String(255), index=True)
    locality: Mapped[str | None] = mapped_column(String(255), index=True)
    streets: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    landmarks: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    segment_hash: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")

    outage: Mapped[Outage] = relationship(back_populates="segments")

    __table_args__ = (
        Index("ix_outage_segments_outage_hash", "outage_id", "segment_hash", unique=True),
    )


class OutageVersion(TimestampMixin, Base):
    __tablename__ = "outage_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    outage_id: Mapped[int] = mapped_column(ForeignKey("outages.id", ondelete="CASCADE"), index=True)
    outage_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("outage_segments.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column()
    content_hash: Mapped[str] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    outage_segment_id: Mapped[int] = mapped_column(
        ForeignKey("outage_segments.id", ondelete="CASCADE"),
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(20))
    segment_version: Mapped[int] = mapped_column(default=1, server_default="1")
    address_titles: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_notifications_segment_delivery",
            "user_id",
            "outage_segment_id",
            "notification_type",
            "segment_version",
            unique=True,
        ),
    )


class SourceCheck(TimestampMixin, Base):
    __tablename__ = "source_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), default="chechenenergo", index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    consecutive_errors: Mapped[int] = mapped_column(default=0, server_default="0")


class Broadcast(TimestampMixin, Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    sent_count: Mapped[int] = mapped_column(default=0, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

