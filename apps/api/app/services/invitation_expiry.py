"""Authoritative effective-expiry predicates and a bounded persistence job."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from app.models import InvitationStatus, MatchingInvitation

DEFAULT_INVITATION_EXPIRY_BATCH_SIZE: Final = 20
MAX_INVITATION_EXPIRY_BATCH_SIZE: Final = 100

Clock = Callable[[], datetime]


class InvitationExpiryValidationError(ValueError):
    """Raised when expiry processing receives an unsafe operational bound."""


@dataclass(frozen=True, slots=True)
class InvitationExpiryReport:
    """Safe aggregate result from one atomic expiry batch."""

    selected: int
    expired: int


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_instant(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invitation expiry timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def effective_invitation_status(
    invitation: MatchingInvitation,
    *,
    at: datetime,
) -> InvitationStatus:
    """Project stale persisted PENDING rows as EXPIRED without waiting for cleanup."""
    current_time = _utc_instant(at)
    expires_at = _utc_instant(invitation.expires_at)
    if invitation.status is InvitationStatus.PENDING and expires_at <= current_time:
        return InvitationStatus.EXPIRED
    return invitation.status


def effective_pending_predicate(*, at: datetime) -> ColumnElement[bool]:
    """Return the shared SQL predicate for invitations that remain usable."""
    current_time = _utc_instant(at)
    return and_(
        MatchingInvitation.status == InvitationStatus.PENDING,
        MatchingInvitation.expires_at > current_time,
    )


def expired_pending_predicate(*, at: datetime) -> ColumnElement[bool]:
    """Return the shared SQL predicate for due persisted PENDING rows."""
    current_time = _utc_instant(at)
    return and_(
        MatchingInvitation.status == InvitationStatus.PENDING,
        MatchingInvitation.expires_at <= current_time,
    )


async def expire_invitation_batch(
    session: AsyncSession,
    *,
    batch_size: int = DEFAULT_INVITATION_EXPIRY_BATCH_SIZE,
    clock: Clock = _system_utc_now,
) -> tuple[UUID, ...]:
    """Lock and transition one deterministic due batch inside the caller transaction."""
    if not 1 <= batch_size <= MAX_INVITATION_EXPIRY_BATCH_SIZE:
        raise InvitationExpiryValidationError(
            "Invitation expiry batch size is outside the supported range."
        )
    current_time = _utc_instant(clock())
    statement = (
        select(MatchingInvitation)
        .where(expired_pending_predicate(at=current_time))
        .order_by(MatchingInvitation.expires_at, MatchingInvitation.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    rows = tuple((await session.scalars(statement)).all())
    for invitation in rows:
        invitation.expire(at=current_time)
    if rows:
        await session.flush()
    return tuple(invitation.id for invitation in rows)


async def process_invitation_expiry_batch(
    factory: async_sessionmaker[AsyncSession],
    *,
    batch_size: int = DEFAULT_INVITATION_EXPIRY_BATCH_SIZE,
    clock: Clock = _system_utc_now,
) -> InvitationExpiryReport:
    """Atomically persist one bounded batch; failures roll back and remain retryable."""
    async with factory() as session:
        try:
            expired_ids = await expire_invitation_batch(
                session,
                batch_size=batch_size,
                clock=clock,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    count = len(expired_ids)
    return InvitationExpiryReport(selected=count, expired=count)
