"""REC-003 read-only ranked recommendations over REC-001/REC-002 contracts."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from math import ceil
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.matching import (
    CompatibilityExplanation,
    CompatibilitySignalExplanation,
    MatchingRecommendation,
    MatchingRecommendationListResponse,
)
from app.schemas.profile_catalog import CatalogLocale
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    load_matching_scoring_profiles,
)
from app.services.matching_scoring import (
    CompatibilityScore,
    CompatibilitySignalBreakdown,
    score_eligible_pair,
)

DEFAULT_RECOMMENDATION_PAGE_SIZE: Final = 20
MAX_RECOMMENDATION_PAGE_SIZE: Final = 50
MAX_RECOMMENDATION_CANDIDATES: Final = 500
_PUBLIC_SCORE_DECIMAL_PLACES: Final = 6


class MatchingRecommendationError(RuntimeError):
    """Base class for sanitized REC-003 read failures."""


class MatchingRecommendationStateError(MatchingRecommendationError):
    """Raised when current eligibility changes during a recommendation read."""


class MatchingRecommendationCapacityError(MatchingRecommendationError):
    """Raised instead of silently truncating a candidate pool beyond the safe bound."""


def current_reference_week_start(now: datetime | None = None) -> date:
    """Return the UTC calendar Monday used for timezone-aware weekly availability."""
    current_date = (now or datetime.now(UTC)).date()
    return current_date - timedelta(days=current_date.weekday())


def _public_number(value: Fraction) -> float:
    return round(float(value), _PUBLIC_SCORE_DECIMAL_PLACES)


def _public_signal(
    signal: CompatibilitySignalBreakdown,
) -> CompatibilitySignalExplanation:
    return CompatibilitySignalExplanation(
        similarity=_public_number(signal.similarity),
        weight=signal.weight,
        points=_public_number(signal.points),
    )


def project_compatibility_explanation(
    score: CompatibilityScore,
) -> CompatibilityExplanation:
    """Project an exact REC-002 score into the shared public explanation DTO."""
    return CompatibilityExplanation(
        interests=_public_signal(score.breakdown.interests),
        activities=_public_signal(score.breakdown.activities),
        availability=_public_signal(score.breakdown.availability),
        languages=_public_signal(score.breakdown.languages),
        major=_public_signal(score.breakdown.major),
    )


async def list_ranked_matching_recommendations(
    session: AsyncSession,
    current: EligibleMatchingPrincipal,
    *,
    locale: CatalogLocale,
    page: int,
    page_size: int,
    reference_week_start: date,
) -> MatchingRecommendationListResponse:
    """Return a bounded deterministic page without creating or mutating domain state."""
    if page < 1:
        raise ValueError("Recommendation page must be positive.")
    if not 1 <= page_size <= MAX_RECOMMENDATION_PAGE_SIZE:
        raise ValueError("Recommendation page size is outside the supported range.")
    if reference_week_start.weekday() != 0:
        raise ValueError("Recommendation reference week must begin on Monday.")

    current_profile, candidates = await load_matching_scoring_profiles(
        session,
        current,
        locale=locale,
        candidate_limit=MAX_RECOMMENDATION_CANDIDATES + 1,
    )
    if current_profile is None:
        raise MatchingRecommendationStateError
    if len(candidates) > MAX_RECOMMENDATION_CANDIDATES:
        raise MatchingRecommendationCapacityError

    scored = [
        (
            score_eligible_pair(
                current,
                candidate.principal,
                current_profile,
                candidate.profile,
                reference_week_start=reference_week_start,
            ),
            candidate.profile,
        )
        for candidate in candidates
    ]
    scored.sort(key=lambda item: (-item[0].precise_score, item[1].id.int))

    total = len(scored)
    start = (page - 1) * page_size
    items = [
        MatchingRecommendation(
            profile=profile,
            score=score.score,
            explanation=project_compatibility_explanation(score),
        )
        for score, profile in scored[start : start + page_size]
    ]
    return MatchingRecommendationListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
        reference_week_start=reference_week_start,
    )
