"""Durable one-to-one Buddy conversation and plain-text message persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

MAX_BUDDY_MESSAGE_CODE_POINTS: Final = 10_000
BUDDY_MESSAGE_MAX_RETENTION_DAYS: Final = 90
BUDDY_MESSAGE_READ_RETENTION_DAYS: Final = 30
BUDDY_MESSAGE_MAX_RETENTION: Final = timedelta(days=BUDDY_MESSAGE_MAX_RETENTION_DAYS)
BUDDY_MESSAGE_READ_RETENTION: Final = timedelta(days=BUDDY_MESSAGE_READ_RETENTION_DAYS)


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value


def buddy_message_expires_at(created_at: datetime) -> datetime:
    """Return the deterministic never-read retention deadline."""
    return _require_aware(created_at, field_name="Buddy message creation time") + (
        BUDDY_MESSAGE_MAX_RETENTION
    )


def validate_buddy_message_body(body: str) -> str:
    """Validate the persistence boundary without changing plain-text content."""
    if not body.strip():
        raise ValueError("Buddy message body must not be blank.")
    if len(body) > MAX_BUDDY_MESSAGE_CODE_POINTS:
        raise ValueError("Buddy message body exceeds the persisted code-point limit.")
    return body


class BuddyConversation(Base):
    """The single durable conversation derived from one authoritative ACTIVE Match."""

    __tablename__ = "buddy_conversations"
    # Conversations have no edit/delete lifecycle. Semester reset deletes the Match and
    # reaches this row through the database cascade.
    updated_at = None  # type: ignore[assignment]
    deleted_at = None

    match_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.matches.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # SEM-001 owns the semesters table, backfill, and FK. Until then this mirrors
    # the nullable Match linkage without inventing another cohort authority.
    semester_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class BuddyMessage(Base):
    """An immutable plain-text message with first-read retention metadata."""

    __tablename__ = "buddy_messages"
    __table_args__ = (
        CheckConstraint(
            f"body ~ '[^[:space:]]' AND char_length(body) <= {MAX_BUDDY_MESSAGE_CODE_POINTS}",
            name="ck_buddy_messages_body_length",
        ),
        CheckConstraint(
            "(read_at IS NULL "
            "AND expires_at = created_at + INTERVAL '90 days') "
            "OR (read_at IS NOT NULL "
            "AND read_at >= created_at "
            "AND expires_at = LEAST("
            "read_at + INTERVAL '30 days', "
            "created_at + INTERVAL '90 days'))",
            name="ck_buddy_messages_retention_timestamps",
        ),
        Index(
            "ix_buddy_messages_conversation_created_at_id",
            "conversation_id",
            "created_at",
            "id",
        ),
        Index("ix_buddy_messages_expires_at", "expires_at"),
        Index("ix_buddy_messages_sender_id", "sender_id"),
    )

    # Message content and ownership are append-only. Only read_at/expires_at are
    # mutable, through the column-level runtime grants used by CHAT-002.
    updated_at = None  # type: ignore[assignment]
    deleted_at = None

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{APPLICATION_SCHEMA}.buddy_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sender_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("(now() + INTERVAL '90 days')"),
    )

    @validates("body")
    def validate_body(self, _key: str, value: str) -> str:
        return validate_buddy_message_body(value)

    @validates("created_at", "read_at", "expires_at")
    def validate_aware_datetime(
        self,
        key: str,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None:
            _require_aware(value, field_name=key.replace("_", " ").title())
        return value
