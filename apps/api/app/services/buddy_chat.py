"""Atomic persistence helpers for Buddy conversations and messages."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BuddyConversation,
    BuddyMatch,
    BuddyMessage,
    MatchStatus,
    buddy_message_expires_at,
    validate_buddy_message_body,
)

Clock = Callable[[], datetime]


class BuddyConversationPersistenceReason(StrEnum):
    """Sanitized conversation persistence rejection reasons."""

    ACTIVE_MATCH_REQUIRED = "CHAT_ACTIVE_MATCH_REQUIRED"


class BuddyConversationPersistenceError(RuntimeError):
    """Raised when a conversation cannot derive from an ACTIVE Match."""

    def __init__(self, reason: BuddyConversationPersistenceReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class BuddyMessagePersistenceReason(StrEnum):
    """Sanitized message persistence rejection reasons."""

    ACTIVE_CONVERSATION_REQUIRED = "CHAT_ACTIVE_CONVERSATION_REQUIRED"
    SENDER_NOT_PARTICIPANT = "CHAT_SENDER_NOT_PARTICIPANT"


class BuddyMessagePersistenceError(RuntimeError):
    """Raised without content or participant details when persistence is denied."""

    def __init__(self, reason: BuddyMessagePersistenceReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Buddy message timestamp must be timezone-aware.")
    return value.astimezone(UTC)


async def get_or_create_buddy_conversation(
    session: AsyncSession,
    *,
    match_id: UUID,
    clock: Clock = _system_utc_now,
) -> BuddyConversation:
    """Atomically return the one conversation for an authoritative ACTIVE Match.

    The helper flushes through one PostgreSQL ``ON CONFLICT`` statement and never
    commits, so INV-005 can compose it with Match activation in one transaction.
    """
    buddy_match = await session.scalar(
        select(BuddyMatch).where(
            BuddyMatch.id == match_id,
            BuddyMatch.status == MatchStatus.ACTIVE,
            BuddyMatch.deleted_at.is_(None),
        )
    )
    if buddy_match is None:
        raise BuddyConversationPersistenceError(
            BuddyConversationPersistenceReason.ACTIVE_MATCH_REQUIRED
        )

    created_at = _utc_now(clock)
    statement = (
        insert(BuddyConversation)
        .values(
            match_id=buddy_match.id,
            semester_id=buddy_match.semester_id,
            created_at=created_at,
        )
        .on_conflict_do_nothing(index_elements=[BuddyConversation.match_id])
        .returning(BuddyConversation)
    )
    conversation = await session.scalar(statement)
    if conversation is not None:
        return conversation

    existing = await session.scalar(
        select(BuddyConversation).where(BuddyConversation.match_id == buddy_match.id)
    )
    if existing is None:  # pragma: no cover - protects against external transaction misuse.
        raise BuddyConversationPersistenceError(
            BuddyConversationPersistenceReason.ACTIVE_MATCH_REQUIRED
        )
    return existing


async def persist_buddy_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_sender_id: UUID,
    body: str,
    clock: Clock = _system_utc_now,
) -> BuddyMessage:
    """Persist one message for a backend-authenticated ACTIVE Match participant.

    Future transports must pass the authenticated principal, never a sender identity
    accepted from request content. PostgreSQL repeats this membership check in a
    trigger so direct writes cannot bypass the invariant.
    """
    validated_body = validate_buddy_message_body(body)
    buddy_match = await session.scalar(
        select(BuddyMatch)
        .join(BuddyConversation, BuddyConversation.match_id == BuddyMatch.id)
        .where(
            BuddyConversation.id == conversation_id,
            BuddyMatch.status == MatchStatus.ACTIVE,
            BuddyMatch.deleted_at.is_(None),
        )
    )
    if buddy_match is None:
        raise BuddyMessagePersistenceError(
            BuddyMessagePersistenceReason.ACTIVE_CONVERSATION_REQUIRED
        )
    if authenticated_sender_id not in {
        buddy_match.participant_one_user_id,
        buddy_match.participant_two_user_id,
    }:
        raise BuddyMessagePersistenceError(BuddyMessagePersistenceReason.SENDER_NOT_PARTICIPANT)

    created_at = _utc_now(clock)
    message = BuddyMessage(
        conversation_id=conversation_id,
        sender_id=authenticated_sender_id,
        body=validated_body,
        created_at=created_at,
        expires_at=buddy_message_expires_at(created_at),
    )
    session.add(message)
    await session.flush()
    return message
