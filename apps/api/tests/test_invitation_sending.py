"""INV-003 invitation creation policy unit tests."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.invitation_sending as sending
from app.models import InvitationStatus, MatchingInvitation, StudentType, User, UserRole
from app.services.invitation_sending import (
    MATCHING_INVITATION_CREATED,
    InvitationSendError,
    InvitationSendReason,
    send_matching_invitation,
)
from app.services.matching_eligibility import EligibleMatchingPrincipal

NOW = datetime(2026, 9, 29, 8, 15, tzinfo=UTC)
SENDER_ID = UUID("10000000-0000-4000-8000-000000000001")
RECIPIENT_ID = UUID("20000000-0000-4000-8000-000000000001")
SENDER_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
RECIPIENT_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _principal(user_id: UUID, profile_id: UUID, student_type: StudentType) -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=user_id,
        profile_id=profile_id,
        student_type=student_type,
    )


def _user(user_id: UUID, email: str) -> User:
    return User(
        id=user_id,
        email=email,
        password_hash="not-sensitive",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.scalar = AsyncMock()
    nested = MagicMock(spec=AbstractAsyncContextManager[None])
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    mock.begin_nested.return_value = nested

    def assign_id(value: object) -> None:
        if isinstance(value, MatchingInvitation):
            value.id = INVITATION_ID

    mock.add.side_effect = assign_id
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_send_creates_trimmed_seven_day_invitation_and_safe_outbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    sender = _principal(SENDER_ID, SENDER_PROFILE_ID, StudentType.VIETNAMESE)
    recipient = _principal(
        RECIPIENT_ID,
        RECIPIENT_PROFILE_ID,
        StudentType.INTERNATIONAL,
    )
    sender_user = _user(SENDER_ID, "sender@example.com")
    recipient_user = _user(RECIPIENT_ID, "recipient@example.com")
    monkeypatch.setattr(
        sending,
        "_lock_and_revalidate_pair",
        AsyncMock(return_value=(sender_user, recipient_user, sender, recipient)),
    )
    expire_or_reject = AsyncMock()
    reject_active = AsyncMock()
    require_capacity = AsyncMock()
    enqueue = AsyncMock()
    monkeypatch.setattr(sending, "_expire_or_reject_pending_pair", expire_or_reject)
    monkeypatch.setattr(sending, "_reject_active_pair", reject_active)
    monkeypatch.setattr(sending, "_require_pending_capacity", require_capacity)
    monkeypatch.setattr(sending, "enqueue_transactional_email", enqueue)

    invitation = await send_matching_invitation(
        session,
        sender,
        recipient_profile_id=RECIPIENT_PROFILE_ID,
        message="  Hello\tfriend  ",
        clock=lambda: NOW,
    )

    assert invitation.id == INVITATION_ID
    assert invitation.message == "Hello\tfriend"
    assert invitation.status is InvitationStatus.PENDING
    assert invitation.created_at == NOW
    assert invitation.expires_at == NOW + timedelta(days=7)
    expire_or_reject.assert_awaited_once_with(
        session,
        sender_user_id=SENDER_ID,
        recipient_user_id=RECIPIENT_ID,
        at=NOW,
    )
    reject_active.assert_awaited_once()
    require_capacity.assert_awaited_once()
    await_args = enqueue.await_args
    assert await_args is not None
    enqueue.assert_awaited_once_with(
        session,
        event_type=MATCHING_INVITATION_CREATED,
        aggregate_id=INVITATION_ID,
        recipient_user_id=RECIPIENT_ID,
        recipient_email="recipient@example.com",
        idempotency_key=f"matching-invitation-created:{INVITATION_ID}",
        payload={"invitation_id": str(INVITATION_ID)},
        clock=await_args.kwargs["clock"],
    )
    assert await_args.kwargs["clock"]() == NOW


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("count", "rejected"),
    ((29, False), (30, True)),
)
async def test_outgoing_limit_counts_only_effective_pending(
    count: int,
    rejected: bool,
) -> None:
    mock, session = _session()
    mock.scalar.return_value = count

    if rejected:
        with pytest.raises(InvitationSendError) as raised:
            await sending._require_pending_capacity(session, sender_user_id=SENDER_ID, at=NOW)
        assert raised.value.reason is InvitationSendReason.PENDING_LIMIT_REACHED
    else:
        await sending._require_pending_capacity(session, sender_user_id=SENDER_ID, at=NOW)

    statement = mock.scalar.await_args.args[0]
    sql = str(statement).upper()
    assert "SENDER_ID" in sql
    assert "STATUS" in sql
    assert "EXPIRES_AT >" in sql


@pytest.mark.anyio
async def test_stale_pending_pair_is_expired_before_reinvite() -> None:
    mock, session = _session()
    invitation = MatchingInvitation(
        sender_id=SENDER_ID,
        recipient_id=RECIPIENT_ID,
        message="Hello",
        status=InvitationStatus.PENDING,
        created_at=NOW - timedelta(days=7),
        expires_at=NOW,
    )
    mock.scalar.return_value = invitation

    await sending._expire_or_reject_pending_pair(
        session,
        sender_user_id=SENDER_ID,
        recipient_user_id=RECIPIENT_ID,
        at=NOW,
    )

    assert invitation.status is InvitationStatus.EXPIRED
    assert invitation.expired_at == NOW
    mock.flush.assert_awaited_once_with()


@pytest.mark.anyio
async def test_unexpired_reciprocal_pair_is_rejected_safely() -> None:
    mock, session = _session()
    invitation = MatchingInvitation(
        sender_id=RECIPIENT_ID,
        recipient_id=SENDER_ID,
        message="private text",
        status=InvitationStatus.PENDING,
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
    )
    mock.scalar.return_value = invitation

    with pytest.raises(InvitationSendError) as raised:
        await sending._expire_or_reject_pending_pair(
            session,
            sender_user_id=SENDER_ID,
            recipient_user_id=RECIPIENT_ID,
            at=NOW,
        )

    assert raised.value.reason is InvitationSendReason.PENDING_EXISTS
    assert "private text" not in str(raised.value)
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_active_match_blocks_reinvite_independent_of_invitation_history() -> None:
    mock, session = _session()
    mock.scalar.return_value = True

    with pytest.raises(InvitationSendError) as raised:
        await sending._reject_active_pair(
            session,
            sender_user_id=SENDER_ID,
            recipient_user_id=RECIPIENT_ID,
        )

    assert raised.value.reason is InvitationSendReason.ACTIVE_PAIR_EXISTS


@pytest.mark.anyio
async def test_accepted_invitation_history_without_active_match_does_not_block() -> None:
    mock, session = _session()
    mock.scalar.return_value = None

    await sending._reject_active_pair(
        session,
        sender_user_id=SENDER_ID,
        recipient_user_id=RECIPIENT_ID,
    )
