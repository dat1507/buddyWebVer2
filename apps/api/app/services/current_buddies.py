"""Owner-filtered ACTIVE Buddy projections for BUDDY-002."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import ceil
from typing import Final, cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    BuddyConversation,
    BuddyMatch,
    MatchStatus,
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
)
from app.schemas.matching import (
    CompatibilityExplanation,
    CurrentBuddy,
    CurrentBuddyListResponse,
)
from app.schemas.profile_catalog import CatalogLocale
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_reads import load_safe_participant_profiles

DEFAULT_CURRENT_BUDDY_PAGE_SIZE: Final = 20
MAX_CURRENT_BUDDY_PAGE_SIZE: Final = 50
_SNAPSHOT_SIGNAL_KEYS: Final = (
    "interests",
    "activities",
    "availability",
    "languages",
    "major",
)
_SNAPSHOT_KEYS: Final = frozenset((*_SNAPSHOT_SIGNAL_KEYS, "reference_week_start"))


class CurrentBuddyReadStateError(RuntimeError):
    """Raised when authoritative relationship state cannot form a safe projection."""


@dataclass(frozen=True, slots=True)
class _CurrentBuddyRow:
    match_id: UUID
    participant_one_user_id: UUID
    participant_two_user_id: UUID
    score: int
    score_breakdown: dict[str, object]
    activated_at: datetime
    conversation_id: UUID | None


def _validate_page(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("Current Buddy page must be positive.")
    if not 1 <= page_size <= MAX_CURRENT_BUDDY_PAGE_SIZE:
        raise ValueError("Current Buddy page size is outside the supported range.")


def _owner_conditions(owner_user_id: UUID) -> tuple[ColumnElement[bool], ...]:
    return (
        BuddyMatch.status == MatchStatus.ACTIVE,
        BuddyMatch.deleted_at.is_(None),
        or_(
            BuddyMatch.participant_one_user_id == owner_user_id,
            BuddyMatch.participant_two_user_id == owner_user_id,
        ),
    )


async def _list_current_buddy_rows(
    session: AsyncSession,
    *,
    owner_user_id: UUID,
    page: int,
    page_size: int,
) -> tuple[tuple[_CurrentBuddyRow, ...], int]:
    conditions = _owner_conditions(owner_user_id)
    total = int(await session.scalar(select(func.count(BuddyMatch.id)).where(*conditions)) or 0)
    result = await session.execute(
        select(
            BuddyMatch.id,
            BuddyMatch.participant_one_user_id,
            BuddyMatch.participant_two_user_id,
            BuddyMatch.score,
            BuddyMatch.score_breakdown,
            BuddyMatch.activated_at,
            BuddyConversation.id,
        )
        .outerjoin(BuddyConversation, BuddyConversation.match_id == BuddyMatch.id)
        .where(*conditions)
        .order_by(BuddyMatch.activated_at.desc(), BuddyMatch.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = cast(
        tuple[
            tuple[UUID, UUID, UUID, int, dict[str, object], datetime, UUID | None],
            ...,
        ],
        tuple(result.tuples().all()),
    )
    return (
        tuple(
            _CurrentBuddyRow(
                match_id=match_id,
                participant_one_user_id=participant_one_user_id,
                participant_two_user_id=participant_two_user_id,
                score=score,
                score_breakdown=score_breakdown,
                activated_at=activated_at,
                conversation_id=conversation_id,
            )
            for (
                match_id,
                participant_one_user_id,
                participant_two_user_id,
                score,
                score_breakdown,
                activated_at,
                conversation_id,
            ) in rows
        ),
        total,
    )


def _other_participant_id(row: _CurrentBuddyRow, owner_user_id: UUID) -> UUID:
    if (
        row.participant_one_user_id == owner_user_id
        and row.participant_two_user_id != owner_user_id
    ):
        return row.participant_two_user_id
    if (
        row.participant_two_user_id == owner_user_id
        and row.participant_one_user_id != owner_user_id
    ):
        return row.participant_one_user_id
    raise CurrentBuddyReadStateError("Current Buddy participant state is invalid.")


def _compatibility_snapshot(
    value: dict[str, object],
) -> tuple[date, CompatibilityExplanation]:
    if set(value) != _SNAPSHOT_KEYS:
        raise CurrentBuddyReadStateError("Current Buddy compatibility state is invalid.")
    raw_reference_week = value["reference_week_start"]
    if not isinstance(raw_reference_week, str):
        raise CurrentBuddyReadStateError("Current Buddy compatibility state is invalid.")
    try:
        reference_week_start = date.fromisoformat(raw_reference_week)
        explanation = CompatibilityExplanation.model_validate(
            {key: value[key] for key in _SNAPSHOT_SIGNAL_KEYS}
        )
    except (ValueError, ValidationError):
        raise CurrentBuddyReadStateError("Current Buddy compatibility state is invalid.") from None
    if reference_week_start.weekday() != 0:
        raise CurrentBuddyReadStateError("Current Buddy compatibility state is invalid.")
    return reference_week_start, explanation


async def list_current_buddies(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    *,
    locale: CatalogLocale,
    page: int,
    page_size: int,
) -> CurrentBuddyListResponse:
    """Return one private deterministic page from authoritative ACTIVE Matches."""
    _validate_page(page, page_size)
    rows, total = await _list_current_buddy_rows(
        session,
        owner_user_id=current.user.id,
        page=page,
        page_size=page_size,
    )
    if not rows:
        return CurrentBuddyListResponse(
            items=[],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    row_other_user_ids = tuple(_other_participant_id(row, current.user.id) for row in rows)
    other_user_ids = tuple(dict.fromkeys(row_other_user_ids))
    profiles = await load_safe_participant_profiles(
        session,
        other_user_ids,
        locale=locale,
    )
    items: list[CurrentBuddy] = []
    for row, other_user_id in zip(rows, row_other_user_ids, strict=True):
        if row.conversation_id is None:
            raise CurrentBuddyReadStateError("Current Buddy conversation is unavailable.")
        profile = profiles.get(other_user_id)
        if profile is None:
            raise CurrentBuddyReadStateError("Current Buddy profile is unavailable.")
        reference_week_start, explanation = _compatibility_snapshot(row.score_breakdown)
        items.append(
            CurrentBuddy(
                match_id=row.match_id,
                conversation_id=row.conversation_id,
                buddy=profile,
                score=row.score,
                explanation=explanation,
                reference_week_start=reference_week_start,
            )
        )
    return CurrentBuddyListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


async def get_active_buddy_avatar(
    session: AsyncSession,
    current: VerifiedBuddyPrincipal,
    photo_id: UUID,
) -> ProfilePhoto | None:
    """Authorize a current avatar through an exact ACTIVE Match participant relation."""
    relationship = or_(
        and_(
            BuddyMatch.participant_one_user_id == current.user.id,
            BuddyMatch.participant_two_profile_id == StudentProfile.id,
        ),
        and_(
            BuddyMatch.participant_two_user_id == current.user.id,
            BuddyMatch.participant_one_profile_id == StudentProfile.id,
        ),
    )
    return cast(
        ProfilePhoto | None,
        await session.scalar(
            select(ProfilePhoto)
            .join(StudentProfile, StudentProfile.id == ProfilePhoto.profile_id)
            .join(BuddyMatch, relationship)
            .where(
                ProfilePhoto.id == photo_id,
                ProfilePhoto.is_avatar.is_(True),
                ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
                ProfilePhoto.deleted_at.is_(None),
                StudentProfile.deleted_at.is_(None),
                BuddyMatch.status == MatchStatus.ACTIVE,
                BuddyMatch.deleted_at.is_(None),
            )
        ),
    )
