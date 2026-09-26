"""Localized catalogs and atomic owner-bound preference replacement services."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Activity,
    Interest,
    Language,
    LanguageProficiency,
    PreferenceKind,
    ProfileCustomPreference,
    ProfileInterest,
    ProfileLanguage,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas.profile_catalog import (
    CustomLanguageInput,
    CustomLanguageSelection,
    CustomPreferenceInput,
    CustomPreferenceSelection,
    ProfileActivityUpdate,
    ProfileInterestUpdate,
    ProfileLanguageSelection,
    ProfileLanguageUpdate,
    ProfilePreferenceUpdate,
)
from app.services.preference_identity import (
    PreferenceIdentityError,
    normalize_preference_identity,
    normalize_preference_key,
)
from app.services.preference_storage import (
    list_selectable_activities,
    read_profile_activity_ids,
    replace_profile_activity_ids,
)
from app.services.profiles import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
    get_or_create_own_profile,
    get_or_create_own_profile_for_update,
)


@dataclass(frozen=True, slots=True)
class ProfileCatalogSelections:
    """Complete deterministic preference selections for one authenticated profile."""

    interest_ids: tuple[UUID, ...]
    custom_interests: tuple[CustomPreferenceSelection, ...]
    languages: tuple[ProfileLanguageSelection, ...]
    custom_languages: tuple[CustomLanguageSelection, ...]
    activity_ids: tuple[UUID, ...]
    custom_activities: tuple[CustomPreferenceSelection, ...]


@dataclass(frozen=True, slots=True)
class ProfileInterestMutation:
    """Interest replacement result carrying the new snapshot version."""

    version: int
    interest_ids: tuple[UUID, ...]
    custom_interests: tuple[CustomPreferenceSelection, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileLanguageMutation:
    """Language replacement result carrying the new snapshot version."""

    version: int
    languages: tuple[ProfileLanguageSelection, ...]
    custom_languages: tuple[CustomLanguageSelection, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileActivityMutation:
    """Activity replacement result carrying the new snapshot version."""

    version: int
    activity_ids: tuple[UUID, ...]
    custom_activities: tuple[CustomPreferenceSelection, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfilePreferenceSnapshot:
    """Versioned complete owner projection used by the combined preference API."""

    version: int
    interest_ids: tuple[UUID, ...]
    custom_interests: tuple[CustomPreferenceSelection, ...]
    languages: tuple[ProfileLanguageSelection, ...]
    custom_languages: tuple[CustomLanguageSelection, ...]
    activity_ids: tuple[UUID, ...]
    custom_activities: tuple[CustomPreferenceSelection, ...]


@dataclass(frozen=True, slots=True)
class _PreparedCustomPreference:
    display_label: str
    normalized_key: str
    proficiency: LanguageProficiency | None


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


async def list_active_activities(session: AsyncSession) -> tuple[Activity, ...]:
    """Return only selectable Activities in stable catalog order."""
    return await list_selectable_activities(session)


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


async def _custom_rows(
    session: AsyncSession,
    profile_id: UUID,
    kind: PreferenceKind | None = None,
) -> tuple[ProfileCustomPreference, ...]:
    statement = select(ProfileCustomPreference).where(
        ProfileCustomPreference.profile_id == profile_id,
        ProfileCustomPreference.deleted_at.is_(None),
    )
    if kind is not None:
        statement = statement.where(ProfileCustomPreference.kind == kind)
    result = await session.scalars(
        statement.order_by(
            ProfileCustomPreference.kind,
            ProfileCustomPreference.normalized_key,
        )
    )
    return tuple(result.all())


def _custom_label_selections(
    rows: tuple[ProfileCustomPreference, ...],
    kind: PreferenceKind,
) -> tuple[CustomPreferenceSelection, ...]:
    return tuple(
        CustomPreferenceSelection(label=row.display_label)
        for row in rows
        if row.kind is kind
    )


def _custom_language_selections(
    rows: tuple[ProfileCustomPreference, ...],
) -> tuple[CustomLanguageSelection, ...]:
    return tuple(
        CustomLanguageSelection(
            label=row.display_label,
            proficiency=row.proficiency,
        )
        for row in rows
        if row.kind is PreferenceKind.LANGUAGE and row.proficiency is not None
    )


async def get_own_catalog_selections(
    session: AsyncSession,
    owner: User,
    profile: StudentProfile,
) -> ProfileCatalogSelections:
    """Read every preference namespace through the authenticated profile owner."""
    if (
        not owner.is_active
        or owner.deleted_at is not None
        or owner.role is not UserRole.USER
        or profile.user_id != owner.id
        or profile.deleted_at is not None
    ):
        raise ProfileAccessError("Profile catalog access is not permitted.")

    return await _read_catalog_selections(session, profile.id)


async def _read_catalog_selections(
    session: AsyncSession,
    profile_id: UUID,
    *,
    custom_rows: tuple[ProfileCustomPreference, ...] | None = None,
) -> ProfileCatalogSelections:
    rows = await _custom_rows(session, profile_id) if custom_rows is None else custom_rows
    return ProfileCatalogSelections(
        interest_ids=await _interest_ids(session, profile_id),
        custom_interests=_custom_label_selections(rows, PreferenceKind.INTEREST),
        languages=await _language_selections(session, profile_id),
        custom_languages=_custom_language_selections(rows),
        activity_ids=await read_profile_activity_ids(session, profile_id),
        custom_activities=_custom_label_selections(rows, PreferenceKind.ACTIVITY),
    )


def _snapshot(
    profile: StudentProfile,
    selections: ProfileCatalogSelections,
) -> ProfilePreferenceSnapshot:
    return ProfilePreferenceSnapshot(
        version=profile.version,
        interest_ids=selections.interest_ids,
        custom_interests=selections.custom_interests,
        languages=selections.languages,
        custom_languages=selections.custom_languages,
        activity_ids=selections.activity_ids,
        custom_activities=selections.custom_activities,
    )


async def get_own_preference_snapshot(
    session: AsyncSession,
    owner: User,
) -> ProfilePreferenceSnapshot:
    """Return a versioned full preference projection, creating a resumable draft if absent."""
    profile = await get_or_create_own_profile(session, owner)
    return _snapshot(profile, await get_own_catalog_selections(session, owner, profile))


def _catalog_identity_keys(labels: tuple[tuple[str, str], ...]) -> frozenset[str]:
    keys: set[str] = set()
    try:
        for label_en, label_de in labels:
            keys.add(normalize_preference_key(label_en))
            keys.add(normalize_preference_key(label_de))
    except PreferenceIdentityError as error:
        raise ProfileValidationError("Selectable preference catalog is invalid.") from error
    return frozenset(keys)


def _normalize_custom(
    values: tuple[tuple[str, LanguageProficiency | None], ...],
    catalog_keys: frozenset[str],
) -> tuple[_PreparedCustomPreference, ...]:
    prepared: list[_PreparedCustomPreference] = []
    seen: set[str] = set()
    for label, proficiency in values:
        try:
            identity = normalize_preference_identity(label)
        except PreferenceIdentityError as error:
            raise ProfileValidationError("Custom preference is invalid.") from error
        if identity.normalized_key in catalog_keys or identity.normalized_key in seen:
            raise ProfileValidationError("Custom preference duplicates an existing preference.")
        seen.add(identity.normalized_key)
        prepared.append(
            _PreparedCustomPreference(
                display_label=identity.display_label,
                normalized_key=identity.normalized_key,
                proficiency=proficiency,
            )
        )
    return tuple(sorted(prepared, key=lambda item: item.normalized_key))


async def _prepare_interests(
    session: AsyncSession,
    interest_ids: list[UUID],
    custom_interests: list[CustomPreferenceInput],
) -> tuple[tuple[UUID, ...], tuple[_PreparedCustomPreference, ...]]:
    catalog = await list_active_interests(session)
    requested = set(interest_ids)
    if not requested.issubset({item.id for item in catalog}):
        raise ProfileValidationError("Profile interests are invalid.")
    prepared = _normalize_custom(
        tuple((item.label, None) for item in custom_interests),
        _catalog_identity_keys(tuple((item.label_en, item.label_de) for item in catalog)),
    )
    return tuple(sorted(requested, key=str)), prepared


async def _prepare_languages(
    session: AsyncSession,
    languages: list[ProfileLanguageSelection],
    custom_languages: list[CustomLanguageInput],
) -> tuple[
    tuple[ProfileLanguageSelection, ...],
    tuple[_PreparedCustomPreference, ...],
]:
    catalog = await list_active_languages(session)
    requested = {item.language_code for item in languages}
    if not requested.issubset({item.code for item in catalog}):
        raise ProfileValidationError("Profile languages are invalid.")
    prepared = _normalize_custom(
        tuple((item.label, item.proficiency) for item in custom_languages),
        _catalog_identity_keys(tuple((item.label_en, item.label_de) for item in catalog)),
    )
    return tuple(sorted(languages, key=lambda item: item.language_code)), prepared


async def _prepare_activities(
    session: AsyncSession,
    activity_ids: list[UUID],
    custom_activities: list[CustomPreferenceInput],
) -> tuple[tuple[UUID, ...], tuple[_PreparedCustomPreference, ...]]:
    catalog = await list_active_activities(session)
    requested = set(activity_ids)
    if not requested.issubset({item.id for item in catalog}):
        raise ProfileValidationError("Profile activities are invalid.")
    prepared = _normalize_custom(
        tuple((item.label, None) for item in custom_activities),
        _catalog_identity_keys(tuple((item.label_en, item.label_de) for item in catalog)),
    )
    return tuple(sorted(requested, key=str)), prepared


def _prepared_signature(
    values: tuple[_PreparedCustomPreference, ...],
) -> tuple[tuple[str, str, LanguageProficiency | None], ...]:
    return tuple(
        (item.normalized_key, item.display_label, item.proficiency) for item in values
    )


def _row_signature(
    rows: tuple[ProfileCustomPreference, ...],
) -> tuple[tuple[str, str, LanguageProficiency | None], ...]:
    return tuple(
        (row.normalized_key, row.display_label, row.proficiency)
        for row in sorted(rows, key=lambda item: item.normalized_key)
    )


def _custom_models(
    profile_id: UUID,
    kind: PreferenceKind,
    values: tuple[_PreparedCustomPreference, ...],
) -> list[ProfileCustomPreference]:
    return [
        ProfileCustomPreference(
            profile_id=profile_id,
            kind=kind,
            display_label=item.display_label,
            normalized_key=item.normalized_key,
            proficiency=item.proficiency,
        )
        for item in values
    ]


def _custom_label_output(
    values: tuple[_PreparedCustomPreference, ...],
) -> tuple[CustomPreferenceSelection, ...]:
    return tuple(CustomPreferenceSelection(label=item.display_label) for item in values)


def _custom_language_output(
    values: tuple[_PreparedCustomPreference, ...],
) -> tuple[CustomLanguageSelection, ...]:
    return tuple(
        CustomLanguageSelection(label=item.display_label, proficiency=item.proficiency)
        for item in values
        if item.proficiency is not None
    )


async def _replace_custom_kind(
    session: AsyncSession,
    profile_id: UUID,
    kind: PreferenceKind,
    values: tuple[_PreparedCustomPreference, ...],
) -> None:
    await session.execute(
        delete(ProfileCustomPreference).where(
            ProfileCustomPreference.profile_id == profile_id,
            ProfileCustomPreference.kind == kind,
        )
    )
    rows = _custom_models(profile_id, kind, values)
    if rows:
        session.add_all(rows)


async def replace_own_interests(
    session: AsyncSession,
    owner: User,
    update: ProfileInterestUpdate,
) -> ProfileInterestMutation:
    """Atomically replace predefined and custom Interests for the current owner."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    requested_ids, requested_custom = await _prepare_interests(
        session, update.interest_ids, update.custom_interests
    )
    existing_ids = await _interest_ids(session, profile.id)
    existing_custom = await _custom_rows(session, profile.id, PreferenceKind.INTEREST)
    changed = (
        requested_ids != existing_ids
        or _prepared_signature(requested_custom) != _row_signature(existing_custom)
    )
    if changed:
        await session.execute(
            delete(ProfileInterest).where(ProfileInterest.profile_id == profile.id)
        )
        rows = [
            ProfileInterest(profile_id=profile.id, interest_id=interest_id)
            for interest_id in requested_ids
        ]
        if rows:
            session.add_all(rows)
        await _replace_custom_kind(
            session, profile.id, PreferenceKind.INTEREST, requested_custom
        )
        profile.version += 1
        await session.flush()

    return ProfileInterestMutation(
        version=profile.version,
        interest_ids=requested_ids,
        custom_interests=_custom_label_output(requested_custom),
    )


async def replace_own_languages(
    session: AsyncSession,
    owner: User,
    update: ProfileLanguageUpdate,
) -> ProfileLanguageMutation:
    """Atomically replace predefined and custom Languages with proficiency."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    requested, requested_custom = await _prepare_languages(
        session, update.languages, update.custom_languages
    )
    existing = await _language_selections(session, profile.id)
    existing_custom = await _custom_rows(session, profile.id, PreferenceKind.LANGUAGE)
    changed = (
        requested != existing
        or _prepared_signature(requested_custom) != _row_signature(existing_custom)
    )
    if changed:
        await session.execute(
            delete(ProfileLanguage).where(ProfileLanguage.profile_id == profile.id)
        )
        rows = [
            ProfileLanguage(
                profile_id=profile.id,
                language_code=item.language_code,
                proficiency=item.proficiency,
            )
            for item in requested
        ]
        if rows:
            session.add_all(rows)
        await _replace_custom_kind(
            session, profile.id, PreferenceKind.LANGUAGE, requested_custom
        )
        profile.version += 1
        await session.flush()

    return ProfileLanguageMutation(
        version=profile.version,
        languages=requested,
        custom_languages=_custom_language_output(requested_custom),
    )


async def replace_own_activities(
    session: AsyncSession,
    owner: User,
    update: ProfileActivityUpdate,
) -> ProfileActivityMutation:
    """Atomically replace predefined and custom Activities for the current owner."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    requested_ids, requested_custom = await _prepare_activities(
        session, update.activity_ids, update.custom_activities
    )
    existing_ids = await read_profile_activity_ids(session, profile.id)
    existing_custom = await _custom_rows(session, profile.id, PreferenceKind.ACTIVITY)
    changed = (
        requested_ids != existing_ids
        or _prepared_signature(requested_custom) != _row_signature(existing_custom)
    )
    if changed:
        await replace_profile_activity_ids(
            session,
            profile.id,
            requested_ids,
            existing=existing_ids,
        )
        await _replace_custom_kind(
            session, profile.id, PreferenceKind.ACTIVITY, requested_custom
        )
        profile.version += 1
        await session.flush()

    return ProfileActivityMutation(
        version=profile.version,
        activity_ids=requested_ids,
        custom_activities=_custom_label_output(requested_custom),
    )


async def replace_own_preferences(
    session: AsyncSession,
    owner: User,
    update: ProfilePreferenceUpdate,
) -> ProfilePreferenceSnapshot:
    """Replace all preference groups under one owner lock and one transaction."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.version != update.version:
        raise ProfileVersionConflictError("Profile version is stale.")

    interest_ids, custom_interests = await _prepare_interests(
        session, update.interest_ids, update.custom_interests
    )
    languages, custom_languages = await _prepare_languages(
        session, update.languages, update.custom_languages
    )
    activity_ids, custom_activities = await _prepare_activities(
        session, update.activity_ids, update.custom_activities
    )

    existing_custom_rows = await _custom_rows(session, profile.id)
    existing = await _read_catalog_selections(
        session,
        profile.id,
        custom_rows=existing_custom_rows,
    )
    requested_custom_signature = (
        _prepared_signature(custom_interests),
        _prepared_signature(custom_languages),
        _prepared_signature(custom_activities),
    )
    existing_custom_signature = tuple(
        _row_signature(
            tuple(row for row in existing_custom_rows if row.kind is kind)
        )
        for kind in (
            PreferenceKind.INTEREST,
            PreferenceKind.LANGUAGE,
            PreferenceKind.ACTIVITY,
        )
    )
    changed = (
        interest_ids != existing.interest_ids
        or languages != existing.languages
        or activity_ids != existing.activity_ids
        or requested_custom_signature != existing_custom_signature
    )
    if changed:
        await session.execute(
            delete(ProfileInterest).where(ProfileInterest.profile_id == profile.id)
        )
        await session.execute(
            delete(ProfileLanguage).where(ProfileLanguage.profile_id == profile.id)
        )
        await replace_profile_activity_ids(
            session,
            profile.id,
            activity_ids,
            existing=existing.activity_ids,
        )
        await session.execute(
            delete(ProfileCustomPreference).where(
                ProfileCustomPreference.profile_id == profile.id
            )
        )
        rows = [
            *(
                ProfileInterest(profile_id=profile.id, interest_id=interest_id)
                for interest_id in interest_ids
            ),
            *(
                ProfileLanguage(
                    profile_id=profile.id,
                    language_code=item.language_code,
                    proficiency=item.proficiency,
                )
                for item in languages
            ),
            *_custom_models(profile.id, PreferenceKind.INTEREST, custom_interests),
            *_custom_models(profile.id, PreferenceKind.LANGUAGE, custom_languages),
            *_custom_models(profile.id, PreferenceKind.ACTIVITY, custom_activities),
        ]
        if rows:
            session.add_all(rows)
        profile.version += 1
        await session.flush()

    return ProfilePreferenceSnapshot(
        version=profile.version,
        interest_ids=interest_ids,
        custom_interests=_custom_label_output(custom_interests),
        languages=languages,
        custom_languages=_custom_language_output(custom_languages),
        activity_ids=activity_ids,
        custom_activities=_custom_label_output(custom_activities),
    )
