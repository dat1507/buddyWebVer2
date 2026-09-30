"""Shared locking and ACTIVE Match policy for cross-domain Buddy invariants."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BuddyMatch, MatchStatus, User, UserRole


class BuddyParticipantStateError(RuntimeError):
    """Sanitized failure while locking a current USER participant set."""

    def __init__(self) -> None:
        super().__init__("Buddy participant state is invalid.")


def _available_user(user: User | None) -> bool:
    return bool(
        user is not None
        and user.role is UserRole.USER
        and user.is_active
        and user.deleted_at is None
    )


async def lock_current_buddy_users(
    session: AsyncSession,
    user_ids: Iterable[UUID],
) -> tuple[User, ...]:
    """Lock current USER rows in canonical UUID order for Buddy invariants."""
    ordered_ids = tuple(sorted(set(user_ids), key=lambda user_id: user_id.int))
    if not ordered_ids:
        raise BuddyParticipantStateError
    users = tuple(
        (
            await session.scalars(
                select(User)
                .where(User.id.in_(ordered_ids))
                .order_by(User.id)
                .with_for_update()
            )
        ).all()
    )
    users_by_id = {user.id: user for user in users}
    if not all(_available_user(users_by_id.get(user_id)) for user_id in ordered_ids):
        raise BuddyParticipantStateError
    return tuple(users_by_id[user_id] for user_id in ordered_ids)


async def has_active_buddy_match(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> bool:
    """Use participant indexes to answer only whether one ACTIVE Match exists."""
    active_exists = await session.scalar(
        select(
            exists().where(
                BuddyMatch.status == MatchStatus.ACTIVE,
                or_(
                    BuddyMatch.participant_one_user_id == user_id,
                    BuddyMatch.participant_two_user_id == user_id,
                ),
            )
        )
    )
    return bool(active_exists)
