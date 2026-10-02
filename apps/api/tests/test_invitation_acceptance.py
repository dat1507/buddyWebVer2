"""INV-005 atomic acceptance orchestration and stable replay tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.invitation_acceptance as acceptance
from app.models import (
    BuddyConversation,
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.services.buddy_access import BuddyCapabilityError, VerifiedBuddyPrincipal
from app.services.buddy_matches import (
    BuddyMatchActivationError,
    BuddyMatchActivationReason,
    LockedBuddyParticipants,
)
from app.services.invitation_acceptance import (
    MATCHING_INVITATION_ACCEPTED,
    InvitationAcceptError,
    InvitationAcceptReason,
    accept_matching_invitation,
)
from app.services.matching_eligibility import EligibleMatchingPrincipal

NOW = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
SENDER_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
SENDER_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
RECIPIENT_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
RECIPIENT_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")
MATCH_ID = UUID("40000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("50000000-0000-4000-8000-000000000001")
SEMESTER_ID = UUID("60000000-0000-4000-8000-000000000001")


def _user(user_id: UUID, email: str) -> User:
    return User(
        id=user_id,
        email=email,
        password_hash="test-only-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
        semester_id=SEMESTER_ID,
    )


def _profile(profile_id: UUID, user_id: UUID, student_type: StudentType) -> StudentProfile:
    return StudentProfile(
        id=profile_id,
        user_id=user_id,
        full_name="Eligible participant",
        student_type=student_type,
        matching_opt_in=True,
    )


def _invitation(
    status: InvitationStatus = InvitationStatus.PENDING,
    *,
    expires_at: datetime | None = None,
) -> MatchingInvitation:
    return MatchingInvitation(
        id=INVITATION_ID,
        sender_id=SENDER_USER_ID,
        recipient_id=RECIPIENT_USER_ID,
        message="Private invitation message",
        status=status,
        created_at=NOW - timedelta(hours=1),
        updated_at=NOW - timedelta(hours=1),
        expires_at=expires_at or NOW + timedelta(days=6),
        responded_at=NOW if status is InvitationStatus.ACCEPTED else None,
        cancelled_at=NOW if status is InvitationStatus.CANCELLED else None,
        expired_at=NOW if status is InvitationStatus.EXPIRED else None,
    )


def _participants() -> LockedBuddyParticipants:
    return LockedBuddyParticipants(
        sender_user=_user(SENDER_USER_ID, "sender@example.invalid"),
        recipient_user=_user(RECIPIENT_USER_ID, "recipient@example.invalid"),
        sender_profile=_profile(
            SENDER_PROFILE_ID,
            SENDER_USER_ID,
            StudentType.VIETNAMESE,
        ),
        recipient_profile=_profile(
            RECIPIENT_PROFILE_ID,
            RECIPIENT_USER_ID,
            StudentType.INTERNATIONAL,
        ),
    )


def _current(participants: LockedBuddyParticipants | None = None) -> VerifiedBuddyPrincipal:
    value = participants or _participants()
    return VerifiedBuddyPrincipal(
        user=value.recipient_user,
        profile=value.recipient_profile,
    )


def _principals() -> tuple[EligibleMatchingPrincipal, EligibleMatchingPrincipal]:
    return (
        EligibleMatchingPrincipal(
            user_id=SENDER_USER_ID,
            profile_id=SENDER_PROFILE_ID,
            student_type=StudentType.VIETNAMESE,
        ),
        EligibleMatchingPrincipal(
            user_id=RECIPIENT_USER_ID,
            profile_id=RECIPIENT_PROFILE_ID,
            student_type=StudentType.INTERNATIONAL,
        ),
    )


def _session(*scalar_values: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=scalar_values)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install_happy_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    participants: LockedBuddyParticipants,
) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    sender, recipient = _principals()
    monkeypatch.setattr(
        acceptance,
        "lock_buddy_match_participants",
        AsyncMock(return_value=participants),
    )
    monkeypatch.setattr(
        acceptance,
        "get_eligible_matching_principal",
        AsyncMock(side_effect=[sender, recipient]),
    )
    monkeypatch.setattr(
        acceptance,
        "load_matching_pair_scoring_profiles",
        AsyncMock(return_value=(SimpleNamespace(), SimpleNamespace())),
    )
    monkeypatch.setattr(acceptance, "score_eligible_pair", MagicMock(return_value=object()))
    activate = AsyncMock(return_value=BuddyMatch(id=MATCH_ID))
    conversation = AsyncMock(return_value=BuddyConversation(id=CONVERSATION_ID))
    enqueue = AsyncMock()
    monkeypatch.setattr(acceptance, "activate_buddy_match", activate)
    monkeypatch.setattr(acceptance, "get_or_create_buddy_conversation", conversation)
    monkeypatch.setattr(acceptance, "enqueue_transactional_email", enqueue)
    return activate, conversation, enqueue


@pytest.mark.anyio
async def test_accept_stages_transition_match_conversation_and_one_safe_event_without_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invitation = _invitation()
    participants = _participants()
    mock, session = _session(invitation, invitation)
    activate, conversation, enqueue = _install_happy_dependencies(monkeypatch, participants)

    result = await accept_matching_invitation(
        session,
        _current(participants),
        invitation_id=INVITATION_ID,
        clock=lambda: NOW,
    )

    assert result.invitation_id == INVITATION_ID
    assert result.match_id == MATCH_ID
    assert result.conversation_id == CONVERSATION_ID
    assert result.status is InvitationStatus.ACCEPTED
    assert invitation.status is InvitationStatus.ACCEPTED
    assert invitation.responded_at == NOW
    locked_reload = mock.scalar.await_args_list[1].args[0]
    assert locked_reload.get_execution_options()["populate_existing"] is True
    assert "for update" in str(locked_reload).lower()
    activate.assert_awaited_once()
    assert activate.await_args is not None
    assert activate.await_args.kwargs["locked_participants"] is participants
    conversation.assert_awaited_once_with(
        session,
        match_id=MATCH_ID,
        clock=ANY,
    )
    enqueue.assert_awaited_once_with(
        session,
        event_type=MATCHING_INVITATION_ACCEPTED,
        aggregate_id=INVITATION_ID,
        recipient_user_id=SENDER_USER_ID,
        recipient_email="sender@example.invalid",
        idempotency_key=f"matching-invitation-accepted:{INVITATION_ID}",
        payload={
            "invitation_id": str(INVITATION_ID),
            "match_id": str(MATCH_ID),
            "conversation_id": str(CONVERSATION_ID),
        },
        clock=ANY,
    )
    mock.commit.assert_not_called()
    mock.rollback.assert_not_called()


@pytest.mark.anyio
async def test_accepted_replay_returns_stable_result_without_duplicate_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invitation = _invitation(InvitationStatus.ACCEPTED)
    buddy_match = BuddyMatch(id=MATCH_ID, accepted_invitation_id=INVITATION_ID)
    conversation = BuddyConversation(id=CONVERSATION_ID, match_id=MATCH_ID)
    mock, session = _session(invitation, buddy_match, conversation)
    activate = AsyncMock()
    enqueue = AsyncMock()
    monkeypatch.setattr(acceptance, "activate_buddy_match", activate)
    monkeypatch.setattr(acceptance, "enqueue_transactional_email", enqueue)

    result = await accept_matching_invitation(
        session,
        _current(),
        invitation_id=INVITATION_ID,
        clock=lambda: NOW,
    )

    assert (result.match_id, result.conversation_id) == (MATCH_ID, CONVERSATION_ID)
    activate.assert_not_awaited()
    enqueue.assert_not_awaited()
    assert mock.scalar.await_count == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("invitation", "reason"),
    (
        (_invitation(InvitationStatus.DECLINED), InvitationAcceptReason.NOT_PENDING),
        (_invitation(InvitationStatus.CANCELLED), InvitationAcceptReason.NOT_PENDING),
        (_invitation(InvitationStatus.EXPIRED), InvitationAcceptReason.NOT_PENDING),
        (
            _invitation(expires_at=NOW),
            InvitationAcceptReason.EXPIRED,
        ),
    ),
)
async def test_terminal_and_effectively_expired_rows_never_create_relationship(
    invitation: MatchingInvitation,
    reason: InvitationAcceptReason,
) -> None:
    mock, session = _session(invitation)

    with pytest.raises(InvitationAcceptError) as raised:
        await accept_matching_invitation(
            session,
            _current(),
            invitation_id=INVITATION_ID,
            clock=lambda: NOW,
        )

    assert raised.value.reason is reason
    mock.add.assert_not_called()


@pytest.mark.anyio
async def test_foreign_or_missing_invitation_is_indistinguishable() -> None:
    mock, session = _session(None)

    with pytest.raises(InvitationAcceptError) as raised:
        await accept_matching_invitation(
            session,
            _current(),
            invitation_id=INVITATION_ID,
            clock=lambda: NOW,
        )

    assert raised.value.reason is InvitationAcceptReason.NOT_FOUND
    statement = str(mock.scalar.await_args.args[0]).lower()
    assert "recipient_id" in statement
    assert "for update" not in statement


@pytest.mark.anyio
async def test_locked_recipient_eligibility_is_revalidated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invitation = _invitation()
    participants = _participants()
    _mock, session = _session(invitation)
    monkeypatch.setattr(
        acceptance,
        "lock_buddy_match_participants",
        AsyncMock(return_value=participants),
    )
    monkeypatch.setattr(
        acceptance,
        "get_eligible_matching_principal",
        AsyncMock(
            side_effect=[
                _principals()[0],
                BuddyCapabilityError(),
            ]
        ),
    )

    with pytest.raises(InvitationAcceptError) as raised:
        await accept_matching_invitation(
            session,
            _current(participants),
            invitation_id=INVITATION_ID,
            clock=lambda: NOW,
        )

    assert raised.value.reason is InvitationAcceptReason.RECIPIENT_INELIGIBLE


@pytest.mark.anyio
async def test_match_conflict_and_conversation_failure_stop_outbox_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invitation = _invitation()
    participants = _participants()
    _mock, session = _session(invitation, invitation)
    activate, conversation, enqueue = _install_happy_dependencies(monkeypatch, participants)
    activate.side_effect = BuddyMatchActivationError(BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS)

    with pytest.raises(InvitationAcceptError) as raised:
        await accept_matching_invitation(
            session,
            _current(participants),
            invitation_id=INVITATION_ID,
            clock=lambda: NOW,
        )

    assert raised.value.reason is InvitationAcceptReason.ACTIVE_PAIR_EXISTS
    conversation.assert_not_awaited()
    enqueue.assert_not_awaited()

    second_invitation = _invitation()
    _mock, second_session = _session(second_invitation, second_invitation)
    _activate, second_conversation, second_enqueue = _install_happy_dependencies(
        monkeypatch,
        participants,
    )
    second_conversation.side_effect = RuntimeError("injected conversation failure")
    with pytest.raises(RuntimeError, match="injected conversation failure"):
        await accept_matching_invitation(
            second_session,
            _current(participants),
            invitation_id=INVITATION_ID,
            clock=lambda: NOW,
        )
    second_enqueue.assert_not_awaited()
