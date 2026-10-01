"""Bounded, aggregate-only ADMIN matching monitoring queries."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from math import ceil
from typing import Final, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.models import (
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
    MatchStatus,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.schemas.admin_matching import (
    AdminInvitationStateCounts,
    AdminMatchingParticipantDetail,
    AdminMatchingParticipantListResponse,
    AdminMatchingParticipantSummary,
    AdminMatchingStats,
)
from app.schemas.profile_catalog import CatalogLocale
from app.services.invitation_expiry import effective_pending_predicate
from app.services.invitation_reads import load_safe_participant_profiles

DEFAULT_ADMIN_MATCHING_PAGE_SIZE: Final = 20
MAX_ADMIN_MATCHING_PAGE_SIZE: Final = 50

Clock = Callable[[], datetime]


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Admin matching timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _participant_conditions() -> tuple[ColumnElement[bool], ...]:
    return (
        User.role == UserRole.USER,
        User.deleted_at.is_(None),
        StudentProfile.deleted_at.is_(None),
    )


def _active_match_conditions() -> tuple[ColumnElement[bool], ...]:
    return (
        BuddyMatch.status == MatchStatus.ACTIVE,
        BuddyMatch.deleted_at.is_(None),
    )


def _buddy_count_subquery() -> Subquery:
    active_participants = union_all(
        select(BuddyMatch.participant_one_profile_id.label("profile_id")).where(
            *_active_match_conditions()
        ),
        select(BuddyMatch.participant_two_profile_id.label("profile_id")).where(
            *_active_match_conditions()
        ),
    ).subquery("active_buddy_participants")
    return (
        select(
            active_participants.c.profile_id,
            func.count().label("buddy_count"),
        )
        .group_by(active_participants.c.profile_id)
        .subquery("active_buddy_counts")
    )


def _validate_page(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("Admin matching page must be positive.")
    if not 1 <= page_size <= MAX_ADMIN_MATCHING_PAGE_SIZE:
        raise ValueError("Admin matching page size is outside the supported range.")


async def get_admin_matching_stats(
    session: AsyncSession,
    *,
    clock: Clock = _system_utc_now,
) -> AdminMatchingStats:
    """Return fixed-query matching aggregates using effective invitation expiry."""
    at = _utc_now(clock)
    buddy_counts = _buddy_count_subquery()
    participant_result = await session.execute(
        select(
            func.count(StudentProfile.id),
            func.count(StudentProfile.id).filter(User.email_verified_at.is_not(None)),
            func.count(StudentProfile.id).filter(func.coalesce(buddy_counts.c.buddy_count, 0) == 0),
        )
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(buddy_counts, buddy_counts.c.profile_id == StudentProfile.id)
        .where(*_participant_conditions())
    )
    participant_count, verified_count, zero_buddy_count = participant_result.tuples().one()

    effective_expired = or_(
        MatchingInvitation.status == InvitationStatus.EXPIRED,
        and_(
            MatchingInvitation.status == InvitationStatus.PENDING,
            MatchingInvitation.expires_at <= at,
        ),
    )
    invitation_result = await session.execute(
        select(
            func.count(MatchingInvitation.id).filter(effective_pending_predicate(at=at)),
            func.count(MatchingInvitation.id).filter(
                MatchingInvitation.status == InvitationStatus.ACCEPTED
            ),
            func.count(MatchingInvitation.id).filter(
                MatchingInvitation.status == InvitationStatus.DECLINED
            ),
            func.count(MatchingInvitation.id).filter(
                MatchingInvitation.status == InvitationStatus.CANCELLED
            ),
            func.count(MatchingInvitation.id).filter(effective_expired),
        ).where(MatchingInvitation.deleted_at.is_(None))
    )
    pending, accepted, declined, cancelled, expired = invitation_result.tuples().one()
    active_match_count = int(
        await session.scalar(select(func.count(BuddyMatch.id)).where(*_active_match_conditions()))
        or 0
    )
    return AdminMatchingStats(
        participant_count=participant_count,
        verified_participant_count=verified_count,
        active_match_count=active_match_count,
        zero_buddy_participant_count=zero_buddy_count,
        invitations=AdminInvitationStateCounts(
            pending=pending,
            accepted=accepted,
            declined=declined,
            cancelled=cancelled,
            expired=expired,
        ),
    )


async def list_admin_matching_participants(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    student_type: StudentType | None,
    verified: bool | None,
    zero_buddies_only: bool,
) -> AdminMatchingParticipantListResponse:
    """Return one safe participant page with a batched ACTIVE Buddy count."""
    _validate_page(page, page_size)
    buddy_counts = _buddy_count_subquery()
    buddy_count = func.coalesce(buddy_counts.c.buddy_count, 0)
    conditions = list(_participant_conditions())
    if student_type is not None:
        conditions.append(StudentProfile.student_type == student_type)
    if verified is not None:
        conditions.append(
            User.email_verified_at.is_not(None) if verified else User.email_verified_at.is_(None)
        )
    if zero_buddies_only:
        conditions.append(buddy_count == 0)

    source = (
        select(StudentProfile.id)
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(buddy_counts, buddy_counts.c.profile_id == StudentProfile.id)
        .where(*conditions)
    ).subquery("filtered_matching_participants")
    total = int(await session.scalar(select(func.count()).select_from(source)) or 0)

    result = await session.execute(
        select(
            StudentProfile.id,
            StudentProfile.display_name,
            StudentProfile.student_type,
            User.is_active,
            User.email_verified_at,
            StudentProfile.matching_opt_in,
            buddy_count.label("buddy_count"),
        )
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(buddy_counts, buddy_counts.c.profile_id == StudentProfile.id)
        .where(*conditions)
        .order_by(StudentProfile.created_at.desc(), StudentProfile.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = cast(
        tuple[
            tuple[UUID, str | None, StudentType | None, bool, datetime | None, bool, int],
            ...,
        ],
        tuple(result.tuples().all()),
    )
    return AdminMatchingParticipantListResponse(
        items=[
            AdminMatchingParticipantSummary(
                profile_id=profile_id,
                display_name=display_name,
                student_type=row_student_type,
                is_active=is_active,
                email_verified=email_verified_at is not None,
                matching_opt_in=matching_opt_in,
                buddy_count=row_buddy_count,
            )
            for (
                profile_id,
                display_name,
                row_student_type,
                is_active,
                email_verified_at,
                matching_opt_in,
                row_buddy_count,
            ) in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


async def get_admin_matching_participant_detail(
    session: AsyncSession,
    *,
    profile_id: UUID,
    locale: CatalogLocale,
) -> AdminMatchingParticipantDetail | None:
    """Return one matching-safe profile through a single batched projection call."""
    buddy_counts = _buddy_count_subquery()
    result = await session.execute(
        select(
            User.id,
            User.is_active,
            User.email_verified_at,
            StudentProfile.matching_opt_in,
            func.coalesce(buddy_counts.c.buddy_count, 0),
        )
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(buddy_counts, buddy_counts.c.profile_id == StudentProfile.id)
        .where(StudentProfile.id == profile_id, *_participant_conditions())
    )
    row = result.tuples().one_or_none()
    if row is None:
        return None
    user_id, is_active, email_verified_at, matching_opt_in, buddy_count = cast(
        tuple[UUID, bool, datetime | None, bool, int],
        row,
    )
    profiles = await load_safe_participant_profiles(session, (user_id,), locale=locale)
    profile = profiles.get(user_id)
    if profile is None:
        return None
    return AdminMatchingParticipantDetail(
        profile=profile,
        is_active=is_active,
        email_verified=email_verified_at is not None,
        matching_opt_in=matching_opt_in,
        buddy_count=buddy_count,
    )
