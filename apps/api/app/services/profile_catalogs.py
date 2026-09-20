"""Localized catalog reads and optimistic owner-bound relation replacement."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Interest,
    Language,
    ProfileInterest,
    ProfileLanguage,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas.profile_catalog import (
    ProfileInterestUpdate,
    ProfileLanguageSelection,
    ProfileLanguageUpdate,
)
from app.services.profiles import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
    get_or_create_own_profile_for_update,
)


@dataclass(frozen=True, slots=True)
class ProfileCatalogSelections:
    """Canonical normalized selections for an authenticated profile."""

    interest_ids: tuple[UUID, ...]
    languages: tuple[ProfileLanguageSelection, ...]


@dataclass(frozen=True, slots=True)
class ProfileInterestMutation:
    """Interest replacement result carrying the new snapshot version."""

    version: int
    interest_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ProfileLanguageMutation:
    """Language replacement result carrying the new snapshot version."""

    version: int
    languages: tuple[ProfileLanguageSelection, ...]


async def list_active_interests(session: AsyncSession) -> tuple[Interest, ...]:
    """Return only selectable interests in stable catalog order."""
    result = await session.scalars(
        select(Interest)
        .where(Interest.is_active.is_(True), Interest.deleted_at.is_(None))
        .order_by(Interest.category, Interest.code)
    )
    return tuple(result.all())


async def list_active_languages(session: AsyncSession) -> tuple[Language, ...]:
    """Return only selectable languages in stable catalog order."""
    result = await session.scalars(
        select(Language).where(Language.is_active.is_(True)).order_by(Language.code)
    )
    return tuple(result.all())


async def _interest_ids(session: AsyncSession, profile_id: UUID) -> tuple[UUID, ...]:
    result = await session.scalars(
        select(ProfileInterest.interest_id)
        .where(ProfileInterest.profile_id == profile_id)
        .order_by(ProfileInterest.interest_id)
    )
    return tuple(result.all())


async def _language_selections(
    session: AsyncSession, profile_id: UUID
) -> tuple[ProfileLanguageSelection, ...]:
    result = await session.scalars(
        select(ProfileLanguage)
        .where(ProfileLanguage.profile_id == profile_id)
        .order_by(ProfileLanguage.language_code)
    )
    return tuple(
        ProfileLanguageSelection(
            language_code=selection.language_code,
            proficiency=selection.proficiency,
        )
        for selection in result.all()
    )


async def get_own_catalog_selections(
    session: AsyncSession,
    owner: User,
    profile: StudentProfile,
) -> ProfileCatalogSelections:
    """Read normalized relations through the authenticated profile owner."""
    if (
        not owner.is_active
        or owner.deleted_at is not None
        or owner.role is not UserRole.USER
        or profile.user_id != owner.id
        or profile.deleted_at is not None
    ):
        raise ProfileAccessError("Profile catalog access is not permitted.")
    return ProfileCatalogSelections(
        interest_ids=await _interest_ids(session, profile.id),
        languages=await _language_selections(session, profile.id),
    )


async def _validate_interest_ids(session: AsyncSession, requested: set[UUID]) -> None:
    if not requested:
        return
    result = await session.scalars(
        select(Interest.id).where(
            Interest.id.in_(requested),
            Interest.is_active.is_(True),
            Interest.deleted_at.is_(None),
        )
    )
    if set(result.all()) != requested:
        raise ProfileValidationError("Profile interests are invalid.")


async def _validate_language_codes(session: AsyncSession, requested: set[str]) -> None:
    if not requested:
        return
    result = await session.scalars(
        select(Language.code).where(
            Language.code.in_(requested),
            Language.is_active.is_(True),
        )
    )
    if set(result.all()) != requested:
        raise ProfileValidationError("Profile languages are invalid.")


async def replace_own_interests(
    session: AsyncSession,
    owner: User,
    update: ProfileInterestUpdate,
) -> ProfileInterestMutation:
    """Replace one owner's complete interest set and advance its snapshot version."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    requested = set(update.interest_ids)
    await _validate_interest_ids(session, requested)
    existing = set(await _interest_ids(session, profile.id))
    if requested != existing:
        await session.execute(
            delete(ProfileInterest).where(ProfileInterest.profile_id == profile.id)
        )
        session.add_all(
            ProfileInterest(profile_id=profile.id, interest_id=interest_id)
            for interest_id in sorted(requested, key=str)
        )
        profile.version += 1
        await session.flush()

    return ProfileInterestMutation(
        version=profile.version,
        interest_ids=tuple(sorted(requested, key=str)),
    )


async def replace_own_languages(
    session: AsyncSession,
    owner: User,
    update: ProfileLanguageUpdate,
) -> ProfileLanguageMutation:
    """Replace one owner's complete language set and advance its snapshot version."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    requested = {selection.language_code: selection.proficiency for selection in update.languages}
    await _validate_language_codes(session, set(requested))
    existing = {
        selection.language_code: selection.proficiency
        for selection in await _language_selections(session, profile.id)
    }
    if requested != existing:
        await session.execute(
            delete(ProfileLanguage).where(ProfileLanguage.profile_id == profile.id)
        )
        session.add_all(
            ProfileLanguage(
                profile_id=profile.id,
                language_code=language_code,
                proficiency=proficiency,
            )
            for language_code, proficiency in sorted(requested.items())
        )
        profile.version += 1
        await session.flush()

    return ProfileLanguageMutation(
        version=profile.version,
        languages=tuple(
            ProfileLanguageSelection(language_code=code, proficiency=proficiency)
            for code, proficiency in sorted(requested.items())
        ),
    )
