"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)

    op.create_table(
        "outages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("rest_url", sa.Text(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outages_external_id"), "outages", ["external_id"], unique=True)
    op.create_index(op.f("ix_outages_event_date"), "outages", ["event_date"], unique=False)
    op.create_index(op.f("ix_outages_content_hash"), "outages", ["content_hash"], unique=False)

    op.create_table(
        "source_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("consecutive_errors", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_checks_source"), "source_checks", ["source"], unique=False)
    op.create_index(op.f("ix_source_checks_status"), "source_checks", ["status"], unique=False)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("sent_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_broadcasts_admin_telegram_id"), "broadcasts", ["admin_telegram_id"], unique=False)

    op.create_table(
        "user_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("district", sa.String(length=255), nullable=True),
        sa.Column("locality", sa.String(length=255), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_addresses_user_id"), "user_addresses", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_addresses_district"), "user_addresses", ["district"], unique=False)
    op.create_index(op.f("ix_user_addresses_locality"), "user_addresses", ["locality"], unique=False)
    op.create_index(op.f("ix_user_addresses_street"), "user_addresses", ["street"], unique=False)
    op.create_index(op.f("ix_user_addresses_landmark"), "user_addresses", ["landmark"], unique=False)

    op.create_table(
        "outage_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outage_id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=False),
        sa.Column("ends_at", sa.Time(), nullable=False),
        sa.Column("raw_zone", sa.Text(), nullable=False),
        sa.Column("normalized_zone", sa.Text(), nullable=False),
        sa.Column("district", sa.String(length=255), nullable=True),
        sa.Column("locality", sa.String(length=255), nullable=True),
        sa.Column("streets", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("landmarks", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("segment_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["outage_id"], ["outages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outage_segments_outage_id"), "outage_segments", ["outage_id"], unique=False)
    op.create_index(op.f("ix_outage_segments_event_date"), "outage_segments", ["event_date"], unique=False)
    op.create_index(op.f("ix_outage_segments_district"), "outage_segments", ["district"], unique=False)
    op.create_index(op.f("ix_outage_segments_locality"), "outage_segments", ["locality"], unique=False)
    op.create_index(op.f("ix_outage_segments_segment_hash"), "outage_segments", ["segment_hash"], unique=False)
    op.create_index(
        "ix_outage_segments_outage_hash",
        "outage_segments",
        ["outage_id", "segment_hash"],
        unique=True,
    )

    op.create_table(
        "outage_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outage_id", sa.Integer(), nullable=False),
        sa.Column("outage_segment_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["outage_id"], ["outages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outage_segment_id"], ["outage_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outage_versions_outage_id"), "outage_versions", ["outage_id"], unique=False)
    op.create_index(
        op.f("ix_outage_versions_outage_segment_id"),
        "outage_versions",
        ["outage_segment_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("outage_segment_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=20), nullable=False),
        sa.Column("segment_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("address_titles", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["outage_segment_id"], ["outage_segments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_notifications_outage_segment_id"),
        "notifications",
        ["outage_segment_id"],
        unique=False,
    )
    op.create_index(
        "uq_notifications_segment_delivery",
        "notifications",
        ["user_id", "outage_segment_id", "notification_type", "segment_version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("outage_versions")
    op.drop_table("outage_segments")
    op.drop_table("user_addresses")
    op.drop_table("broadcasts")
    op.drop_table("source_checks")
    op.drop_table("outages")
    op.drop_table("users")

