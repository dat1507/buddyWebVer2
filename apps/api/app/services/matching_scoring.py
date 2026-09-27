"""Deterministic REC-002 compatibility scoring over REC-001-safe profile data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from fractions import Fraction
from typing import Final
from zoneinfo import ZoneInfo

from app.schemas.matching import (
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.schemas.profile import WeeklyAvailability
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    matching_pair_is_eligible,
)
from app.services.preference_identity import (
    PreferenceIdentityError,
    normalize_preference_key,
)


class MatchingScoringError(ValueError):
    """Raised when a caller attempts to score data outside the REC-001 pair contract."""


@dataclass(frozen=True, slots=True)
class CompatibilityWeights:
    """Fixed V2 percentage-point weights; missing signals are never renormalized."""

    interests: int = 40
    activities: int = 35
    availability: int = 15
    languages: int = 5
    major: int = 5

    def __post_init__(self) -> None:
        values = (
            self.interests,
            self.activities,
            self.availability,
            self.languages,
            self.major,
        )
        if any(value < 0 for value in values) or sum(values) != 100:
            raise ValueError("Compatibility weights must be non-negative and total 100.")


COMPATIBILITY_WEIGHTS: Final = CompatibilityWeights()


@dataclass(frozen=True, slots=True)
class CompatibilitySignalBreakdown:
    """Exact similarity and weighted points for one non-sensitive score signal."""

    similarity: Fraction
    weight: int
    points: Fraction

    def __post_init__(self) -> None:
        if not 0 <= self.similarity <= 1:
            raise ValueError("Compatibility similarity must be between zero and one.")
        if self.weight < 0 or self.points != self.similarity * self.weight:
            raise ValueError("Compatibility signal points are inconsistent.")


@dataclass(frozen=True, slots=True)
class CompatibilityBreakdown:
    """Structured server explanation without profile identities or raw signal values."""

    interests: CompatibilitySignalBreakdown
    activities: CompatibilitySignalBreakdown
    availability: CompatibilitySignalBreakdown
    languages: CompatibilitySignalBreakdown
    major: CompatibilitySignalBreakdown


@dataclass(frozen=True, slots=True)
class CompatibilityScore:
    """Exact score for ranking plus deterministic half-up integer display score."""

    precise_score: Fraction
    score: int
    breakdown: CompatibilityBreakdown
    reference_week_start: date

    def __post_init__(self) -> None:
        signals = (
            self.breakdown.interests,
            self.breakdown.activities,
            self.breakdown.availability,
            self.breakdown.languages,
            self.breakdown.major,
        )
        if self.precise_score != sum((signal.points for signal in signals), Fraction()):
            raise ValueError("Compatibility total is inconsistent with its breakdown.")
        if not 0 <= self.precise_score <= 100 or not 0 <= self.score <= 100:
            raise ValueError("Compatibility score must be between zero and 100.")
        if self.reference_week_start.weekday() != 0:
            raise ValueError("Compatibility reference week must begin on Monday.")


_SignalIdentity = tuple[str, str]
_UtcInterval = tuple[datetime, datetime]


def _normalized_custom_key(label: str) -> str | None:
    try:
        return normalize_preference_key(label)
    except PreferenceIdentityError:
        return None


def _preference_identities(
    values: list[SafeMatchingPreference],
) -> frozenset[_SignalIdentity]:
    identities: set[_SignalIdentity] = set()
    for value in values:
        if value.is_custom:
            key = _normalized_custom_key(value.label)
            if key is not None:
                identities.add(("custom", key))
        elif value.id is not None:
            identities.add(("catalog", str(value.id)))
    return frozenset(identities)


def _language_identities(
    values: list[SafeMatchingLanguage],
) -> frozenset[_SignalIdentity]:
    identities: set[_SignalIdentity] = set()
    for value in values:
        if value.is_custom:
            key = _normalized_custom_key(value.label)
            if key is not None:
                identities.add(("custom", key))
        elif value.code is not None:
            identities.add(("catalog", value.code.casefold()))
    return frozenset(identities)


def _jaccard(
    left: frozenset[_SignalIdentity],
    right: frozenset[_SignalIdentity],
) -> Fraction:
    union = left | right
    if not union:
        return Fraction()
    return Fraction(len(left & right), len(union))


def _exact_overlap(
    left: frozenset[_SignalIdentity],
    right: frozenset[_SignalIdentity],
) -> Fraction:
    return Fraction(1) if left & right else Fraction()


def _normalized_major(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return normalize_preference_key(value)
    except PreferenceIdentityError:
        return None


def _major_similarity(left: str | None, right: str | None) -> Fraction:
    left_key = _normalized_major(left)
    right_key = _normalized_major(right)
    if left_key is None or right_key is None:
        return Fraction()
    return Fraction(1) if left_key == right_key else Fraction()


def _local_minute(
    reference_week_start: date,
    *,
    weekday: int,
    minute: int,
    timezone: ZoneInfo,
) -> datetime:
    local_date = reference_week_start + timedelta(days=weekday - 1)
    if minute == 1440:
        local_date += timedelta(days=1)
        minute = 0
    local_value = datetime.combine(local_date, time.min) + timedelta(minutes=minute)
    return local_value.replace(tzinfo=timezone).astimezone(UTC)


def _merged_utc_intervals(
    availability: WeeklyAvailability | None,
    reference_week_start: date,
) -> tuple[_UtcInterval, ...]:
    if availability is None:
        return ()
    timezone = ZoneInfo(availability.timezone)
    intervals: list[_UtcInterval] = []
    for slot in availability.slots:
        start = _local_minute(
            reference_week_start,
            weekday=slot.weekday,
            minute=slot.start_minute,
            timezone=timezone,
        )
        end = _local_minute(
            reference_week_start,
            weekday=slot.weekday,
            minute=slot.end_minute,
            timezone=timezone,
        )
        if end > start:
            intervals.append((start, end))

    merged: list[_UtcInterval] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return tuple(merged)


def _duration_microseconds(intervals: tuple[_UtcInterval, ...]) -> int:
    return sum((end - start) // timedelta(microseconds=1) for start, end in intervals)


def _intersection_microseconds(
    left: tuple[_UtcInterval, ...],
    right: tuple[_UtcInterval, ...],
) -> int:
    left_index = 0
    right_index = 0
    total = 0
    while left_index < len(left) and right_index < len(right):
        left_start, left_end = left[left_index]
        right_start, right_end = right[right_index]
        start = max(left_start, right_start)
        end = min(left_end, right_end)
        if end > start:
            total += (end - start) // timedelta(microseconds=1)
        if left_end <= right_end:
            left_index += 1
        else:
            right_index += 1
    return total


def _availability_similarity(
    left: WeeklyAvailability | None,
    right: WeeklyAvailability | None,
    reference_week_start: date,
) -> Fraction:
    left_intervals = _merged_utc_intervals(left, reference_week_start)
    right_intervals = _merged_utc_intervals(right, reference_week_start)
    intersection = _intersection_microseconds(left_intervals, right_intervals)
    union = (
        _duration_microseconds(left_intervals)
        + _duration_microseconds(right_intervals)
        - intersection
    )
    if union == 0:
        return Fraction()
    return Fraction(intersection, union)


def _signal(similarity: Fraction, weight: int) -> CompatibilitySignalBreakdown:
    return CompatibilitySignalBreakdown(
        similarity=similarity,
        weight=weight,
        points=similarity * weight,
    )


def _round_half_up(value: Fraction) -> int:
    whole, remainder = divmod(value.numerator, value.denominator)
    return whole + int(remainder * 2 >= value.denominator)


def _require_eligible_safe_pair(
    current: EligibleMatchingPrincipal,
    candidate: EligibleMatchingPrincipal,
    current_profile: SafeMatchingProfile,
    candidate_profile: SafeMatchingProfile,
) -> None:
    principals_match_profiles = (
        current.profile_id == current_profile.id
        and candidate.profile_id == candidate_profile.id
        and current.student_type is current_profile.student_type
        and candidate.student_type is candidate_profile.student_type
    )
    if not principals_match_profiles or not matching_pair_is_eligible(current, candidate):
        raise MatchingScoringError("Compatibility scoring requires an eligible REC-001 pair.")


def score_eligible_pair(
    current: EligibleMatchingPrincipal,
    candidate: EligibleMatchingPrincipal,
    current_profile: SafeMatchingProfile,
    candidate_profile: SafeMatchingProfile,
    *,
    reference_week_start: date,
) -> CompatibilityScore:
    """Score one REC-001 eligible pair using fixed, exact and symmetric V2 rules."""
    if reference_week_start.weekday() != 0:
        raise MatchingScoringError("Compatibility reference week must begin on Monday.")
    _require_eligible_safe_pair(current, candidate, current_profile, candidate_profile)

    interests = _signal(
        _jaccard(
            _preference_identities(current_profile.interests),
            _preference_identities(candidate_profile.interests),
        ),
        COMPATIBILITY_WEIGHTS.interests,
    )
    activities = _signal(
        _jaccard(
            _preference_identities(current_profile.activities),
            _preference_identities(candidate_profile.activities),
        ),
        COMPATIBILITY_WEIGHTS.activities,
    )
    availability = _signal(
        _availability_similarity(
            current_profile.availability,
            candidate_profile.availability,
            reference_week_start,
        ),
        COMPATIBILITY_WEIGHTS.availability,
    )
    languages = _signal(
        _exact_overlap(
            _language_identities(current_profile.languages),
            _language_identities(candidate_profile.languages),
        ),
        COMPATIBILITY_WEIGHTS.languages,
    )
    major = _signal(
        _major_similarity(current_profile.major, candidate_profile.major),
        COMPATIBILITY_WEIGHTS.major,
    )
    breakdown = CompatibilityBreakdown(
        interests=interests,
        activities=activities,
        availability=availability,
        languages=languages,
        major=major,
    )
    precise_score = sum(
        (
            interests.points,
            activities.points,
            availability.points,
            languages.points,
            major.points,
        ),
        Fraction(),
    )
    return CompatibilityScore(
        precise_score=precise_score,
        score=_round_half_up(precise_score),
        breakdown=breakdown,
        reference_week_start=reference_week_start,
    )
