"""Backend-owned profile completion and new-pair eligibility derivation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Interest,
    Language,
    ProfileInterest,
    ProfileLanguage,
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas.profile_completion import (
    MatchingIneligibilityReason,
    ProfileCompletionResponse,
    ProfileCompletionStatus,
    ProfileMissingField,
)
from app.services.profiles import ProfileAccessError, get_or_create_own_profile_for_update


async def count_active_match_reservations(
    _session: AsyncSession,
    _profile_id: UUID,
) -> int:
    """Return the staged reservation count until MATCH-007 installs the real reader.

    Matching is not released before MATCH-007, so BE-016 intentionally has no Match-table
    dependency. Keeping this boundary explicit lets MATCH-007 replace the implementation without
    changing the readiness contract.
    """
    return 0


async def _count_ready_avatars(session: AsyncSession, profile_id: UUID) -> int:
    value = await session.scalar(
        select(func.count(ProfilePhoto.id)).where(
            ProfilePhoto.profile_id == profile_id,
            ProfilePhoto.is_avatar.is_(True),
            ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
            ProfilePhoto.deleted_at.is_(None),
        )
    )
    return int(value or 0)


async def _count_valid_interests(session: AsyncSession, profile_id: UUID) -> int:
    value = await session.scalar(
        select(func.count(ProfileInterest.interest_id))
        .join(Interest, Interest.id == ProfileInterest.interest_id)
        .where(
            ProfileInterest.profile_id == profile_id,
            Interest.is_active.is_(True),
            Interest.deleted_at.is_(None),
        )
    )
    return int(value or 0)


async def _count_valid_languages(session: AsyncSession, profile_id: UUID) -> int:
    value = await session.scalar(
        select(func.count(ProfileLanguage.language_code))
        .join(Language, Language.code == ProfileLanguage.language_code)
        .where(
            ProfileLanguage.profile_id == profile_id,
            Language.is_active.is_(True),
        )
    )
    return int(value or 0)


def derive_profile_completion(
    owner: User,
    profile: StudentProfile,
    *,
    ready_avatar_count: int,
    valid_interest_count: int,
    valid_language_count: int,
    active_reservation_count: int,
) -> ProfileCompletionResponse:
    """Derive readiness only from persisted server-owned state."""
    missing_fields: list[ProfileMissingField] = []
    full_name = profile.full_name.strip() if profile.full_name is not None else ""
    if not 1 <= len(full_name) <= 120:
        missing_fields.append(ProfileMissingField.FULL_NAME)
    if profile.student_type is None:
        missing_fields.append(ProfileMissingField.STUDENT_TYPE)
    if ready_avatar_count != 1:
        missing_fields.append(ProfileMissingField.AVATAR)
    if not 1 <= valid_interest_count <= 20:
        missing_fields.append(ProfileMissingField.INTERESTS)
    if not 1 <= valid_language_count <= 10:
        missing_fields.append(ProfileMissingField.LANGUAGES)

    status = (
        ProfileCompletionStatus.COMPLETE
        if not missing_fields
        else ProfileCompletionStatus.INCOMPLETE
    )
    reasons: list[MatchingIneligibilityReason] = []
    if missing_fields:
        reasons.append(MatchingIneligibilityReason.PROFILE_INCOMPLETE)
    if not owner.is_active:
        reasons.append(MatchingIneligibilityReason.ACCOUNT_INACTIVE)
    if owner.deleted_at is not None:
        reasons.append(MatchingIneligibilityReason.ACCOUNT_DELETED)
    if owner.role is UserRole.USER and owner.email_verified_at is None:
        reasons.append(MatchingIneligibilityReason.EMAIL_VERIFICATION_REQUIRED)
    if not profile.matching_opt_in:
        reasons.append(MatchingIneligibilityReason.MATCHING_OPT_IN_REQUIRED)
    if active_reservation_count > 0:
        reasons.append(MatchingIneligibilityReason.ACTIVE_MATCH_RESERVATION)

    account_is_eligible = (
        owner.role is UserRole.USER
        and owner.is_active
        and owner.deleted_at is None
        and owner.email_verified_at is not None
    )
    return ProfileCompletionResponse(
        status=status,
        percentage=(5 - len(missing_fields)) * 20,
        missing_fields=missing_fields,
        matching_eligible=(
            status is ProfileCompletionStatus.COMPLETE
            and account_is_eligible
            and profile.matching_opt_in
            and active_reservation_count == 0
        ),
        reasons=reasons,
    )


async def get_own_profile_completion(
    session: AsyncSession,
    owner: User,
) -> ProfileCompletionResponse:
    """Lock the owner profile, derive readiness, and stage the first completion milestone."""
    profile = await get_or_create_own_profile_for_update(session, owner)
    if profile.deleted_at is not None or profile.user_id != owner.id:
        raise ProfileAccessError("Profile completion access is not permitted.")

    completion = derive_profile_completion(
        owner,
        profile,
        ready_avatar_count=await _count_ready_avatars(session, profile.id),
        valid_interest_count=await _count_valid_interests(session, profile.id),
        valid_language_count=await _count_valid_languages(session, profile.id),
        active_reservation_count=await count_active_match_reservations(session, profile.id),
    )
    if (
        completion.status is ProfileCompletionStatus.COMPLETE
        and profile.onboarding_completed_at is None
    ):
        profile.onboarding_completed_at = datetime.now(UTC)
        await session.flush()
    return completion
