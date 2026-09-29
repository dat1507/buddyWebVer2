"""Owner-filtered, bounded invitation read projections for INV-004."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import ceil
from typing import Final, Literal, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Activity,
    Interest,
    InvitationStatus,
    Language,
    LanguageProficiency,
    MatchingInvitation,
    PreferenceKind,
    ProfileActivity,
    ProfileCustomPreference,
    ProfileInterest,
    ProfileLanguage,
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    StudentType,
)
from app.schemas.matching import (
    CompatibilityExplanation,
    IncomingInvitation,
    IncomingInvitationListResponse,
    SafeInvitationProfile,
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
    SentInvitation,
    SentInvitationListResponse,
)
from app.schemas.profile import WeeklyAvailability
from app.schemas.profile_catalog import CatalogLocale
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_expiry import effective_pending_predicate
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    matching_pair_is_eligible,
)
from app.services.matching_recommendations import project_compatibility_explanation
from app.services.matching_scoring import score_eligible_pair

DEFAULT_INVITATION_PAGE_SIZE: Final = 20
MAX_INVITATION_PAGE_SIZE: Final = 50

Clock = Callable[[], datetime]
_InvitationView = Literal["incoming", "sent"]


class InvitationReadStateError(RuntimeError):
    """Raised when persisted invitation/profile state cannot form a safe projection."""


@dataclass(frozen=True, slots=True)
class _InvitationRow:
    id: UUID
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    participant_user_id: UUID
    message: str | None


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invitation read timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _validate_page(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("Invitation page must be positive.")
    if not 1 <= page_size <= MAX_INVITATION_PAGE_SIZE:
        raise ValueError("Invitation page size is outside the supported range.")


def _validate_reference_week(reference_week_start: date) -> None:
    if reference_week_start.weekday() != 0:
        raise ValueError("Invitation reference week must begin on Monday.")


def _visibility_conditions(
    view: _InvitationView,
    *,
    owner_user_id: UUID,
    at: datetime,
) -> tuple[ColumnElement[bool], ...]:
    common: tuple[ColumnElement[bool], ...] = (MatchingInvitation.deleted_at.is_(None),)
    if view == "incoming":
        return (
            MatchingInvitation.recipient_id == owner_user_id,
            effective_pending_predicate(at=at),
            *common,
        )
    return (
        MatchingInvitation.sender_id == owner_user_id,
        or_(
            effective_pending_predicate(at=at),
            and_(
                MatchingInvitation.status == InvitationStatus.ACCEPTED,
                MatchingInvitation.sender_hidden_at.is_(None),
            ),
        ),
        *common,
    )


async def _list_invitation_rows(
    session: AsyncSession,
    *,
    view: _InvitationView,
    owner_user_id: UUID,
    page: int,
    page_size: int,
    at: datetime,
) -> tuple[tuple[_InvitationRow, ...], int]:
    conditions = _visibility_conditions(view, owner_user_id=owner_user_id, at=at)
    total = int(
        await session.scalar(select(func.count(MatchingInvitation.id)).where(*conditions)) or 0
    )
    common_columns = (
        MatchingInvitation.id,
        MatchingInvitation.status,
        MatchingInvitation.created_at,
        MatchingInvitation.expires_at,
    )
    if view == "incoming":
        result = await session.execute(
            select(
                *common_columns,
                MatchingInvitation.sender_id,
                MatchingInvitation.message,
            )
            .where(*conditions)
            .order_by(MatchingInvitation.created_at.desc(), MatchingInvitation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        incoming_rows = cast(
            tuple[
                tuple[UUID, InvitationStatus, datetime, datetime, UUID, str],
                ...,
            ],
            tuple(result.tuples().all()),
        )
        rows = tuple(
            _InvitationRow(
                id=invitation_id,
                status=status,
                created_at=created_at,
                expires_at=expires_at,
                participant_user_id=sender_id,
                message=message,
            )
            for invitation_id, status, created_at, expires_at, sender_id, message in incoming_rows
        )
    else:
        result = await session.execute(
            select(
                *common_columns,
                MatchingInvitation.recipient_id,
            )
            .where(*conditions)
            .order_by(MatchingInvitation.created_at.desc(), MatchingInvitation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        sent_rows = cast(
            tuple[
                tuple[UUID, InvitationStatus, datetime, datetime, UUID],
                ...,
            ],
            tuple(result.tuples().all()),
        )
        rows = tuple(
            _InvitationRow(
                id=invitation_id,
                status=status,
                created_at=created_at,
                expires_at=expires_at,
                participant_user_id=recipient_id,
                message=None,
            )
            for invitation_id, status, created_at, expires_at, recipient_id in sent_rows
        )
    return rows, total


def _localized_label(
    label_en: str,
    label_de: str,
    locale: CatalogLocale,
) -> str:
    return label_de if locale == "de" else label_en


async def _load_invitation_profiles(
    session: AsyncSession,
    user_ids: tuple[UUID, ...],
    *,
    locale: CatalogLocale,
) -> dict[UUID, SafeInvitationProfile]:
    """Batch public fields/preferences in five fixed queries without loading User rows."""
    if not user_ids:
        return {}
    base_result = await session.execute(
        select(
            StudentProfile.user_id,
            StudentProfile.id,
            StudentProfile.display_name,
            StudentProfile.student_type,
            StudentProfile.major,
            StudentProfile.availability,
            ProfilePhoto.id,
            ProfilePhoto.width,
            ProfilePhoto.height,
        )
        .outerjoin(
            ProfilePhoto,
            (ProfilePhoto.profile_id == StudentProfile.id)
            & ProfilePhoto.is_avatar.is_(True)
            & (ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY)
            & ProfilePhoto.deleted_at.is_(None),
        )
        .where(
            StudentProfile.user_id.in_(user_ids),
            StudentProfile.deleted_at.is_(None),
        )
        .order_by(StudentProfile.user_id)
    )
    base_rows = cast(
        tuple[
            tuple[
                UUID,
                UUID,
                str | None,
                StudentType | None,
                str | None,
                dict[str, object] | None,
                UUID | None,
                int | None,
                int | None,
            ],
            ...,
        ],
        tuple(base_result.tuples().all()),
    )
    if not base_rows:
        return {}
    profile_ids = tuple(row[1] for row in base_rows)

    interest_result = await session.execute(
        select(
            ProfileInterest.profile_id,
            Interest.id,
            Interest.code,
            Interest.label_en,
            Interest.label_de,
        )
        .join(Interest, Interest.id == ProfileInterest.interest_id)
        .where(
            ProfileInterest.profile_id.in_(profile_ids),
            Interest.is_active.is_(True),
            Interest.deleted_at.is_(None),
        )
        .order_by(ProfileInterest.profile_id, Interest.category, Interest.code)
    )
    interest_rows = cast(
        tuple[tuple[UUID, UUID, str, str, str], ...],
        tuple(interest_result.tuples().all()),
    )
    language_result = await session.execute(
        select(
            ProfileLanguage.profile_id,
            Language.code,
            Language.label_en,
            Language.label_de,
            ProfileLanguage.proficiency,
        )
        .join(Language, Language.code == ProfileLanguage.language_code)
        .where(
            ProfileLanguage.profile_id.in_(profile_ids),
            Language.is_active.is_(True),
        )
        .order_by(ProfileLanguage.profile_id, Language.code)
    )
    language_rows = cast(
        tuple[tuple[UUID, str, str, str, LanguageProficiency], ...],
        tuple(language_result.tuples().all()),
    )
    activity_result = await session.execute(
        select(
            ProfileActivity.profile_id,
            Activity.id,
            Activity.code,
            Activity.label_en,
            Activity.label_de,
        )
        .join(Activity, Activity.id == ProfileActivity.activity_id)
        .where(
            ProfileActivity.profile_id.in_(profile_ids),
            Activity.is_active.is_(True),
            Activity.deleted_at.is_(None),
        )
        .order_by(ProfileActivity.profile_id, Activity.code)
    )
    activity_rows = cast(
        tuple[tuple[UUID, UUID, str, str, str], ...],
        tuple(activity_result.tuples().all()),
    )
    custom_result = await session.execute(
        select(
            ProfileCustomPreference.profile_id,
            ProfileCustomPreference.kind,
            ProfileCustomPreference.display_label,
            ProfileCustomPreference.proficiency,
        )
        .where(
            ProfileCustomPreference.profile_id.in_(profile_ids),
            ProfileCustomPreference.deleted_at.is_(None),
        )
        .order_by(
            ProfileCustomPreference.profile_id,
            ProfileCustomPreference.kind,
            ProfileCustomPreference.display_label,
            ProfileCustomPreference.id,
        )
    )
    custom_rows = cast(
        tuple[tuple[UUID, PreferenceKind, str, LanguageProficiency | None], ...],
        tuple(custom_result.tuples().all()),
    )

    interests: defaultdict[UUID, list[SafeMatchingPreference]] = defaultdict(list)
    languages: defaultdict[UUID, list[SafeMatchingLanguage]] = defaultdict(list)
    activities: defaultdict[UUID, list[SafeMatchingPreference]] = defaultdict(list)
    for profile_id, item_id, code, label_en, label_de in interest_rows:
        interests[profile_id].append(
            SafeMatchingPreference(
                id=item_id,
                code=code,
                label=_localized_label(label_en, label_de, locale),
                is_custom=False,
            )
        )
    for profile_id, code, label_en, label_de, predefined_proficiency in language_rows:
        languages[profile_id].append(
            SafeMatchingLanguage(
                code=code,
                label=_localized_label(label_en, label_de, locale),
                proficiency=predefined_proficiency,
                is_custom=False,
            )
        )
    for profile_id, item_id, code, label_en, label_de in activity_rows:
        activities[profile_id].append(
            SafeMatchingPreference(
                id=item_id,
                code=code,
                label=_localized_label(label_en, label_de, locale),
                is_custom=False,
            )
        )
    for profile_id, kind, display_label, custom_proficiency in custom_rows:
        if kind is PreferenceKind.INTEREST:
            interests[profile_id].append(
                SafeMatchingPreference(
                    id=None,
                    code=None,
                    label=display_label,
                    is_custom=True,
                )
            )
        elif kind is PreferenceKind.ACTIVITY:
            activities[profile_id].append(
                SafeMatchingPreference(
                    id=None,
                    code=None,
                    label=display_label,
                    is_custom=True,
                )
            )
        elif kind is PreferenceKind.LANGUAGE and custom_proficiency is not None:
            languages[profile_id].append(
                SafeMatchingLanguage(
                    code=None,
                    label=display_label,
                    proficiency=custom_proficiency,
                    is_custom=True,
                )
            )

    profiles: dict[UUID, SafeInvitationProfile] = {}
    for (
        user_id,
        profile_id,
        display_name,
        student_type,
        major,
        availability_value,
        avatar_id,
        avatar_width,
        avatar_height,
    ) in base_rows:
        avatar = (
            SafeMatchingAvatar(
                id=avatar_id,
                width=avatar_width,
                height=avatar_height,
            )
            if avatar_id is not None and avatar_width is not None and avatar_height is not None
            else None
        )
        availability = (
            WeeklyAvailability.model_validate(availability_value)
            if availability_value is not None
            else None
        )
        profiles[user_id] = SafeInvitationProfile(
            id=profile_id,
            display_name=display_name,
            student_type=student_type,
            major=major,
            avatar=avatar,
            interests=interests[profile_id],
            languages=languages[profile_id],
            activities=activities[profile_id],
            availability=availability,
        )
    return profiles


def _as_scoring_profile(profile: SafeInvitationProfile) -> SafeMatchingProfile | None:
    if (
        profile.student_type is None
        or profile.avatar is None
        or not profile.interests
        or not profile.languages
    ):
        return None
    return SafeMatchingProfile(
        id=profile.id,
        display_name=profile.display_name,
        student_type=profile.student_type,
        major=profile.major,
        avatar=profile.avatar,
        interests=profile.interests,
        languages=profile.languages,
        activities=profile.activities,
        availability=profile.availability,
    )


def _current_compatibility(
    *,
    current_user_id: UUID,
    current_profile: SafeInvitationProfile,
    participant_user_id: UUID,
    participant_profile: SafeInvitationProfile,
    reference_week_start: date,
) -> tuple[int | None, CompatibilityExplanation | None]:
    scoring_current = _as_scoring_profile(current_profile)
    scoring_participant = _as_scoring_profile(participant_profile)
    if scoring_current is None or scoring_participant is None:
        return None, None
    assert current_profile.student_type is not None
    assert participant_profile.student_type is not None
    current = EligibleMatchingPrincipal(
        user_id=current_user_id,
        profile_id=current_profile.id,
        student_type=current_profile.student_type,
    )
    participant = EligibleMatchingPrincipal(
        user_id=participant_user_id,
        profile_id=participant_profile.id,
        student_type=participant_profile.student_type,
    )
    if not matching_pair_is_eligible(current, participant):
        return None, None
    score = score_eligible_pair(
        current,
        participant,
        scoring_current,
        scoring_participant,
        reference_week_start=reference_week_start,
    )
    return score.score, project_compatibility_explanation(score)


async def list_incoming_invitations(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    locale: CatalogLocale,
    page: int,
    page_size: int,
    reference_week_start: date,
    clock: Clock = _system_utc_now,
) -> IncomingInvitationListResponse:
    """Return only the owner's effective PENDING incoming invitations."""
    _validate_page(page, page_size)
    _validate_reference_week(reference_week_start)
    rows, total = await _list_invitation_rows(
        session,
        view="incoming",
        owner_user_id=current.user.id,
        page=page,
        page_size=page_size,
        at=_utc_now(clock),
    )
    if not rows:
        return IncomingInvitationListResponse(
            items=[],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
            reference_week_start=reference_week_start,
        )
    user_ids = tuple(dict.fromkeys((current.user.id, *(row.participant_user_id for row in rows))))
    profiles = await _load_invitation_profiles(session, user_ids, locale=locale)
    current_profile = profiles.get(current.user.id)
    if rows and current_profile is None:
        raise InvitationReadStateError

    items: list[IncomingInvitation] = []
    for row in rows:
        sender = profiles.get(row.participant_user_id)
        if sender is None or current_profile is None or row.message is None:
            raise InvitationReadStateError
        score, explanation = _current_compatibility(
            current_user_id=current.user.id,
            current_profile=current_profile,
            participant_user_id=row.participant_user_id,
            participant_profile=sender,
            reference_week_start=reference_week_start,
        )
        items.append(
            IncomingInvitation(
                id=row.id,
                status=row.status,
                created_at=row.created_at,
                expires_at=row.expires_at,
                sender=sender,
                message=row.message,
                score=score,
                explanation=explanation,
            )
        )
    return IncomingInvitationListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
        reference_week_start=reference_week_start,
    )


async def list_sent_invitations(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    locale: CatalogLocale,
    page: int,
    page_size: int,
    reference_week_start: date,
    clock: Clock = _system_utc_now,
) -> SentInvitationListResponse:
    """Return only the owner's effective PENDING and unhidden ACCEPTED sent rows."""
    _validate_page(page, page_size)
    _validate_reference_week(reference_week_start)
    rows, total = await _list_invitation_rows(
        session,
        view="sent",
        owner_user_id=current.user.id,
        page=page,
        page_size=page_size,
        at=_utc_now(clock),
    )
    if not rows:
        return SentInvitationListResponse(
            items=[],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
            reference_week_start=reference_week_start,
        )
    user_ids = tuple(dict.fromkeys((current.user.id, *(row.participant_user_id for row in rows))))
    profiles = await _load_invitation_profiles(session, user_ids, locale=locale)
    current_profile = profiles.get(current.user.id)
    if rows and current_profile is None:
        raise InvitationReadStateError

    items: list[SentInvitation] = []
    for row in rows:
        recipient = profiles.get(row.participant_user_id)
        if recipient is None or current_profile is None:
            raise InvitationReadStateError
        score, explanation = _current_compatibility(
            current_user_id=current.user.id,
            current_profile=current_profile,
            participant_user_id=row.participant_user_id,
            participant_profile=recipient,
            reference_week_start=reference_week_start,
        )
        items.append(
            SentInvitation(
                id=row.id,
                status=row.status,
                created_at=row.created_at,
                expires_at=row.expires_at,
                recipient=recipient,
                score=score,
                explanation=explanation,
            )
        )
    return SentInvitationListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
        reference_week_start=reference_week_start,
    )
