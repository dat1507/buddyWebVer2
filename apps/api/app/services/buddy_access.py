"""Shared current-database capability policy for Buddy and chat transports."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentProfile, User, UserRole
from app.schemas.profile_completion import MatchingIneligibilityReason


class BuddyCapabilityError(PermissionError):
    """Sanitized denial with an optional frontend-safe completion reason."""

    def __init__(self, reason: MatchingIneligibilityReason | None = None) -> None:
        super().__init__("Buddy capability is unavailable.")
        self.reason = reason


@dataclass(frozen=True, slots=True)
class VerifiedBuddyPrincipal:
    """Persisted USER and profile selected only from the authenticated owner ID."""

    user: User = field(repr=False)
    profile: StudentProfile = field(repr=False)


async def get_verified_buddy_principal(
    session: AsyncSession,
    current_user: User,
) -> VerifiedBuddyPrincipal:
    """Require current USER state, timestamp verification, and an owned live profile."""
    if (
        current_user.role is not UserRole.USER
        or not current_user.is_active
        or current_user.deleted_at is not None
    ):
        raise BuddyCapabilityError()
    if current_user.email_verified_at is None:
        raise BuddyCapabilityError(
            MatchingIneligibilityReason.EMAIL_VERIFICATION_REQUIRED
        )

    profile = await session.scalar(
        select(StudentProfile).where(
            StudentProfile.user_id == current_user.id,
            StudentProfile.deleted_at.is_(None),
        )
    )
    if (
        profile is None
        or profile.user_id != current_user.id
        or profile.deleted_at is not None
    ):
        raise BuddyCapabilityError()
    return VerifiedBuddyPrincipal(user=current_user, profile=profile)
