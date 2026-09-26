"""Owner-bound, resumable student-profile persistence services."""

from __future__ import annotations

from datetime import date
from typing import Final, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentProfile, User, UserRole
from app.schemas.profile import ProfilePreferences, ProfileUpdate, WeeklyAvailability
from app.services.preference_storage import (
    list_selectable_activities,
    read_profile_activity_ids,
    replace_profile_activity_ids,
)

POSTGRES_UNIQUE_VIOLATION: Final = "23505"
_MUTABLE_FIELDS: Final = frozenset(
    {
        "full_name",
        "display_name",
        "student_type",
        "nationality",
        "major",
        "study_year",
        "bio",
        "home_university",
        "arrival_date",
        "departure_date",
        "availability",
        "preferences",
        "matching_opt_in",
    }
)


class ProfileAccessError(PermissionError):
    """Raised when an account is not allowed to own a student profile."""


class ProfileVersionConflictError(ValueError):
    """Raised when optimistic concurrency detects a stale profile version."""


class ProfileValidationError(ValueError):
    """Raised when a cross-field or catalog-backed update is invalid."""


def _require_profile_owner(owner: User) -> None:
    if not owner.is_active or owner.deleted_at is not None or owner.role is not UserRole.USER:
        raise ProfileAccessError("Profile access is not permitted.")


def _postgres_sqlstate(error: IntegrityError) -> str | None:
    current: BaseException | None = error.orig
    while current is not None:
        for attribute in ("sqlstate", "pgcode"):
            value = getattr(current, attribute, None)
            if isinstance(value, str):
                return value
        current = current.__cause__
    return None


async def _select_own_profile(
    session: AsyncSession,
    owner_id: UUID,
    *,
    for_update: bool = False,
) -> StudentProfile | None:
    statement = select(StudentProfile).where(StudentProfile.user_id == owner_id)
    if for_update:
        statement = statement.with_for_update()
    return cast(StudentProfile | None, await session.scalar(statement))


async def _get_or_create_own_profile(
    session: AsyncSession,
    owner: User,
    *,
    for_update: bool,
) -> StudentProfile:
    _require_profile_owner(owner)
    existing = await _select_own_profile(session, owner.id, for_update=for_update)
    if existing is not None:
        return existing

    candidate = StudentProfile(user_id=owner.id)
    try:
        async with session.begin_nested():
            session.add(candidate)
            await session.flush()
    except IntegrityError as error:
        if _postgres_sqlstate(error) != POSTGRES_UNIQUE_VIOLATION:
            raise
        winner = await _select_own_profile(session, owner.id, for_update=for_update)
        if winner is None:
            raise
        return winner
    return candidate


async def get_or_create_own_profile(session: AsyncSession, owner: User) -> StudentProfile:
    """Read the authenticated USER's profile or stage one race-safe draft.

    The caller owns commit/rollback. A savepoint isolates the expected unique-user race so a losing
    concurrent request can read the winning row without rolling back unrelated outer work.
    """
    return await _get_or_create_own_profile(session, owner, for_update=False)


async def get_or_create_own_profile_for_update(
    session: AsyncSession,
    owner: User,
) -> StudentProfile:
    """Resolve and lock the owner profile for related-table operations."""
    return await _get_or_create_own_profile(session, owner, for_update=True)


def _availability_value(value: WeeklyAvailability) -> dict[str, object]:
    return {
        "timezone": value.timezone,
        "slots": [slot.model_dump() for slot in value.slots],
    }


def _update_values(update: ProfileUpdate) -> dict[str, object | None]:
    changes: dict[str, object | None] = {}
    for field_name in update.model_fields_set.intersection(_MUTABLE_FIELDS):
        value = getattr(update, field_name)
        if isinstance(value, WeeklyAvailability):
            changes[field_name] = _availability_value(value)
        elif isinstance(value, ProfilePreferences):
            continue
        else:
            changes[field_name] = value
    return changes


async def update_own_profile(
    session: AsyncSession,
    owner: User,
    update: ProfileUpdate,
) -> StudentProfile:
    """Validate and stage an owner-bound partial update without committing it."""
    profile = await _get_or_create_own_profile(session, owner, for_update=True)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    changes = _update_values(update)
    arrival_date = cast(date | None, changes.get("arrival_date", profile.arrival_date))
    departure_date = cast(date | None, changes.get("departure_date", profile.departure_date))
    if arrival_date is not None and departure_date is not None and departure_date < arrival_date:
        raise ProfileValidationError("Profile dates are invalid.")

    requested_activity_ids: set[UUID] | None = None
    existing_activity_ids: tuple[UUID, ...] = ()
    if "preferences" in update.model_fields_set and update.preferences is not None:
        requested_activity_ids = set(update.preferences.preferred_activity_ids)
        selectable = await list_selectable_activities(session)
        if not requested_activity_ids.issubset({activity.id for activity in selectable}):
            raise ProfileValidationError("Profile preferences are invalid.")
        existing_activity_ids = await read_profile_activity_ids(session, profile.id)

    for field_name, value in changes.items():
        setattr(profile, field_name, value)
    if requested_activity_ids is not None:
        await replace_profile_activity_ids(
            session,
            profile.id,
            requested_activity_ids,
            existing=existing_activity_ids,
        )
    profile.version += 1
    await session.flush()
    return profile
