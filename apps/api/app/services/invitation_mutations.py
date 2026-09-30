"""Owner-scoped Decline, Cancel, and accepted-row hide mutations for INV-006."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InvitationStatus, MatchingInvitation
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_expiry import effective_invitation_status

Clock = Callable[[], datetime]
InvitationOwner = Literal["recipient", "sender"]


class InvitationMutationReason(StrEnum):
    """Stable, privacy-safe invitation mutation rejection reasons."""

    NOT_FOUND = "INVITATION_MUTATION_NOT_FOUND"
    EXPIRED = "INVITATION_MUTATION_EXPIRED"
    INVALID_STATE = "INVITATION_MUTATION_INVALID_STATE"


class InvitationMutationError(RuntimeError):
    """Sanitized mutation rejection without participant or persistence detail."""

    def __init__(self, reason: InvitationMutationReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class InvitationMutationResult:
    """Minimal stable receipt shared by all three owner mutations."""

    invitation_id: UUID
    status: InvitationStatus


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invitation mutation timestamps must be timezone-aware.")
    return value.astimezone(UTC)


async def _load_owned_invitation_for_update(
    session: AsyncSession,
    *,
    invitation_id: UUID,
    owner_user_id: UUID,
    owner: InvitationOwner,
) -> MatchingInvitation:
    owner_condition = (
        MatchingInvitation.recipient_id == owner_user_id
        if owner == "recipient"
        else MatchingInvitation.sender_id == owner_user_id
    )
    statement = (
        select(MatchingInvitation)
        .where(
            MatchingInvitation.id == invitation_id,
            owner_condition,
            MatchingInvitation.deleted_at.is_(None),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    invitation = await session.scalar(statement)
    if invitation is None:
        raise InvitationMutationError(InvitationMutationReason.NOT_FOUND)
    return invitation


def _result(invitation: MatchingInvitation) -> InvitationMutationResult:
    return InvitationMutationResult(
        invitation_id=invitation.id,
        status=invitation.status,
    )


async def decline_matching_invitation(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    invitation_id: UUID,
    clock: Clock = _system_utc_now,
) -> InvitationMutationResult:
    """Idempotently decline one effective-PENDING invitation as its recipient."""
    invitation = await _load_owned_invitation_for_update(
        session,
        invitation_id=invitation_id,
        owner_user_id=current.user.id,
        owner="recipient",
    )
    if invitation.status is InvitationStatus.DECLINED:
        return _result(invitation)

    changed_at = _utc_now(clock)
    if effective_invitation_status(invitation, at=changed_at) is InvitationStatus.EXPIRED:
        raise InvitationMutationError(InvitationMutationReason.EXPIRED)
    if invitation.status is not InvitationStatus.PENDING:
        raise InvitationMutationError(InvitationMutationReason.INVALID_STATE)

    invitation.decline(at=changed_at)
    await session.flush()
    return _result(invitation)


async def cancel_matching_invitation(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    invitation_id: UUID,
    clock: Clock = _system_utc_now,
) -> InvitationMutationResult:
    """Idempotently cancel one effective-PENDING invitation as its sender."""
    invitation = await _load_owned_invitation_for_update(
        session,
        invitation_id=invitation_id,
        owner_user_id=current.user.id,
        owner="sender",
    )
    if invitation.status is InvitationStatus.CANCELLED:
        return _result(invitation)

    changed_at = _utc_now(clock)
    if effective_invitation_status(invitation, at=changed_at) is InvitationStatus.EXPIRED:
        raise InvitationMutationError(InvitationMutationReason.EXPIRED)
    if invitation.status is not InvitationStatus.PENDING:
        raise InvitationMutationError(InvitationMutationReason.INVALID_STATE)

    invitation.cancel(at=changed_at)
    await session.flush()
    return _result(invitation)


async def hide_accepted_invitation_from_sender(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    invitation_id: UUID,
    clock: Clock = _system_utc_now,
) -> InvitationMutationResult:
    """Idempotently hide only the sender's accepted invitation-history row."""
    invitation = await _load_owned_invitation_for_update(
        session,
        invitation_id=invitation_id,
        owner_user_id=current.user.id,
        owner="sender",
    )
    if invitation.status is not InvitationStatus.ACCEPTED:
        raise InvitationMutationError(InvitationMutationReason.INVALID_STATE)

    if invitation.hide_from_sender(at=_utc_now(clock)):
        await session.flush()
    return _result(invitation)
