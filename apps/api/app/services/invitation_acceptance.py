"""Atomic recipient-owned invitation acceptance orchestration for INV-005."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BuddyConversation,
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
)
from app.services.buddy_access import BuddyCapabilityError, VerifiedBuddyPrincipal
from app.services.buddy_chat import get_or_create_buddy_conversation
from app.services.buddy_matches import (
    BuddyMatchActivationError,
    BuddyMatchActivationReason,
    activate_buddy_match,
    lock_buddy_match_participants,
)
from app.services.email_outbox import enqueue_transactional_email
from app.services.invitation_expiry import effective_invitation_status
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    get_eligible_matching_principal,
    load_matching_pair_scoring_profiles,
    matching_pair_is_eligible,
)
from app.services.matching_recommendations import current_reference_week_start
from app.services.matching_scoring import score_eligible_pair

MATCHING_INVITATION_ACCEPTED = "MATCHING_INVITATION_ACCEPTED"
Clock = Callable[[], datetime]


class InvitationAcceptReason(StrEnum):
    """Stable, privacy-safe reasons returned by the recipient Accept endpoint."""

    NOT_FOUND = "INVITATION_ACCEPT_NOT_FOUND"
    EXPIRED = "INVITATION_ACCEPT_EXPIRED"
    NOT_PENDING = "INVITATION_ACCEPT_NOT_PENDING"
    RECIPIENT_INELIGIBLE = "INVITATION_ACCEPT_RECIPIENT_INELIGIBLE"
    PARTICIPANT_INELIGIBLE = "INVITATION_ACCEPT_PARTICIPANT_INELIGIBLE"
    OPPOSITE_TYPES_REQUIRED = "INVITATION_ACCEPT_OPPOSITE_TYPES_REQUIRED"
    ACTIVE_PAIR_EXISTS = "INVITATION_ACCEPT_ACTIVE_PAIR_EXISTS"
    STATE_CONFLICT = "INVITATION_ACCEPT_STATE_CONFLICT"


class InvitationAcceptError(RuntimeError):
    """Sanitized domain rejection without invitation, participant, or SQL details."""

    def __init__(self, reason: InvitationAcceptReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class InvitationAcceptanceResult:
    """Minimal stable receipt for a newly accepted or safely replayed request."""

    invitation_id: UUID
    match_id: UUID
    conversation_id: UUID
    status: InvitationStatus = InvitationStatus.ACCEPTED


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invitation acceptance timestamps must be timezone-aware.")
    return value.astimezone(UTC)


async def _load_owned_invitation(
    session: AsyncSession,
    *,
    invitation_id: UUID,
    recipient_user_id: UUID,
    for_update: bool = False,
) -> MatchingInvitation:
    statement = select(MatchingInvitation).where(
        MatchingInvitation.id == invitation_id,
        MatchingInvitation.recipient_id == recipient_user_id,
        MatchingInvitation.deleted_at.is_(None),
    )
    if for_update:
        # Refresh an identity-map row after waiting on a concurrent winner. Without
        # this, SQLAlchemy can return the request's stale observed PENDING object even
        # though PostgreSQL locked and returned the now-ACCEPTED row.
        statement = statement.with_for_update().execution_options(populate_existing=True)
    invitation = await session.scalar(statement)
    if invitation is None:
        raise InvitationAcceptError(InvitationAcceptReason.NOT_FOUND)
    return invitation


async def _load_completed_result(
    session: AsyncSession,
    invitation: MatchingInvitation,
) -> InvitationAcceptanceResult:
    buddy_match = await session.scalar(
        select(BuddyMatch).where(
            BuddyMatch.accepted_invitation_id == invitation.id,
            BuddyMatch.deleted_at.is_(None),
        )
    )
    if buddy_match is None:
        raise InvitationAcceptError(InvitationAcceptReason.STATE_CONFLICT)
    conversation = await session.scalar(
        select(BuddyConversation).where(BuddyConversation.match_id == buddy_match.id)
    )
    if conversation is None:
        raise InvitationAcceptError(InvitationAcceptReason.STATE_CONFLICT)
    return InvitationAcceptanceResult(
        invitation_id=invitation.id,
        match_id=buddy_match.id,
        conversation_id=conversation.id,
    )


def _map_activation_error(error: BuddyMatchActivationError) -> InvitationAcceptError:
    reasons = {
        BuddyMatchActivationReason.PARTICIPANT_STATE_INVALID: (
            InvitationAcceptReason.PARTICIPANT_INELIGIBLE
        ),
        BuddyMatchActivationReason.OPPOSITE_TYPES_REQUIRED: (
            InvitationAcceptReason.OPPOSITE_TYPES_REQUIRED
        ),
        BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS: InvitationAcceptReason.ACTIVE_PAIR_EXISTS,
        BuddyMatchActivationReason.INVITATION_NOT_ACCEPTED: InvitationAcceptReason.STATE_CONFLICT,
    }
    return InvitationAcceptError(reasons[error.reason])


async def _require_current_eligibility(
    session: AsyncSession,
    principal: VerifiedBuddyPrincipal,
    *,
    recipient: bool,
) -> EligibleMatchingPrincipal:
    try:
        return await get_eligible_matching_principal(session, principal)
    except BuddyCapabilityError:
        reason = (
            InvitationAcceptReason.RECIPIENT_INELIGIBLE
            if recipient
            else InvitationAcceptReason.PARTICIPANT_INELIGIBLE
        )
        raise InvitationAcceptError(reason) from None


async def accept_matching_invitation(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    invitation_id: UUID,
    clock: Clock = _system_utc_now,
) -> InvitationAcceptanceResult:
    """Accept once and atomically stage its Match, conversation, and outbox event.

    The caller owns commit/rollback. All locks follow USER then profile then invitation
    order, matching the student-type update and BUDDY-001 activation policy.
    """
    observed = await _load_owned_invitation(
        session,
        invitation_id=invitation_id,
        recipient_user_id=current.user.id,
    )
    if observed.status is InvitationStatus.ACCEPTED:
        return await _load_completed_result(session, observed)
    if observed.status is not InvitationStatus.PENDING:
        raise InvitationAcceptError(InvitationAcceptReason.NOT_PENDING)
    if effective_invitation_status(observed, at=_utc_now(clock)) is InvitationStatus.EXPIRED:
        raise InvitationAcceptError(InvitationAcceptReason.EXPIRED)

    try:
        participants = await lock_buddy_match_participants(
            session,
            invitation=observed,
        )
    except BuddyMatchActivationError as error:
        raise _map_activation_error(error) from None

    sender = await _require_current_eligibility(
        session,
        VerifiedBuddyPrincipal(
            user=participants.sender_user,
            profile=participants.sender_profile,
        ),
        recipient=False,
    )
    recipient = await _require_current_eligibility(
        session,
        VerifiedBuddyPrincipal(
            user=participants.recipient_user,
            profile=participants.recipient_profile,
        ),
        recipient=True,
    )
    if recipient.user_id != current.user.id:
        raise InvitationAcceptError(InvitationAcceptReason.NOT_FOUND)
    if not matching_pair_is_eligible(sender, recipient):
        raise InvitationAcceptError(InvitationAcceptReason.OPPOSITE_TYPES_REQUIRED)

    invitation = await _load_owned_invitation(
        session,
        invitation_id=invitation_id,
        recipient_user_id=current.user.id,
        for_update=True,
    )
    if invitation.sender_id != observed.sender_id:
        raise InvitationAcceptError(InvitationAcceptReason.STATE_CONFLICT)
    if invitation.status is InvitationStatus.ACCEPTED:
        return await _load_completed_result(session, invitation)
    if invitation.status is not InvitationStatus.PENDING:
        raise InvitationAcceptError(InvitationAcceptReason.NOT_PENDING)

    accepted_at = _utc_now(clock)
    if effective_invitation_status(invitation, at=accepted_at) is InvitationStatus.EXPIRED:
        raise InvitationAcceptError(InvitationAcceptReason.EXPIRED)

    scoring_profiles = await load_matching_pair_scoring_profiles(
        session,
        sender,
        recipient,
        locale="en",
    )
    if scoring_profiles is None:
        raise InvitationAcceptError(InvitationAcceptReason.PARTICIPANT_INELIGIBLE)
    compatibility = score_eligible_pair(
        sender,
        recipient,
        scoring_profiles[0],
        scoring_profiles[1],
        reference_week_start=current_reference_week_start(accepted_at),
    )

    invitation.accept(at=accepted_at)
    try:
        buddy_match = await activate_buddy_match(
            session,
            accepted_invitation_id=invitation.id,
            compatibility=compatibility,
            locked_participants=participants,
            clock=lambda: accepted_at,
        )
    except BuddyMatchActivationError as error:
        raise _map_activation_error(error) from None
    conversation = await get_or_create_buddy_conversation(
        session,
        match_id=buddy_match.id,
        clock=lambda: accepted_at,
    )
    await enqueue_transactional_email(
        session,
        event_type=MATCHING_INVITATION_ACCEPTED,
        aggregate_id=invitation.id,
        recipient_user_id=participants.sender_user.id,
        recipient_email=participants.sender_user.email,
        idempotency_key=f"matching-invitation-accepted:{invitation.id}",
        payload={
            "invitation_id": str(invitation.id),
            "match_id": str(buddy_match.id),
            "conversation_id": str(conversation.id),
        },
        clock=lambda: accepted_at,
    )
    return InvitationAcceptanceResult(
        invitation_id=invitation.id,
        match_id=buddy_match.id,
        conversation_id=conversation.id,
    )
