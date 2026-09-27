"""Reusable REC-001 eligibility policy and privacy-safe candidate projection."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import cast
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import ScalarSelect

from app.models import (
    Activity,
    Interest,
    Language,
    PreferenceKind,
    ProfileActivity,
    ProfileCustomPreference,
    ProfileInterest,
    ProfileLanguage,
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.schemas.matching import (
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.schemas.profile import WeeklyAvailability
from app.schemas.profile_catalog import CatalogLocale
from app.services.buddy_access import (
    BuddyCapabilityError,
    VerifiedBuddyPrincipal,
)
from app.services.profile_completion import get_profile_completion


@dataclass(frozen=True, slots=True)
class EligibleMatchingPrincipal:
    """Minimal internal identity for a currently eligible matching participant."""

    user_id: UUID
    profile_id: UUID
    student_type: StudentType


@dataclass(frozen=True, slots=True)
class EligibleMatchingCandidate:
    """Internal eligible principal paired with its public-safe projection."""

    principal: EligibleMatchingPrincipal = field(repr=False)
    profile: SafeMatchingProfile


async def get_eligible_matching_principal(
    session: AsyncSession,
    principal: VerifiedBuddyPrincipal,
) -> EligibleMatchingPrincipal:
    """Require current persisted completion and opt-in after the shared VERIFIED guard."""
    completion = await get_profile_completion(session, principal.user, principal.profile)
    if not completion.matching_eligible:
        raise BuddyCapabilityError(completion.reasons[0] if completion.reasons else None)
    if principal.profile.student_type is None:  # Covered by profile completion; narrows the type.
        raise BuddyCapabilityError()
    return EligibleMatchingPrincipal(
        user_id=principal.user.id,
        profile_id=principal.profile.id,
        student_type=principal.profile.student_type,
    )


def matching_pair_is_eligible(
    current: EligibleMatchingPrincipal,
    candidate: EligibleMatchingPrincipal,
) -> bool:
    """Apply the REC-001 pair rule without any reservation or relationship exclusion."""
    return (
        current.user_id != candidate.user_id
        and current.profile_id != candidate.profile_id
        and current.student_type is not candidate.student_type
    )


def _custom_count(kind: PreferenceKind) -> ScalarSelect[int]:
    return (
        select(func.count(ProfileCustomPreference.id))
        .where(
            ProfileCustomPreference.profile_id == StudentProfile.id,
            ProfileCustomPreference.kind == kind,
            ProfileCustomPreference.deleted_at.is_(None),
        )
        .correlate(StudentProfile)
        .scalar_subquery()
    )


def _interest_count() -> ColumnElement[int]:
    predefined = (
        select(func.count(ProfileInterest.interest_id))
        .join(Interest, Interest.id == ProfileInterest.interest_id)
        .where(
            ProfileInterest.profile_id == StudentProfile.id,
            Interest.is_active.is_(True),
            Interest.deleted_at.is_(None),
        )
        .correlate(StudentProfile)
        .scalar_subquery()
    )
    return predefined + _custom_count(PreferenceKind.INTEREST)


def _language_count() -> ColumnElement[int]:
    predefined = (
        select(func.count(ProfileLanguage.language_code))
        .join(Language, Language.code == ProfileLanguage.language_code)
        .where(
            ProfileLanguage.profile_id == StudentProfile.id,
            Language.is_active.is_(True),
        )
        .correlate(StudentProfile)
        .scalar_subquery()
    )
    return predefined + _custom_count(PreferenceKind.LANGUAGE)


def _eligible_candidate_conditions(
    current: EligibleMatchingPrincipal,
) -> tuple[ColumnElement[bool], ...]:
    ready_avatar_count = (
        select(func.count(ProfilePhoto.id))
        .where(
            ProfilePhoto.profile_id == StudentProfile.id,
            ProfilePhoto.is_avatar.is_(True),
            ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
            ProfilePhoto.deleted_at.is_(None),
        )
        .correlate(StudentProfile)
        .scalar_subquery()
    )
    interest_count = _interest_count()
    language_count = _language_count()
    return (
        User.role == UserRole.USER,
        User.is_active.is_(True),
        User.deleted_at.is_(None),
        User.email_verified_at.is_not(None),
        StudentProfile.deleted_at.is_(None),
        StudentProfile.user_id != current.user_id,
        StudentProfile.id != current.profile_id,
        StudentProfile.student_type.is_not(None),
        StudentProfile.student_type != current.student_type,
        StudentProfile.matching_opt_in.is_(True),
        func.char_length(func.btrim(StudentProfile.full_name)).between(1, 120),
        ready_avatar_count == 1,
        interest_count.between(1, 20),
        language_count.between(1, 10),
    )


def eligible_candidate_statement(
    current: EligibleMatchingPrincipal,
    *,
    limit: int,
) -> Select[tuple[StudentProfile, ProfilePhoto]]:
    """Build a bounded, deterministic query that never selects private User columns."""
    if limit < 1:
        raise ValueError("Candidate query limit must be positive.")
    return (
        select(StudentProfile, ProfilePhoto)
        .join(User, User.id == StudentProfile.user_id)
        .join(
            ProfilePhoto,
            (ProfilePhoto.profile_id == StudentProfile.id)
            & ProfilePhoto.is_avatar.is_(True)
            & (ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY)
            & ProfilePhoto.deleted_at.is_(None),
        )
        .where(*_eligible_candidate_conditions(current))
        .order_by(StudentProfile.id)
        .limit(limit)
    )


def _localized_label(value: Interest | Activity | Language, locale: CatalogLocale) -> str:
    return value.label_de if locale == "de" else value.label_en


async def _project_safe_profiles(
    session: AsyncSession,
    rows: tuple[tuple[StudentProfile, ProfilePhoto], ...],
    *,
    locale: CatalogLocale,
) -> tuple[SafeMatchingProfile, ...]:
    if not rows:
        return ()
    profile_ids = tuple(profile.id for profile, _photo in rows)

    interest_rows = (
        (
            await session.execute(
                select(ProfileInterest.profile_id, Interest)
                .join(Interest, Interest.id == ProfileInterest.interest_id)
                .where(
                    ProfileInterest.profile_id.in_(profile_ids),
                    Interest.is_active.is_(True),
                    Interest.deleted_at.is_(None),
                )
                .order_by(ProfileInterest.profile_id, Interest.category, Interest.code)
            )
        )
        .tuples()
        .all()
    )
    language_rows = (
        (
            await session.execute(
                select(ProfileLanguage.profile_id, Language, ProfileLanguage.proficiency)
                .join(Language, Language.code == ProfileLanguage.language_code)
                .where(
                    ProfileLanguage.profile_id.in_(profile_ids),
                    Language.is_active.is_(True),
                )
                .order_by(ProfileLanguage.profile_id, Language.code)
            )
        )
        .tuples()
        .all()
    )
    activity_rows = (
        (
            await session.execute(
                select(ProfileActivity.profile_id, Activity)
                .join(Activity, Activity.id == ProfileActivity.activity_id)
                .where(
                    ProfileActivity.profile_id.in_(profile_ids),
                    Activity.is_active.is_(True),
                    Activity.deleted_at.is_(None),
                )
                .order_by(ProfileActivity.profile_id, Activity.code)
            )
        )
        .tuples()
        .all()
    )
    custom_rows = (
        (
            await session.execute(
                select(ProfileCustomPreference)
                .where(
                    ProfileCustomPreference.profile_id.in_(profile_ids),
                    ProfileCustomPreference.deleted_at.is_(None),
                )
                .order_by(
                    ProfileCustomPreference.profile_id,
                    ProfileCustomPreference.kind,
                    ProfileCustomPreference.normalized_key,
                )
            )
        )
        .scalars()
        .all()
    )

    interests: defaultdict[UUID, list[SafeMatchingPreference]] = defaultdict(list)
    languages: defaultdict[UUID, list[SafeMatchingLanguage]] = defaultdict(list)
    activities: defaultdict[UUID, list[SafeMatchingPreference]] = defaultdict(list)
    for profile_id, interest in interest_rows:
        interests[profile_id].append(
            SafeMatchingPreference(
                id=interest.id,
                code=interest.code,
                label=_localized_label(interest, locale),
                is_custom=False,
            )
        )
    for profile_id, language, proficiency in language_rows:
        languages[profile_id].append(
            SafeMatchingLanguage(
                code=language.code,
                label=_localized_label(language, locale),
                proficiency=proficiency,
                is_custom=False,
            )
        )
    for profile_id, activity in activity_rows:
        activities[profile_id].append(
            SafeMatchingPreference(
                id=activity.id,
                code=activity.code,
                label=_localized_label(activity, locale),
                is_custom=False,
            )
        )
    for custom in custom_rows:
        if custom.kind is PreferenceKind.INTEREST:
            interests[custom.profile_id].append(
                SafeMatchingPreference(
                    id=None,
                    code=None,
                    label=custom.display_label,
                    is_custom=True,
                )
            )
        elif custom.kind is PreferenceKind.ACTIVITY:
            activities[custom.profile_id].append(
                SafeMatchingPreference(
                    id=None,
                    code=None,
                    label=custom.display_label,
                    is_custom=True,
                )
            )
        elif custom.kind is PreferenceKind.LANGUAGE and custom.proficiency is not None:
            languages[custom.profile_id].append(
                SafeMatchingLanguage(
                    code=None,
                    label=custom.display_label,
                    proficiency=custom.proficiency,
                    is_custom=True,
                )
            )

    projected: list[SafeMatchingProfile] = []
    for profile, avatar in rows:
        if profile.student_type is None:  # Query invariant; narrows the model type.
            continue
        availability = (
            WeeklyAvailability.model_validate(profile.availability)
            if profile.availability is not None
            else None
        )
        projected.append(
            SafeMatchingProfile(
                id=profile.id,
                display_name=profile.display_name,
                student_type=profile.student_type,
                major=profile.major,
                avatar=SafeMatchingAvatar(
                    id=avatar.id,
                    width=avatar.width,
                    height=avatar.height,
                ),
                interests=interests[profile.id],
                languages=languages[profile.id],
                activities=activities[profile.id],
                availability=availability,
            )
        )
    return tuple(projected)


async def list_eligible_matching_profiles(
    session: AsyncSession,
    current: EligibleMatchingPrincipal,
    *,
    locale: CatalogLocale,
    limit: int,
) -> tuple[SafeMatchingProfile, ...]:
    """Return one deterministic bounded batch using fixed-count preference queries."""
    result = await session.execute(eligible_candidate_statement(current, limit=limit))
    rows = cast(tuple[tuple[StudentProfile, ProfilePhoto], ...], tuple(result.tuples().all()))
    return await _project_safe_profiles(session, rows, locale=locale)


async def load_matching_scoring_profiles(
    session: AsyncSession,
    current: EligibleMatchingPrincipal,
    *,
    locale: CatalogLocale,
    candidate_limit: int,
) -> tuple[SafeMatchingProfile | None, tuple[EligibleMatchingCandidate, ...]]:
    """Load the current profile and one bounded eligible pool with fixed query count."""
    if candidate_limit < 1:
        raise ValueError("Candidate query limit must be positive.")

    current_result = await session.execute(
        select(StudentProfile, ProfilePhoto)
        .join(
            ProfilePhoto,
            (ProfilePhoto.profile_id == StudentProfile.id)
            & ProfilePhoto.is_avatar.is_(True)
            & (ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY)
            & ProfilePhoto.deleted_at.is_(None),
        )
        .where(
            StudentProfile.id == current.profile_id,
            StudentProfile.user_id == current.user_id,
            StudentProfile.student_type == current.student_type,
            StudentProfile.deleted_at.is_(None),
        )
    )
    current_rows = cast(
        tuple[tuple[StudentProfile, ProfilePhoto], ...],
        tuple(current_result.tuples().all()),
    )
    if len(current_rows) != 1:
        return None, ()

    candidate_result = await session.execute(
        eligible_candidate_statement(current, limit=candidate_limit)
    )
    candidate_rows = cast(
        tuple[tuple[StudentProfile, ProfilePhoto], ...],
        tuple(candidate_result.tuples().all()),
    )
    projected = await _project_safe_profiles(
        session,
        current_rows + candidate_rows,
        locale=locale,
    )
    if not projected or projected[0].id != current.profile_id:
        return None, ()
    candidates = tuple(
        EligibleMatchingCandidate(
            principal=EligibleMatchingPrincipal(
                user_id=profile.user_id,
                profile_id=profile.id,
                student_type=safe_profile.student_type,
            ),
            profile=safe_profile,
        )
        for (profile, _avatar), safe_profile in zip(
            candidate_rows,
            projected[1:],
            strict=True,
        )
    )
    return projected[0], candidates


async def get_eligible_candidate_avatar(
    session: AsyncSession,
    current: EligibleMatchingPrincipal,
    photo_id: UUID,
) -> ProfilePhoto | None:
    """Authorize one candidate avatar under the same current eligibility predicates."""
    return cast(
        ProfilePhoto | None,
        await session.scalar(
            select(ProfilePhoto)
            .join(StudentProfile, StudentProfile.id == ProfilePhoto.profile_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(
                ProfilePhoto.id == photo_id,
                ProfilePhoto.is_avatar.is_(True),
                ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
                ProfilePhoto.deleted_at.is_(None),
                *_eligible_candidate_conditions(current),
            )
        ),
    )
