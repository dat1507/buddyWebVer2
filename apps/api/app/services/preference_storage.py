"""Low-level Activity relation reads and replacements shared by profile services."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, ProfileActivity


async def list_selectable_activities(session: AsyncSession) -> tuple[Activity, ...]:
    """Load the bounded shared Activity catalog in stable code order."""
    result = await session.scalars(
        select(Activity)
        .where(Activity.is_active.is_(True), Activity.deleted_at.is_(None))
        .order_by(Activity.code)
    )
    return tuple(result.all())


async def read_profile_activity_ids(
    session: AsyncSession,
    profile_id: UUID,
) -> tuple[UUID, ...]:
    """Read one profile's predefined Activity identifiers deterministically."""
    result = await session.scalars(
        select(ProfileActivity.activity_id)
        .where(ProfileActivity.profile_id == profile_id)
        .order_by(ProfileActivity.activity_id)
    )
    return tuple(result.all())


async def replace_profile_activity_ids(
    session: AsyncSession,
    profile_id: UUID,
    requested: Collection[UUID],
    *,
    existing: Collection[UUID] | None = None,
) -> bool:
    """Replace one profile's Activity relations without committing or changing its version."""
    requested_set = set(requested)
    existing_set = (
        set(await read_profile_activity_ids(session, profile_id))
        if existing is None
        else set(existing)
    )
    if requested_set == existing_set:
        return False

    await session.execute(
        delete(ProfileActivity).where(ProfileActivity.profile_id == profile_id)
    )
    rows = [
        ProfileActivity(profile_id=profile_id, activity_id=activity_id)
        for activity_id in sorted(requested_set, key=str)
    ]
    if rows:
        session.add_all(rows)
    return True
