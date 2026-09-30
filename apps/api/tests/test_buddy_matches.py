"""BUDDY-001 activation policy, locking, snapshot, and conflict tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InvitationStatus,
    MatchingInvitation,
    MatchStatus,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.services.buddy_matches import (
    BuddyMatchActivationError,
    BuddyMatchActivationReason,
    activate_buddy_match,
    compatibility_score_snapshot,
)
from app.services.matching_scoring import (
    CompatibilityBreakdown,
    CompatibilityScore,
    CompatibilitySignalBreakdown,
)

NOW = datetime(2026, 9, 30, 1, 0, tzinfo=UTC)
SENDER_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
SENDER_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
RECIPIENT_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
RECIPIENT_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")


class _ScalarRows:
    def __init__(self, rows: tuple[object, ...]) -> None:
        self._rows = rows

    def all(self) -> tuple[object, ...]:
        return self._rows


def _compatibility() -> CompatibilityScore:
    interests = CompatibilitySignalBreakdown(Fraction(1), 40, Fraction(40))
    activities = CompatibilitySignalBreakdown(Fraction(1, 2), 35, Fraction(35, 2))
    availability = CompatibilitySignalBreakdown(Fraction(0), 15, Fraction(0))
    languages = CompatibilitySignalBreakdown(Fraction(1), 5, Fraction(5))
    major = CompatibilitySignalBreakdown(Fraction(0), 5, Fraction(0))
    return CompatibilityScore(
        precise_score=Fraction(125, 2),
        score=63,
        breakdown=CompatibilityBreakdown(
            interests=interests,
            activities=activities,
            availability=availability,
            languages=languages,
            major=major,
        ),
        reference_week_start=date(2026, 9, 28),
    )


def _invitation(status: InvitationStatus = InvitationStatus.ACCEPTED) -> MatchingInvitation:
    return MatchingInvitation(
        id=INVITATION_ID,
        sender_id=SENDER_USER_ID,
        recipient_id=RECIPIENT_USER_ID,
        message="Accepted invitation",
        status=status,
        created_at=NOW - timedelta(hours=1),
        updated_at=NOW,
        expires_at=NOW + timedelta(days=7),
        responded_at=NOW if status is InvitationStatus.ACCEPTED else None,
    )


def _user(user_id: UUID) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.invalid",
        password_hash="test-only-hash",
        role=UserRole.USER,
        is_active=True,
    )


def _profile(
    profile_id: UUID,
    user_id: UUID,
    student_type: StudentType,
) -> StudentProfile:
    return StudentProfile(
        id=profile_id,
        user_id=user_id,
        full_name="Test Participant",
        student_type=student_type,
    )


def _session(
    *,
    invitation: MatchingInvitation,
    sender_type: StudentType = StudentType.VIETNAMESE,
    recipient_type: StudentType = StudentType.INTERNATIONAL,
    existing_match_id: UUID | None = None,
) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[invitation, invitation, existing_match_id])
    mock.scalars = AsyncMock(
        side_effect=[
            _ScalarRows((_user(SENDER_USER_ID), _user(RECIPIENT_USER_ID))),
            _ScalarRows(
                (
                    _profile(SENDER_PROFILE_ID, SENDER_USER_ID, sender_type),
                    _profile(RECIPIENT_PROFILE_ID, RECIPIENT_USER_ID, recipient_type),
                )
            ),
        ]
    )
    mock.flush = AsyncMock()
    nested = MagicMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=None)
    mock.begin_nested.return_value = nested
    return mock, cast(AsyncSession, mock)


def test_score_snapshot_contains_only_numeric_public_breakdown() -> None:
    snapshot = compatibility_score_snapshot(_compatibility())

    assert snapshot["reference_week_start"] == "2026-09-28"
    assert snapshot["interests"] == {"similarity": 1.0, "weight": 40, "points": 40.0}
    rendered = repr(snapshot).lower()
    for forbidden in (
        "email",
        "user_id",
        "profile_id",
        "normalized_key",
        "object_key",
        "message",
    ):
        assert forbidden not in rendered


@pytest.mark.anyio
async def test_activation_creates_one_active_match_without_committing() -> None:
    mock, session = _session(invitation=_invitation())

    result = await activate_buddy_match(
        session,
        accepted_invitation_id=INVITATION_ID,
        compatibility=_compatibility(),
        clock=lambda: NOW,
    )

    assert result.status is MatchStatus.ACTIVE
    assert result.participant_one_user_id == SENDER_USER_ID
    assert result.participant_two_user_id == RECIPIENT_USER_ID
    assert result.participant_one_profile_id == SENDER_PROFILE_ID
    assert result.participant_two_profile_id == RECIPIENT_PROFILE_ID
    assert result.accepted_invitation_id == INVITATION_ID
    assert result.score == 63
    assert result.activated_at == NOW
    assert mock.scalars.await_count == 2
    statements = [str(call.args[0]).lower() for call in mock.scalars.await_args_list]
    assert all("order by" in statement and "for update" in statement for statement in statements)
    scalar_statements = [str(call.args[0]).lower() for call in mock.scalar.await_args_list]
    assert "for update" not in scalar_statements[0]
    assert "for update" in scalar_statements[1]
    assert "for update" in scalar_statements[2]
    mock.add.assert_called_once_with(result)
    mock.flush.assert_awaited_once()
    mock.commit.assert_not_called()


@pytest.mark.anyio
async def test_activation_requires_accepted_invitation_before_participant_queries() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=_invitation(InvitationStatus.PENDING))

    with pytest.raises(BuddyMatchActivationError) as raised:
        await activate_buddy_match(
            cast(AsyncSession, mock),
            accepted_invitation_id=INVITATION_ID,
            compatibility=_compatibility(),
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMatchActivationReason.INVITATION_NOT_ACCEPTED
    mock.scalars.assert_not_called()
    mock.add.assert_not_called()


@pytest.mark.anyio
async def test_activation_revalidates_invitation_after_participant_locks() -> None:
    accepted = _invitation()
    changed = _invitation(InvitationStatus.PENDING)
    mock, session = _session(invitation=accepted)
    mock.scalar = AsyncMock(side_effect=[accepted, changed])

    with pytest.raises(BuddyMatchActivationError) as raised:
        await activate_buddy_match(
            session,
            accepted_invitation_id=INVITATION_ID,
            compatibility=_compatibility(),
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMatchActivationReason.INVITATION_NOT_ACCEPTED
    assert mock.scalars.await_count == 2
    mock.add.assert_not_called()


@pytest.mark.anyio
async def test_activation_rejects_same_type_under_locked_profiles() -> None:
    mock, session = _session(
        invitation=_invitation(),
        sender_type=StudentType.VIETNAMESE,
        recipient_type=StudentType.VIETNAMESE,
    )

    with pytest.raises(BuddyMatchActivationError) as raised:
        await activate_buddy_match(
            session,
            accepted_invitation_id=INVITATION_ID,
            compatibility=_compatibility(),
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMatchActivationReason.OPPOSITE_TYPES_REQUIRED
    mock.add.assert_not_called()


@pytest.mark.anyio
async def test_activation_rejects_existing_active_unordered_pair() -> None:
    mock, session = _session(
        invitation=_invitation(),
        existing_match_id=UUID("40000000-0000-4000-8000-000000000001"),
    )

    with pytest.raises(BuddyMatchActivationError) as raised:
        await activate_buddy_match(
            session,
            accepted_invitation_id=INVITATION_ID,
            compatibility=_compatibility(),
            clock=lambda: NOW,
        )

    assert raised.value.reason is BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS
    mock.add.assert_not_called()


@pytest.mark.anyio
async def test_activation_rejects_naive_clock_before_database_access() -> None:
    mock = MagicMock(spec=AsyncSession)

    with pytest.raises(ValueError, match="timezone-aware"):
        await activate_buddy_match(
            cast(AsyncSession, mock),
            accepted_invitation_id=INVITATION_ID,
            compatibility=_compatibility(),
            clock=lambda: datetime(2026, 9, 30, 1, 0),
        )

    mock.scalar.assert_not_called()
