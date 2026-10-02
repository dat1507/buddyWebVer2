"""Concurrency-safe ACTIVE Buddy Match activation foundation for BUDDY-001."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
    MatchStatus,
    StudentProfile,
    StudentType,
    User,
    canonical_user_pair,
)
from app.services.buddy_match_policy import (
    BuddyParticipantStateError,
    lock_current_buddy_users,
)
from app.services.matching_recommendations import project_compatibility_explanation
from app.services.matching_scoring import CompatibilityScore

_UNIQUE_VIOLATION_SQLSTATE = "23505"
Clock = Callable[[], datetime]


class BuddyMatchActivationReason(StrEnum):
    """Stable internal rejection reasons for future INV-005 conflict mapping."""

    INVITATION_NOT_ACCEPTED = "MATCH_INVITATION_NOT_ACCEPTED"
    PARTICIPANT_STATE_INVALID = "MATCH_PARTICIPANT_STATE_INVALID"
    OPPOSITE_TYPES_REQUIRED = "MATCH_OPPOSITE_TYPES_REQUIRED"
    ACTIVE_PAIR_EXISTS = "MATCH_ACTIVE_PAIR_EXISTS"


class BuddyMatchActivationError(RuntimeError):
    """Sanitized activation rejection without participant or score details."""

    def __init__(self, reason: BuddyMatchActivationReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class LockedBuddyParticipants:
    """Canonical participant locks shared by Match activation and invitation Accept."""

    sender_user: User = field(repr=False)
    recipient_user: User = field(repr=False)
    sender_profile: StudentProfile = field(repr=False)
    recipient_profile: StudentProfile = field(repr=False)


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Buddy Match activation timestamp must be timezone-aware.")
    return value.astimezone(UTC)


def compatibility_score_snapshot(score: CompatibilityScore) -> dict[str, object]:
    """Persist only public numeric REC-002 explanation data and its reference week."""
    explanation = project_compatibility_explanation(score).model_dump(mode="json")
    return {
        "reference_week_start": score.reference_week_start.isoformat(),
        **cast(dict[str, object], explanation),
    }


async def lock_buddy_match_participants(
    session: AsyncSession,
    *,
    invitation: MatchingInvitation,
) -> LockedBuddyParticipants:
    """Lock USER then profile rows in the shared canonical order and revalidate types."""
    participant_ids = canonical_user_pair(invitation.sender_id, invitation.recipient_id)
    try:
        users = await lock_current_buddy_users(session, participant_ids)
    except BuddyParticipantStateError:
        raise BuddyMatchActivationError(
            BuddyMatchActivationReason.PARTICIPANT_STATE_INVALID
        ) from None

    profiles = tuple(
        (
            await session.scalars(
                select(StudentProfile)
                .where(StudentProfile.user_id.in_(participant_ids))
                .order_by(StudentProfile.user_id)
                .with_for_update()
            )
        ).all()
    )
    profiles_by_user_id = {profile.user_id: profile for profile in profiles}
    users_by_id = {user.id: user for user in users}
    sender_user = users_by_id.get(invitation.sender_id)
    recipient_user = users_by_id.get(invitation.recipient_id)
    sender_profile = profiles_by_user_id.get(invitation.sender_id)
    recipient_profile = profiles_by_user_id.get(invitation.recipient_id)
    if (
        sender_user is None
        or recipient_user is None
        or sender_profile is None
        or recipient_profile is None
        or sender_profile.deleted_at is not None
        or recipient_profile.deleted_at is not None
        or sender_user.semester_id is None
        or sender_user.semester_id != recipient_user.semester_id
    ):
        raise BuddyMatchActivationError(BuddyMatchActivationReason.PARTICIPANT_STATE_INVALID)
    if {sender_profile.student_type, recipient_profile.student_type} != {
        StudentType.VIETNAMESE,
        StudentType.INTERNATIONAL,
    }:
        raise BuddyMatchActivationError(BuddyMatchActivationReason.OPPOSITE_TYPES_REQUIRED)
    return LockedBuddyParticipants(
        sender_user=sender_user,
        recipient_user=recipient_user,
        sender_profile=sender_profile,
        recipient_profile=recipient_profile,
    )


async def _active_pair_exists(
    session: AsyncSession,
    *,
    first_user_id: UUID,
    second_user_id: UUID,
) -> bool:
    pair_low, pair_high = canonical_user_pair(first_user_id, second_user_id)
    match_id = await session.scalar(
        select(BuddyMatch.id)
        .where(
            BuddyMatch.pair_low_user_id == pair_low,
            BuddyMatch.pair_high_user_id == pair_high,
            BuddyMatch.status == MatchStatus.ACTIVE,
        )
        .with_for_update()
    )
    return match_id is not None


def _is_unique_violation(error: IntegrityError) -> bool:
    return getattr(error.orig, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE


async def activate_buddy_match(
    session: AsyncSession,
    *,
    accepted_invitation_id: UUID,
    compatibility: CompatibilityScore,
    locked_participants: LockedBuddyParticipants | None = None,
    clock: Clock = _system_utc_now,
) -> BuddyMatch:
    """Create one ACTIVE Match from an already accepted invitation without committing."""
    activated_at = _utc_now(clock)
    invitation = await session.scalar(
        select(MatchingInvitation).where(
            MatchingInvitation.id == accepted_invitation_id,
            MatchingInvitation.deleted_at.is_(None),
        )
    )
    if invitation is None or invitation.status is not InvitationStatus.ACCEPTED:
        raise BuddyMatchActivationError(BuddyMatchActivationReason.INVITATION_NOT_ACCEPTED)

    participants = locked_participants
    if participants is None:
        participants = await lock_buddy_match_participants(
            session,
            invitation=invitation,
        )
    elif (
        participants.sender_user.id != invitation.sender_id
        or participants.recipient_user.id != invitation.recipient_id
        or participants.sender_profile.user_id != invitation.sender_id
        or participants.recipient_profile.user_id != invitation.recipient_id
    ):
        raise BuddyMatchActivationError(BuddyMatchActivationReason.PARTICIPANT_STATE_INVALID)
    locked_invitation = await session.scalar(
        select(MatchingInvitation)
        .where(
            MatchingInvitation.id == accepted_invitation_id,
            MatchingInvitation.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if (
        locked_invitation is None
        or locked_invitation.status is not InvitationStatus.ACCEPTED
        or locked_invitation.sender_id != invitation.sender_id
        or locked_invitation.recipient_id != invitation.recipient_id
    ):
        raise BuddyMatchActivationError(BuddyMatchActivationReason.INVITATION_NOT_ACCEPTED)
    invitation = locked_invitation
    if await _active_pair_exists(
        session,
        first_user_id=invitation.sender_id,
        second_user_id=invitation.recipient_id,
    ):
        raise BuddyMatchActivationError(BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS)

    semester_id = participants.sender_user.semester_id
    if semester_id is None or semester_id != participants.recipient_user.semester_id:
        raise BuddyMatchActivationError(BuddyMatchActivationReason.PARTICIPANT_STATE_INVALID)

    buddy_match = BuddyMatch(
        participant_one_user_id=invitation.sender_id,
        participant_two_user_id=invitation.recipient_id,
        participant_one_profile_id=participants.sender_profile.id,
        participant_two_profile_id=participants.recipient_profile.id,
        status=MatchStatus.ACTIVE,
        accepted_invitation_id=invitation.id,
        semester_id=semester_id,
        score=compatibility.score,
        score_breakdown=compatibility_score_snapshot(compatibility),
        activated_at=activated_at,
        created_at=activated_at,
        updated_at=activated_at,
    )
    try:
        async with session.begin_nested():
            session.add(buddy_match)
            await session.flush()
    except IntegrityError as error:
        if _is_unique_violation(error):
            raise BuddyMatchActivationError(BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS) from None
        raise
    return buddy_match
