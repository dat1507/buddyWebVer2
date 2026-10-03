"""Atomic persistence helpers for Buddy conversations and messages."""

from __future__ import annotations

import base64
import binascii
import struct
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final, cast
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BUDDY_MESSAGE_READ_RETENTION,
    BuddyConversation,
    BuddyMatch,
    BuddyMessage,
    MatchStatus,
    buddy_message_expires_at,
    validate_buddy_message_body,
)

Clock = Callable[[], datetime]
DEFAULT_CHAT_MESSAGE_PAGE_SIZE: Final = 50
MAX_CHAT_MESSAGE_PAGE_SIZE: Final = 100
_CURSOR_VERSION: Final = 1
_CURSOR_LENGTH: Final = 25
_UTC_EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)


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
    IDEMPOTENCY_KEY_REUSED = "CHAT_IDEMPOTENCY_KEY_REUSED"


class BuddyMessagePersistenceError(RuntimeError):
    """Raised without content or participant details when persistence is denied."""

    def __init__(self, reason: BuddyMessagePersistenceReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class BuddyChatReadReason(StrEnum):
    """Sanitized authorized-history/read acknowledgement rejection reasons."""

    CONVERSATION_NOT_FOUND = "CHAT_CONVERSATION_NOT_FOUND"
    MESSAGE_NOT_FOUND = "CHAT_MESSAGE_NOT_FOUND"
    INVALID_CURSOR = "CHAT_INVALID_CURSOR"


class BuddyChatReadError(RuntimeError):
    """Raised without disclosing whether a foreign conversation exists."""

    def __init__(self, reason: BuddyChatReadReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class BuddyMessagePage:
    """One chronological page and its opaque next-older cursor."""

    items: tuple[BuddyMessage, ...]
    next_before: str | None


@dataclass(frozen=True, slots=True)
class BuddyReadAcknowledgement:
    """Result of one bounded, atomic first-read update."""

    through_message_id: UUID
    marked_read_count: int


@dataclass(frozen=True, slots=True)
class BuddyUnreadConversation:
    """Authoritative unread count for one ACTIVE Buddy conversation."""

    conversation_id: UUID
    unread_count: int


@dataclass(frozen=True, slots=True)
class BuddyUnreadSummary:
    """Private unread totals derived only from effective persisted messages."""

    conversations: tuple[BuddyUnreadConversation, ...]
    total_unread_messages: int


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Buddy message timestamp must be timezone-aware.")
    return value.astimezone(UTC)


def _cursor_timestamp_microseconds(value: datetime) -> int:
    normalized = _utc_now(lambda: value)
    delta = normalized - _UTC_EPOCH
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def encode_buddy_message_cursor(created_at: datetime, message_id: UUID) -> str:
    """Encode the complete deterministic order tuple as an opaque URL-safe token."""
    raw = struct.pack(">Bq", _CURSOR_VERSION, _cursor_timestamp_microseconds(created_at))
    return base64.urlsafe_b64encode(raw + message_id.bytes).rstrip(b"=").decode("ascii")


def decode_buddy_message_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode only cursors issued by this version of the history contract."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
        if len(raw) != _CURSOR_LENGTH:
            raise ValueError
        version, microseconds = struct.unpack(">Bq", raw[:9])
        if version != _CURSOR_VERSION or microseconds < 0:
            raise ValueError
        created_at = _UTC_EPOCH + timedelta(microseconds=microseconds)
        return created_at, UUID(bytes=raw[9:])
    except (binascii.Error, OverflowError, ValueError):
        raise BuddyChatReadError(BuddyChatReadReason.INVALID_CURSOR) from None


async def _require_authorized_active_conversation(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_user_id: UUID,
) -> BuddyConversation:
    conversation = await session.scalar(
        select(BuddyConversation)
        .join(BuddyMatch, BuddyMatch.id == BuddyConversation.match_id)
        .where(
            BuddyConversation.id == conversation_id,
            BuddyMatch.status == MatchStatus.ACTIVE,
            BuddyMatch.deleted_at.is_(None),
            or_(
                BuddyMatch.participant_one_user_id == authenticated_user_id,
                BuddyMatch.participant_two_user_id == authenticated_user_id,
            ),
        )
    )
    if conversation is None:
        raise BuddyChatReadError(BuddyChatReadReason.CONVERSATION_NOT_FOUND)
    return conversation


async def authorize_buddy_conversation(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_user_id: UUID,
) -> BuddyConversation:
    """Expose the CHAT-002 ACTIVE-participant policy to realtime transports."""
    return await _require_authorized_active_conversation(
        session,
        conversation_id=conversation_id,
        authenticated_user_id=authenticated_user_id,
    )


async def list_active_buddy_conversation_ids(
    session: AsyncSession,
    *,
    authenticated_user_id: UUID,
) -> tuple[UUID, ...]:
    """Return every conversation the current USER may receive realtime events for."""
    return tuple(
        (
            await session.scalars(
                select(BuddyConversation.id)
                .join(BuddyMatch, BuddyMatch.id == BuddyConversation.match_id)
                .where(
                    BuddyMatch.status == MatchStatus.ACTIVE,
                    BuddyMatch.deleted_at.is_(None),
                    or_(
                        BuddyMatch.participant_one_user_id == authenticated_user_id,
                        BuddyMatch.participant_two_user_id == authenticated_user_id,
                    ),
                )
                .order_by(BuddyConversation.id)
            )
        ).all()
    )


async def get_buddy_unread_summary(
    session: AsyncSession,
    *,
    authenticated_user_id: UUID,
    clock: Clock = _system_utc_now,
) -> BuddyUnreadSummary:
    """Count effective unread incoming messages across authoritative ACTIVE Matches."""
    now = _utc_now(clock)
    result = await session.execute(
        select(BuddyConversation.id, func.count(BuddyMessage.id))
        .join(BuddyMatch, BuddyMatch.id == BuddyConversation.match_id)
        .join(BuddyMessage, BuddyMessage.conversation_id == BuddyConversation.id)
        .where(
            BuddyMatch.status == MatchStatus.ACTIVE,
            BuddyMatch.deleted_at.is_(None),
            or_(
                BuddyMatch.participant_one_user_id == authenticated_user_id,
                BuddyMatch.participant_two_user_id == authenticated_user_id,
            ),
            BuddyMessage.sender_id != authenticated_user_id,
            BuddyMessage.read_at.is_(None),
            BuddyMessage.expires_at > now,
        )
        .group_by(BuddyConversation.id)
        .order_by(BuddyConversation.id)
    )
    conversations = tuple(
        BuddyUnreadConversation(conversation_id=conversation_id, unread_count=int(unread_count))
        for conversation_id, unread_count in result.tuples().all()
    )
    return BuddyUnreadSummary(
        conversations=conversations,
        total_unread_messages=sum(item.unread_count for item in conversations),
    )


async def get_realtime_buddy_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_user_id: UUID,
    message_id: UUID,
    clock: Clock = _system_utc_now,
) -> BuddyMessage | None:
    """Load one effective message after reapplying exact conversation authorization."""
    await _require_authorized_active_conversation(
        session,
        conversation_id=conversation_id,
        authenticated_user_id=authenticated_user_id,
    )
    return cast(
        BuddyMessage | None,
        await session.scalar(
            select(BuddyMessage).where(
                BuddyMessage.id == message_id,
                BuddyMessage.conversation_id == conversation_id,
                BuddyMessage.expires_at > _utc_now(clock),
            )
        ),
    )


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
    client_message_id: UUID | None = None,
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
        client_message_id=client_message_id or uuid4(),
        body=validated_body,
        created_at=created_at,
        expires_at=buddy_message_expires_at(created_at),
    )
    session.add(message)
    await session.flush()
    return message


async def send_buddy_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_sender_id: UUID,
    client_message_id: UUID,
    body: str,
    clock: Clock = _system_utc_now,
) -> BuddyMessage:
    """Idempotently persist one authorized HTTP/realtime fallback send.

    The unique sender/client key makes concurrent retries converge on one row.
    Reuse against another conversation or body is rejected without returning the
    pre-existing message, so the key cannot become a cross-conversation oracle.
    """
    validated_body = validate_buddy_message_body(body)
    try:
        await _require_authorized_active_conversation(
            session,
            conversation_id=conversation_id,
            authenticated_user_id=authenticated_sender_id,
        )
    except BuddyChatReadError:
        raise BuddyMessagePersistenceError(
            BuddyMessagePersistenceReason.ACTIVE_CONVERSATION_REQUIRED
        ) from None

    created_at = _utc_now(clock)
    statement = (
        insert(BuddyMessage)
        .values(
            conversation_id=conversation_id,
            sender_id=authenticated_sender_id,
            client_message_id=client_message_id,
            body=validated_body,
            created_at=created_at,
            expires_at=buddy_message_expires_at(created_at),
        )
        .on_conflict_do_nothing(
            index_elements=[BuddyMessage.sender_id, BuddyMessage.client_message_id]
        )
        .returning(BuddyMessage)
    )
    inserted = await session.scalar(statement)
    if inserted is not None:
        return inserted

    existing = await session.scalar(
        select(BuddyMessage).where(
            BuddyMessage.sender_id == authenticated_sender_id,
            BuddyMessage.client_message_id == client_message_id,
        )
    )
    if (
        existing is None
        or existing.conversation_id != conversation_id
        or existing.body != validated_body
        or existing.expires_at <= created_at
    ):
        raise BuddyMessagePersistenceError(BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED)
    return existing


async def list_buddy_messages(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_user_id: UUID,
    before: str | None = None,
    page_size: int = DEFAULT_CHAT_MESSAGE_PAGE_SIZE,
    clock: Clock = _system_utc_now,
) -> BuddyMessagePage:
    """Return the newest bounded window, or the next older keyset page.

    PostgreSQL reads newest-first through the CHAT-001 composite index; the
    service reverses only that bounded page so every response is chronological.
    """
    if not 1 <= page_size <= MAX_CHAT_MESSAGE_PAGE_SIZE:
        raise ValueError("Chat message page size is outside the supported range.")
    await _require_authorized_active_conversation(
        session,
        conversation_id=conversation_id,
        authenticated_user_id=authenticated_user_id,
    )
    now = _utc_now(clock)
    statement = select(BuddyMessage).where(
        BuddyMessage.conversation_id == conversation_id,
        BuddyMessage.expires_at > now,
    )
    if before is not None:
        cursor_created_at, cursor_id = decode_buddy_message_cursor(before)
        statement = statement.where(
            or_(
                BuddyMessage.created_at < cursor_created_at,
                and_(
                    BuddyMessage.created_at == cursor_created_at,
                    BuddyMessage.id < cursor_id,
                ),
            )
        )
    newest_first = tuple(
        (
            await session.scalars(
                statement.order_by(
                    BuddyMessage.created_at.desc(),
                    BuddyMessage.id.desc(),
                ).limit(page_size + 1)
            )
        ).all()
    )
    has_more = len(newest_first) > page_size
    selected_newest_first = newest_first[:page_size]
    items = tuple(reversed(selected_newest_first))
    next_before = None
    if has_more and selected_newest_first:
        oldest = selected_newest_first[-1]
        next_before = encode_buddy_message_cursor(oldest.created_at, oldest.id)
    return BuddyMessagePage(items=items, next_before=next_before)


async def acknowledge_buddy_messages_read(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    authenticated_reader_id: UUID,
    through_message_id: UUID,
    clock: Clock = _system_utc_now,
) -> BuddyReadAcknowledgement:
    """Atomically set first-read retention for incoming messages through a boundary."""
    now = _utc_now(clock)
    boundary = await session.scalar(
        select(BuddyMessage)
        .join(
            BuddyConversation,
            BuddyConversation.id == BuddyMessage.conversation_id,
        )
        .join(BuddyMatch, BuddyMatch.id == BuddyConversation.match_id)
        .where(
            BuddyConversation.id == conversation_id,
            BuddyMessage.id == through_message_id,
            BuddyMessage.expires_at > now,
            BuddyMatch.status == MatchStatus.ACTIVE,
            BuddyMatch.deleted_at.is_(None),
            or_(
                BuddyMatch.participant_one_user_id == authenticated_reader_id,
                BuddyMatch.participant_two_user_id == authenticated_reader_id,
            ),
        )
    )
    if boundary is None:
        # The same response covers a foreign/inactive conversation, a foreign
        # message boundary, and an effectively expired boundary.
        raise BuddyChatReadError(BuddyChatReadReason.MESSAGE_NOT_FOUND)

    statement = (
        update(BuddyMessage)
        .where(
            BuddyMessage.conversation_id == conversation_id,
            BuddyMessage.sender_id != authenticated_reader_id,
            BuddyMessage.read_at.is_(None),
            BuddyMessage.expires_at > now,
            or_(
                BuddyMessage.created_at < boundary.created_at,
                and_(
                    BuddyMessage.created_at == boundary.created_at,
                    BuddyMessage.id <= boundary.id,
                ),
            ),
        )
        .values(
            read_at=now,
            expires_at=func.least(
                BuddyMessage.expires_at,
                now + BUDDY_MESSAGE_READ_RETENTION,
            ),
        )
        .returning(BuddyMessage.id)
    )
    updated_ids = tuple((await session.scalars(statement)).all())
    return BuddyReadAcknowledgement(
        through_message_id=through_message_id,
        marked_read_count=len(updated_ids),
    )
