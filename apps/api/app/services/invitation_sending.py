"""Atomic, privacy-safe invitation creation policy for INV-003."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    MAX_INVITATION_MESSAGE_CODE_POINTS,
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
    MatchStatus,
    StudentProfile,
    User,
    UserRole,
    canonical_user_pair,
    invitation_expires_at,
)
from app.services.buddy_access import BuddyCapabilityError, VerifiedBuddyPrincipal
from app.services.email_outbox import enqueue_transactional_email
from app.services.invitation_expiry import effective_pending_predicate
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    get_eligible_matching_principal,
    matching_pair_is_eligible,
)

MAX_INVITATION_MESSAGE_WORDS: Final = 500
MAX_OUTGOING_PENDING_INVITATIONS: Final = 30
MATCHING_INVITATION_CREATED: Final = "MATCHING_INVITATION_CREATED"
_UNIQUE_VIOLATION_SQLSTATE: Final = "23505"
_WORD_RUN: Final = re.compile(r"\S+")

Clock = Callable[[], datetime]


class InvitationSendReason(StrEnum):
    """Stable, sanitized reason codes returned by the invitation POST endpoint."""

    MESSAGE_TOO_MANY_WORDS = "INVITATION_MESSAGE_TOO_MANY_WORDS"
    MESSAGE_TOO_MANY_CODE_POINTS = "INVITATION_MESSAGE_TOO_MANY_CODE_POINTS"
    SELF_NOT_ALLOWED = "INVITATION_SELF_NOT_ALLOWED"
    SENDER_INELIGIBLE = "INVITATION_SENDER_INELIGIBLE"
    RECIPIENT_INELIGIBLE = "INVITATION_RECIPIENT_INELIGIBLE"
    PENDING_LIMIT_REACHED = "INVITATION_PENDING_LIMIT_REACHED"
    PENDING_EXISTS = "INVITATION_PENDING_EXISTS"
    ACTIVE_PAIR_EXISTS = "INVITATION_ACTIVE_PAIR_EXISTS"


class InvitationSendError(RuntimeError):
    """Domain rejection that carries no submitted or persisted private value."""

    def __init__(self, reason: InvitationSendReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class CanonicalInvitationMessage:
    """Canonical plain text and counts shared with frontend validation fixtures."""

    value: str = field(repr=False)
    word_count: int
    code_point_count: int


def canonicalize_invitation_message(message: str) -> CanonicalInvitationMessage:
    """Trim outer whitespace and enforce Unicode code-point/maximal-run limits.

    Python ``len`` counts Unicode code points, unlike JavaScript ``String.length``.
    ``\\S+`` is the contract's maximal consecutive non-whitespace run algorithm.
    """
    canonical = message.strip()
    code_point_count = len(canonical)
    if code_point_count > MAX_INVITATION_MESSAGE_CODE_POINTS:
        raise InvitationSendError(InvitationSendReason.MESSAGE_TOO_MANY_CODE_POINTS)
    word_count = sum(1 for _match in _WORD_RUN.finditer(canonical))
    if word_count > MAX_INVITATION_MESSAGE_WORDS:
        raise InvitationSendError(InvitationSendReason.MESSAGE_TOO_MANY_WORDS)
    return CanonicalInvitationMessage(
        value=canonical,
        word_count=word_count,
        code_point_count=code_point_count,
    )


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invitation timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _is_available_user(user: User | None) -> bool:
    return bool(
        user is not None
        and user.role is UserRole.USER
        and user.is_active
        and user.deleted_at is None
        and user.email_verified_at is not None
    )


async def _lock_and_revalidate_pair(
    session: AsyncSession,
    *,
    sender_user_id: UUID,
    recipient_profile_id: UUID,
) -> tuple[User, User, EligibleMatchingPrincipal, EligibleMatchingPrincipal]:
    """Lock both identities in canonical order before rechecking current eligibility."""
    recipient_user_id = await session.scalar(
        select(StudentProfile.user_id).where(
            StudentProfile.id == recipient_profile_id,
            StudentProfile.deleted_at.is_(None),
        )
    )
    if recipient_user_id is None:
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE)
    if recipient_user_id == sender_user_id:
        raise InvitationSendError(InvitationSendReason.SELF_NOT_ALLOWED)

    participant_ids = tuple(
        sorted((sender_user_id, recipient_user_id), key=lambda value: value.int)
    )
    users = tuple(
        (
            await session.scalars(
                select(User)
                .where(User.id.in_(participant_ids))
                .order_by(User.id)
                .with_for_update()
            )
        ).all()
    )
    users_by_id = {user.id: user for user in users}
    sender_user = users_by_id.get(sender_user_id)
    recipient_user = users_by_id.get(recipient_user_id)
    if not _is_available_user(sender_user):
        raise InvitationSendError(InvitationSendReason.SENDER_INELIGIBLE)
    if not _is_available_user(recipient_user):
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE)
    assert sender_user is not None
    assert recipient_user is not None
    if sender_user.semester_id is None:
        raise InvitationSendError(InvitationSendReason.SENDER_INELIGIBLE)
    if (
        recipient_user.semester_id is None
        or recipient_user.semester_id != sender_user.semester_id
    ):
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE)

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
    sender_profile = profiles_by_user_id.get(sender_user_id)
    recipient_profile = profiles_by_user_id.get(recipient_user_id)
    if sender_profile is None or sender_profile.deleted_at is not None:
        raise InvitationSendError(InvitationSendReason.SENDER_INELIGIBLE)
    if (
        recipient_profile is None
        or recipient_profile.id != recipient_profile_id
        or recipient_profile.deleted_at is not None
    ):
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE)

    try:
        sender = await get_eligible_matching_principal(
            session,
            VerifiedBuddyPrincipal(user=sender_user, profile=sender_profile),
        )
    except BuddyCapabilityError:
        raise InvitationSendError(InvitationSendReason.SENDER_INELIGIBLE) from None
    try:
        recipient = await get_eligible_matching_principal(
            session,
            VerifiedBuddyPrincipal(user=recipient_user, profile=recipient_profile),
        )
    except BuddyCapabilityError:
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE) from None
    if not matching_pair_is_eligible(sender, recipient):
        raise InvitationSendError(InvitationSendReason.RECIPIENT_INELIGIBLE)
    return sender_user, recipient_user, sender, recipient


async def _expire_or_reject_pending_pair(
    session: AsyncSession,
    *,
    sender_user_id: UUID,
    recipient_user_id: UUID,
    at: datetime,
) -> None:
    pair_low, pair_high = canonical_user_pair(sender_user_id, recipient_user_id)
    pending = await session.scalar(
        select(MatchingInvitation)
        .where(
            MatchingInvitation.pair_low_user_id == pair_low,
            MatchingInvitation.pair_high_user_id == pair_high,
            MatchingInvitation.status == InvitationStatus.PENDING,
        )
        .with_for_update()
    )
    if pending is None:
        return
    if pending.expires_at > at:
        raise InvitationSendError(InvitationSendReason.PENDING_EXISTS)
    pending.expire(at=at)
    await session.flush()


async def _reject_active_pair(
    session: AsyncSession,
    *,
    sender_user_id: UUID,
    recipient_user_id: UUID,
) -> None:
    """Reject only the authoritative ACTIVE Match, never invitation history alone."""
    pair_low, pair_high = canonical_user_pair(sender_user_id, recipient_user_id)
    active_match_id = await session.scalar(
        select(BuddyMatch.id).where(
            BuddyMatch.pair_low_user_id == pair_low,
            BuddyMatch.pair_high_user_id == pair_high,
            BuddyMatch.status == MatchStatus.ACTIVE,
        )
    )
    if active_match_id is not None:
        raise InvitationSendError(InvitationSendReason.ACTIVE_PAIR_EXISTS)


async def _require_pending_capacity(
    session: AsyncSession,
    *,
    sender_user_id: UUID,
    at: datetime,
) -> None:
    pending_count = await session.scalar(
        select(func.count(MatchingInvitation.id)).where(
            MatchingInvitation.sender_id == sender_user_id,
            effective_pending_predicate(at=at),
        )
    )
    if int(pending_count or 0) >= MAX_OUTGOING_PENDING_INVITATIONS:
        raise InvitationSendError(InvitationSendReason.PENDING_LIMIT_REACHED)


def _is_unique_violation(error: IntegrityError) -> bool:
    return getattr(error.orig, "sqlstate", None) == _UNIQUE_VIOLATION_SQLSTATE


async def send_matching_invitation(
    session: AsyncSession,
    sender: EligibleMatchingPrincipal,
    *,
    recipient_profile_id: UUID,
    message: str,
    clock: Clock = _system_utc_now,
) -> MatchingInvitation:
    """Create one invitation and its email event inside the caller's transaction."""
    canonical_message = canonicalize_invitation_message(message)
    current_time = _utc_now(clock)
    _sender_user, recipient_user, locked_sender, locked_recipient = (
        await _lock_and_revalidate_pair(
            session,
            sender_user_id=sender.user_id,
            recipient_profile_id=recipient_profile_id,
        )
    )
    await _expire_or_reject_pending_pair(
        session,
        sender_user_id=locked_sender.user_id,
        recipient_user_id=locked_recipient.user_id,
        at=current_time,
    )
    await _reject_active_pair(
        session,
        sender_user_id=locked_sender.user_id,
        recipient_user_id=locked_recipient.user_id,
    )
    await _require_pending_capacity(
        session,
        sender_user_id=locked_sender.user_id,
        at=current_time,
    )

    invitation = MatchingInvitation(
        sender_id=locked_sender.user_id,
        recipient_id=locked_recipient.user_id,
        message=canonical_message.value,
        status=InvitationStatus.PENDING,
        expires_at=invitation_expires_at(current_time),
        created_at=current_time,
        updated_at=current_time,
    )
    try:
        async with session.begin_nested():
            session.add(invitation)
            await session.flush()
    except IntegrityError as error:
        if _is_unique_violation(error):
            raise InvitationSendError(InvitationSendReason.PENDING_EXISTS) from None
        raise

    await enqueue_transactional_email(
        session,
        event_type=MATCHING_INVITATION_CREATED,
        aggregate_id=invitation.id,
        recipient_user_id=recipient_user.id,
        recipient_email=recipient_user.email,
        idempotency_key=f"matching-invitation-created:{invitation.id}",
        payload={"invitation_id": str(invitation.id)},
        clock=lambda: current_time,
    )
    return invitation
