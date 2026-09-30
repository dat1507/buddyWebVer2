"""CHAT-001 atomic conversation and participant-safe message service tests."""

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BuddyConversation, BuddyMatch, BuddyMessage, MatchStatus
from app.services.buddy_chat import (
    BuddyConversationPersistenceError,
    BuddyConversationPersistenceReason,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    get_or_create_buddy_conversation,
    persist_buddy_message,
)

MATCH_ID = UUID("10000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-4000-8000-000000000001")
FIRST_USER_ID = UUID("30000000-0000-4000-8000-000000000001")
SECOND_USER_ID = UUID("40000000-0000-4000-8000-000000000001")
OUTSIDER_ID = UUID("50000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 9, 30, 5, 0, tzinfo=UTC)


def _match() -> BuddyMatch:
    return BuddyMatch(
        id=MATCH_ID,
        participant_one_user_id=FIRST_USER_ID,
        participant_two_user_id=SECOND_USER_ID,
        participant_one_profile_id=UUID("60000000-0000-4000-8000-000000000001"),
        participant_two_profile_id=UUID("70000000-0000-4000-8000-000000000001"),
        accepted_invitation_id=UUID("80000000-0000-4000-8000-000000000001"),
        status=MatchStatus.ACTIVE,
        score=80,
        score_breakdown={},
        activated_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


def _conversation() -> BuddyConversation:
    return BuddyConversation(id=CONVERSATION_ID, match_id=MATCH_ID, created_at=NOW)


def _session(*scalar_results: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=scalar_results)
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_conversation_get_or_create_inserts_once_without_committing() -> None:
    conversation = _conversation()
    mock, session = _session(_match(), conversation)

    result = await get_or_create_buddy_conversation(
        session,
        match_id=MATCH_ID,
        clock=lambda: NOW,
    )

    assert result is conversation
    statements = [str(call.args[0]).lower() for call in mock.scalar.await_args_list]
    assert "status" in statements[0]
    assert "on conflict (match_id) do nothing" in statements[1]
    assert "returning" in statements[1]
    mock.commit.assert_not_called()


@pytest.mark.anyio
async def test_conversation_get_or_create_returns_unique_conflict_winner() -> None:
    existing = _conversation()
    mock, session = _session(_match(), None, existing)

    result = await get_or_create_buddy_conversation(
        session,
        match_id=MATCH_ID,
        clock=lambda: NOW,
    )

    assert result is existing
    assert mock.scalar.await_count == 3
    assert "buddy_conversations.match_id" in str(mock.scalar.await_args_list[2].args[0])
    mock.commit.assert_not_called()


@pytest.mark.anyio
async def test_conversation_requires_active_match() -> None:
    mock, session = _session(None)

    with pytest.raises(BuddyConversationPersistenceError) as raised:
        await get_or_create_buddy_conversation(session, match_id=MATCH_ID)

    assert raised.value.reason is BuddyConversationPersistenceReason.ACTIVE_MATCH_REQUIRED
    assert mock.scalar.await_count == 1


@pytest.mark.anyio
async def test_message_persists_for_authenticated_participant_without_commit() -> None:
    mock, session = _session(_match())

    result = await persist_buddy_message(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_sender_id=FIRST_USER_ID,
        body="  Grüße 😀  ",
        clock=lambda: NOW,
    )

    assert isinstance(result, BuddyMessage)
    assert result.conversation_id == CONVERSATION_ID
    assert result.sender_id == FIRST_USER_ID
    assert result.body == "  Grüße 😀  "
    assert result.created_at == NOW
    assert result.expires_at == NOW + timedelta(days=90)
    statement = str(mock.scalar.await_args.args[0]).lower()
    assert "join app_private.buddy_conversations" in statement
    assert "matches.status" in statement
    mock.add.assert_called_once_with(result)
    mock.flush.assert_awaited_once()
    mock.commit.assert_not_called()


@pytest.mark.anyio
async def test_message_rejects_outsider_before_write_with_sanitized_reason() -> None:
    mock, session = _session(_match())

    with pytest.raises(BuddyMessagePersistenceError) as raised:
        await persist_buddy_message(
            session,
            conversation_id=CONVERSATION_ID,
            authenticated_sender_id=OUTSIDER_ID,
            body="Private message",
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMessagePersistenceReason.SENDER_NOT_PARTICIPANT
    assert "Private message" not in str(raised.value)
    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_message_rejects_unknown_conversation_and_invalid_body() -> None:
    missing_mock, missing_session = _session(None)
    with pytest.raises(BuddyMessagePersistenceError) as raised:
        await persist_buddy_message(
            missing_session,
            conversation_id=CONVERSATION_ID,
            authenticated_sender_id=FIRST_USER_ID,
            body="Hello",
        )
    assert raised.value.reason is BuddyMessagePersistenceReason.ACTIVE_CONVERSATION_REQUIRED
    missing_mock.add.assert_not_called()

    invalid_mock, invalid_session = _session(_match())
    with pytest.raises(ValueError, match="blank"):
        await persist_buddy_message(
            invalid_session,
            conversation_id=CONVERSATION_ID,
            authenticated_sender_id=FIRST_USER_ID,
            body=" \t ",
        )
    invalid_mock.scalar.assert_not_awaited()


@pytest.mark.anyio
async def test_message_rejects_naive_server_clock() -> None:
    mock, session = _session(_match())

    with pytest.raises(ValueError, match="timezone-aware"):
        await persist_buddy_message(
            session,
            conversation_id=CONVERSATION_ID,
            authenticated_sender_id=FIRST_USER_ID,
            body="Hello",
            clock=lambda: datetime(2026, 9, 30, 5, 0),
        )

    mock.add.assert_not_called()
