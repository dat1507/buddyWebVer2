"""INV-006 owner mutation, expiry, replay, locking, and privacy service tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InvitationStatus,
    MatchingInvitation,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_mutations import (
    Clock,
    InvitationMutationError,
    InvitationMutationReason,
    InvitationMutationResult,
    cancel_matching_invitation,
    decline_matching_invitation,
    hide_accepted_invitation_from_sender,
)

NOW = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
SENDER_ID = UUID("10000000-0000-4000-8000-000000000001")
RECIPIENT_ID = UUID("20000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")


def _principal(user_id: UUID = RECIPIENT_ID) -> VerifiedBuddyPrincipal:
    user = User(
        id=user_id,
        email="owner@example.invalid",
        password_hash="test-only-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )
    profile = StudentProfile(
        id=PROFILE_ID,
        user_id=user_id,
        full_name="Mutation owner",
        student_type=StudentType.INTERNATIONAL,
    )
    return VerifiedBuddyPrincipal(user=user, profile=profile)


def _invitation(
    status: InvitationStatus = InvitationStatus.PENDING,
    *,
    expires_at: datetime | None = None,
    hidden_at: datetime | None = None,
) -> MatchingInvitation:
    created_at = NOW - timedelta(hours=1)
    responded_at = (
        NOW - timedelta(minutes=30)
        if status in {InvitationStatus.ACCEPTED, InvitationStatus.DECLINED}
        else None
    )
    return MatchingInvitation(
        id=INVITATION_ID,
        sender_id=SENDER_ID,
        recipient_id=RECIPIENT_ID,
        message="Private invitation",
        status=status,
        created_at=created_at,
        updated_at=responded_at or created_at,
        expires_at=expires_at or created_at + timedelta(days=7),
        responded_at=responded_at,
        cancelled_at=(
            NOW - timedelta(minutes=30) if status is InvitationStatus.CANCELLED else None
        ),
        expired_at=(NOW if status is InvitationStatus.EXPIRED else None),
        sender_hidden_at=hidden_at,
    )


def _session(value: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=value)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


async def _call(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    session: AsyncSession,
    owner_id: UUID,
    *,
    clock: Clock = lambda: NOW,
) -> InvitationMutationResult:
    return await operation(
        session,
        _principal(owner_id),
        invitation_id=INVITATION_ID,
        clock=clock,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "owner_id", "expected_status", "owner_column"),
    (
        (decline_matching_invitation, RECIPIENT_ID, InvitationStatus.DECLINED, "recipient_id"),
        (cancel_matching_invitation, SENDER_ID, InvitationStatus.CANCELLED, "sender_id"),
    ),
)
async def test_pending_owner_transition_locks_refreshes_and_flushes_once(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    owner_id: UUID,
    expected_status: InvitationStatus,
    owner_column: str,
) -> None:
    invitation = _invitation()
    mock, session = _session(invitation)

    result = await _call(operation, session, owner_id)

    assert result.invitation_id == INVITATION_ID
    assert result.status is expected_status
    assert invitation.status is expected_status
    statement = mock.scalar.await_args.args[0]
    assert statement.get_execution_options()["populate_existing"] is True
    sql = str(statement).lower()
    assert "for update" in sql
    assert owner_column in sql
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "status", "owner_id"),
    (
        (decline_matching_invitation, InvitationStatus.DECLINED, RECIPIENT_ID),
        (cancel_matching_invitation, InvitationStatus.CANCELLED, SENDER_ID),
    ),
)
async def test_same_terminal_owner_retry_is_idempotent_without_rewrite(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    status: InvitationStatus,
    owner_id: UUID,
) -> None:
    invitation = _invitation(status)
    version = invitation.version
    mock, session = _session(invitation)

    result = await _call(operation, session, owner_id)

    assert result.status is status
    assert invitation.version == version
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "status", "owner_id", "reason"),
    (
        (
            decline_matching_invitation,
            InvitationStatus.ACCEPTED,
            RECIPIENT_ID,
            InvitationMutationReason.INVALID_STATE,
        ),
        (
            decline_matching_invitation,
            InvitationStatus.CANCELLED,
            RECIPIENT_ID,
            InvitationMutationReason.INVALID_STATE,
        ),
        (
            cancel_matching_invitation,
            InvitationStatus.ACCEPTED,
            SENDER_ID,
            InvitationMutationReason.INVALID_STATE,
        ),
        (
            cancel_matching_invitation,
            InvitationStatus.DECLINED,
            SENDER_ID,
            InvitationMutationReason.INVALID_STATE,
        ),
        (
            decline_matching_invitation,
            InvitationStatus.EXPIRED,
            RECIPIENT_ID,
            InvitationMutationReason.EXPIRED,
        ),
        (
            cancel_matching_invitation,
            InvitationStatus.EXPIRED,
            SENDER_ID,
            InvitationMutationReason.EXPIRED,
        ),
    ),
)
async def test_terminal_conflicts_are_stable_and_never_overwrite(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    status: InvitationStatus,
    owner_id: UUID,
    reason: InvitationMutationReason,
) -> None:
    invitation = _invitation(status)
    mock, session = _session(invitation)

    with pytest.raises(InvitationMutationError) as error:
        await _call(operation, session, owner_id)

    assert error.value.reason is reason
    assert invitation.status is status
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "owner_id"),
    (
        (decline_matching_invitation, RECIPIENT_ID),
        (cancel_matching_invitation, SENDER_ID),
    ),
)
async def test_effectively_expired_pending_cannot_be_mutated(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    owner_id: UUID,
) -> None:
    invitation = _invitation(expires_at=NOW)
    mock, session = _session(invitation)

    with pytest.raises(InvitationMutationError) as error:
        await _call(operation, session, owner_id)

    assert error.value.reason is InvitationMutationReason.EXPIRED
    assert invitation.status is InvitationStatus.PENDING
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "owner_id"),
    (
        (decline_matching_invitation, RECIPIENT_ID),
        (cancel_matching_invitation, SENDER_ID),
        (hide_accepted_invitation_from_sender, SENDER_ID),
    ),
)
async def test_foreign_or_missing_invitation_is_indistinguishable(
    operation: Callable[..., Awaitable[InvitationMutationResult]],
    owner_id: UUID,
) -> None:
    mock, session = _session(None)

    with pytest.raises(InvitationMutationError) as error:
        await _call(operation, session, owner_id)

    assert error.value.reason is InvitationMutationReason.NOT_FOUND
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_sender_hide_is_idempotent_and_changes_only_visibility_timestamp() -> None:
    accepted_at = NOW - timedelta(minutes=30)
    invitation = _invitation(InvitationStatus.ACCEPTED)
    mock, session = _session(invitation)

    first = await _call(hide_accepted_invitation_from_sender, session, SENDER_ID)
    second = await _call(
        hide_accepted_invitation_from_sender,
        session,
        SENDER_ID,
        clock=lambda: NOW + timedelta(minutes=1),
    )

    assert first == second
    assert first.status is InvitationStatus.ACCEPTED
    assert invitation.status is InvitationStatus.ACCEPTED
    assert invitation.responded_at == accepted_at
    assert invitation.sender_hidden_at == NOW
    assert mock.flush.await_count == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status",
    (
        InvitationStatus.PENDING,
        InvitationStatus.DECLINED,
        InvitationStatus.CANCELLED,
        InvitationStatus.EXPIRED,
    ),
)
async def test_sender_hide_rejects_every_nonaccepted_state(status: InvitationStatus) -> None:
    invitation = _invitation(status)
    mock, session = _session(invitation)

    with pytest.raises(InvitationMutationError) as error:
        await _call(hide_accepted_invitation_from_sender, session, SENDER_ID)

    assert error.value.reason is InvitationMutationReason.INVALID_STATE
    assert invitation.sender_hidden_at is None
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_mutation_clock_must_be_timezone_aware() -> None:
    invitation = _invitation()
    _mock, session = _session(invitation)

    with pytest.raises(ValueError, match="timezone-aware"):
        await _call(
            decline_matching_invitation,
            session,
            RECIPIENT_ID,
            clock=lambda: datetime(2026, 9, 30, 15, 0),
        )
