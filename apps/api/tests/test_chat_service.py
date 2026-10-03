"""CHAT-002 cursor, authorization, idempotency, and first-read service tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BuddyConversation, BuddyMessage
from app.services.buddy_chat import (
    BuddyChatReadError,
    BuddyChatReadReason,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    acknowledge_buddy_messages_read,
    decode_buddy_message_cursor,
    encode_buddy_message_cursor,
    get_buddy_unread_summary,
    list_buddy_messages,
    send_buddy_message,
)

CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000001")
SENDER_ID = UUID("20000000-0000-4000-8000-000000000001")
READER_ID = UUID("30000000-0000-4000-8000-000000000001")
CLIENT_MESSAGE_ID = UUID("40000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _conversation() -> BuddyConversation:
    return BuddyConversation(
        id=CONVERSATION_ID,
        match_id=UUID("50000000-0000-4000-8000-000000000001"),
        created_at=NOW,
    )


def _message(
    index: int,
    *,
    sender_id: UUID = SENDER_ID,
    body: str | None = None,
) -> BuddyMessage:
    created_at = NOW - timedelta(minutes=10 - index)
    return BuddyMessage(
        id=UUID(f"60000000-0000-4000-8000-{index:012d}"),
        conversation_id=CONVERSATION_ID,
        sender_id=sender_id,
        client_message_id=UUID(f"70000000-0000-4000-8000-{index:012d}"),
        body=body or f"message-{index}",
        created_at=created_at,
        expires_at=created_at + timedelta(days=90),
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.scalars = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _scalars(*items: object) -> MagicMock:
    result = MagicMock()
    result.all.return_value = list(items)
    return result


def test_cursor_round_trip_preserves_full_order_tuple_and_rejects_tampering() -> None:
    message_id = UUID("80000000-0000-4000-8000-000000000001")
    created_at = NOW.replace(microsecond=123456)

    cursor = encode_buddy_message_cursor(created_at, message_id)

    assert "2026" not in cursor
    assert decode_buddy_message_cursor(cursor) == (created_at, message_id)
    with pytest.raises(BuddyChatReadError) as raised:
        decode_buddy_message_cursor(cursor[:-1] + "!")
    assert raised.value.reason is BuddyChatReadReason.INVALID_CURSOR


@pytest.mark.anyio
async def test_history_uses_participant_filter_expiry_keyset_and_chronological_page() -> None:
    mock, session = _session()
    newest, middle, oldest, extra = (_message(index) for index in (4, 3, 2, 1))
    mock.scalar.return_value = _conversation()
    mock.scalars.return_value = _scalars(newest, middle, oldest, extra)
    before = encode_buddy_message_cursor(NOW, UUID(int=999))

    page = await list_buddy_messages(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_user_id=SENDER_ID,
        before=before,
        page_size=3,
        clock=lambda: NOW,
    )

    assert page.items == (oldest, middle, newest)
    assert page.next_before == encode_buddy_message_cursor(oldest.created_at, oldest.id)
    authorization_sql = str(mock.scalar.await_args.args[0]).lower()
    history_sql = str(mock.scalars.await_args.args[0]).lower()
    assert "matches.status" in authorization_sql
    assert "participant_one_user_id" in authorization_sql
    assert "participant_two_user_id" in authorization_sql
    assert "expires_at >" in history_sql
    assert "created_at <" in history_sql and "buddy_messages.id <" in history_sql
    assert "created_at desc" in history_sql and "id desc" in history_sql
    assert "limit" in history_sql


@pytest.mark.anyio
async def test_history_rejects_foreign_conversation_before_message_query() -> None:
    mock, session = _session()
    mock.scalar.return_value = None

    with pytest.raises(BuddyChatReadError) as raised:
        await list_buddy_messages(
            session,
            conversation_id=CONVERSATION_ID,
            authenticated_user_id=READER_ID,
        )

    assert raised.value.reason is BuddyChatReadReason.CONVERSATION_NOT_FOUND
    mock.scalars.assert_not_awaited()


@pytest.mark.anyio
async def test_history_empty_page_has_no_cursor() -> None:
    mock, session = _session()
    mock.scalar.return_value = _conversation()
    mock.scalars.return_value = _scalars()

    page = await list_buddy_messages(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_user_id=SENDER_ID,
        clock=lambda: NOW,
    )

    assert page.items == ()
    assert page.next_before is None


@pytest.mark.anyio
async def test_send_inserts_once_and_exact_retry_returns_same_message() -> None:
    inserted = _message(1, body="  inert <b>text</b> 😀  ")
    inserted.client_message_id = CLIENT_MESSAGE_ID
    first_mock, first_session = _session()
    first_mock.scalar.side_effect = [_conversation(), inserted]

    created = await send_buddy_message(
        first_session,
        conversation_id=CONVERSATION_ID,
        authenticated_sender_id=SENDER_ID,
        client_message_id=CLIENT_MESSAGE_ID,
        body=inserted.body,
        clock=lambda: NOW,
    )

    assert created is inserted
    insert_sql = str(first_mock.scalar.await_args_list[1].args[0]).lower()
    assert "on conflict (sender_id, client_message_id) do nothing" in insert_sql
    assert "returning" in insert_sql

    replay_mock, replay_session = _session()
    replay_mock.scalar.side_effect = [_conversation(), None, inserted]
    replay = await send_buddy_message(
        replay_session,
        conversation_id=CONVERSATION_ID,
        authenticated_sender_id=SENDER_ID,
        client_message_id=CLIENT_MESSAGE_ID,
        body=inserted.body,
        clock=lambda: NOW + timedelta(seconds=2),
    )
    assert replay is inserted


@pytest.mark.anyio
@pytest.mark.parametrize(
    "conflict",
    ["different body", "different conversation", "expired replay"],
)
async def test_send_rejects_idempotency_key_reuse_without_leaking_existing(
    conflict: str,
) -> None:
    existing = _message(1, body="original")
    existing.client_message_id = CLIENT_MESSAGE_ID
    if conflict == "different conversation":
        existing.conversation_id = UUID("90000000-0000-4000-8000-000000000001")
        requested_body = "original"
    else:
        requested_body = "changed"
    if conflict == "expired replay":
        existing.expires_at = NOW - timedelta(microseconds=1)
        requested_body = "original"
    mock, session = _session()
    mock.scalar.side_effect = [_conversation(), None, existing]

    with pytest.raises(BuddyMessagePersistenceError) as raised:
        await send_buddy_message(
            session,
            conversation_id=CONVERSATION_ID,
            authenticated_sender_id=SENDER_ID,
            client_message_id=CLIENT_MESSAGE_ID,
            body=requested_body,
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED
    assert "original" not in str(raised.value)


@pytest.mark.anyio
async def test_read_ack_is_one_conditional_incoming_only_retention_update() -> None:
    boundary = _message(5, sender_id=READER_ID)
    mock, session = _session()
    mock.scalar.return_value = boundary
    updated_one = UUID("a0000000-0000-4000-8000-000000000001")
    updated_two = UUID("a0000000-0000-4000-8000-000000000002")
    mock.scalars.return_value = _scalars(updated_one, updated_two)

    result = await acknowledge_buddy_messages_read(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_reader_id=READER_ID,
        through_message_id=boundary.id,
        clock=lambda: NOW,
    )

    assert result.marked_read_count == 2
    update_sql = str(mock.scalars.await_args.args[0]).lower()
    assert "update app_private.buddy_messages" in update_sql
    assert "sender_id !=" in update_sql
    assert "read_at is null" in update_sql
    assert "expires_at >" in update_sql
    assert "created_at <" in update_sql and "buddy_messages.id <=" in update_sql
    assert "least(" in update_sql
    assert "returning" in update_sql


@pytest.mark.anyio
async def test_read_ack_rejects_foreign_expired_or_unknown_boundary_without_update() -> None:
    mock, session = _session()
    mock.scalar.return_value = None

    with pytest.raises(BuddyChatReadError) as raised:
        await acknowledge_buddy_messages_read(
            session,
            conversation_id=CONVERSATION_ID,
            authenticated_reader_id=READER_ID,
            through_message_id=UUID(int=99),
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyChatReadReason.MESSAGE_NOT_FOUND
    mock.scalars.assert_not_awaited()


@pytest.mark.anyio
async def test_unread_summary_counts_only_effective_incoming_active_match_messages() -> None:
    other_conversation = UUID("10000000-0000-4000-8000-000000000002")
    mock, session = _session()
    rows = MagicMock()
    rows.tuples.return_value.all.return_value = [
        (CONVERSATION_ID, 2),
        (other_conversation, 1),
    ]
    mock.execute = AsyncMock(return_value=rows)

    summary = await get_buddy_unread_summary(
        session,
        authenticated_user_id=READER_ID,
        clock=lambda: NOW,
    )

    assert summary.total_unread_messages == 3
    assert [(item.conversation_id, item.unread_count) for item in summary.conversations] == [
        (CONVERSATION_ID, 2),
        (other_conversation, 1),
    ]
    statement = str(mock.execute.await_args.args[0]).lower()
    assert "matches.status" in statement and "matches.deleted_at is null" in statement
    assert "buddy_messages.sender_id !=" in statement
    assert "buddy_messages.read_at is null" in statement
    assert "buddy_messages.expires_at >" in statement
    assert "group by app_private.buddy_conversations.id" in statement
