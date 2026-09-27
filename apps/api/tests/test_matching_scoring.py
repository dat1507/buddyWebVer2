"""REC-002 golden, property, boundary, and privacy tests."""

from __future__ import annotations

from datetime import date
from fractions import Fraction
from inspect import signature
from uuid import UUID

import pytest

from app.models import LanguageProficiency, StudentType
from app.schemas.matching import (
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.schemas.profile import WeeklyAvailability
from app.services.matching_eligibility import EligibleMatchingPrincipal
from app.services.matching_scoring import (
    COMPATIBILITY_WEIGHTS,
    CompatibilityScore,
    MatchingScoringError,
    score_eligible_pair,
)

REFERENCE_WEEK = date(2026, 1, 5)


def _catalog_preference(identifier: int, code: str) -> SafeMatchingPreference:
    return SafeMatchingPreference(
        id=UUID(int=identifier),
        code=code,
        label=code.title(),
        is_custom=False,
    )


def _custom_preference(label: str) -> SafeMatchingPreference:
    return SafeMatchingPreference(id=None, code=None, label=label, is_custom=True)


def _catalog_language(
    code: str,
    proficiency: LanguageProficiency = LanguageProficiency.INTERMEDIATE,
) -> SafeMatchingLanguage:
    return SafeMatchingLanguage(
        code=code,
        label=code.upper(),
        proficiency=proficiency,
        is_custom=False,
    )


def _custom_language(
    label: str,
    proficiency: LanguageProficiency = LanguageProficiency.INTERMEDIATE,
) -> SafeMatchingLanguage:
    return SafeMatchingLanguage(
        code=None,
        label=label,
        proficiency=proficiency,
        is_custom=True,
    )


def _availability(
    timezone: str,
    *,
    weekday: int = 1,
    start_minute: int,
    end_minute: int,
) -> WeeklyAvailability:
    return WeeklyAvailability.model_validate(
        {
            "timezone": timezone,
            "slots": [
                {
                    "weekday": weekday,
                    "start_minute": start_minute,
                    "end_minute": end_minute,
                }
            ],
        }
    )


def _profile(
    identifier: int,
    student_type: StudentType,
    *,
    interests: list[SafeMatchingPreference] | None = None,
    languages: list[SafeMatchingLanguage] | None = None,
    activities: list[SafeMatchingPreference] | None = None,
    availability: WeeklyAvailability | None = None,
    major: str | None = None,
) -> SafeMatchingProfile:
    return SafeMatchingProfile(
        id=UUID(int=identifier),
        display_name=f"Buddy {identifier}",
        student_type=student_type,
        major=major,
        avatar=SafeMatchingAvatar(
            id=UUID(int=identifier + 10_000),
            width=640,
            height=480,
        ),
        interests=interests or [_catalog_preference(identifier + 20_000, "interest")],
        languages=languages or [_catalog_language(f"q{identifier:02d}")],
        activities=activities or [],
        availability=availability,
    )


def _principal(profile: SafeMatchingProfile, user_identifier: int) -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=UUID(int=user_identifier),
        profile_id=profile.id,
        student_type=profile.student_type,
    )


def _score(
    current: SafeMatchingProfile,
    candidate: SafeMatchingProfile,
    *,
    reference_week: date = REFERENCE_WEEK,
) -> CompatibilityScore:
    return score_eligible_pair(
        _principal(current, 101),
        _principal(candidate, 202),
        current,
        candidate,
        reference_week_start=reference_week,
    )


def test_fixed_weights_are_exact_and_never_renormalized() -> None:
    weights = (
        COMPATIBILITY_WEIGHTS.interests,
        COMPATIBILITY_WEIGHTS.activities,
        COMPATIBILITY_WEIGHTS.availability,
        COMPATIBILITY_WEIGHTS.languages,
        COMPATIBILITY_WEIGHTS.major,
    )

    assert weights == (40, 35, 15, 5, 5)
    assert sum(weights) == 100


def test_golden_fixture_produces_exact_breakdown_and_half_up_display_score() -> None:
    current = _profile(
        1,
        StudentType.VIETNAMESE,
        interests=[
            _catalog_preference(11, "art"),
            _catalog_preference(12, "music"),
        ],
        activities=[
            _catalog_preference(21, "hiking"),
            _catalog_preference(22, "cooking"),
        ],
        languages=[_catalog_language("de", LanguageProficiency.BEGINNER)],
        availability=_availability("UTC", start_minute=540, end_minute=660),
        major="Computer   Science",
    )
    candidate = _profile(
        2,
        StudentType.INTERNATIONAL,
        interests=[
            _catalog_preference(12, "music"),
            _catalog_preference(13, "travel"),
        ],
        activities=[_catalog_preference(21, "hiking")],
        languages=[_catalog_language("de", LanguageProficiency.NATIVE)],
        availability=_availability("UTC", start_minute=600, end_minute=720),
        major="ＣＯＭＰＵＴＥＲ science",
    )

    result = _score(current, candidate)

    assert result.breakdown.interests.similarity == Fraction(1, 3)
    assert result.breakdown.activities.similarity == Fraction(1, 2)
    assert result.breakdown.availability.similarity == Fraction(1, 3)
    assert result.breakdown.languages.similarity == 1
    assert result.breakdown.major.similarity == 1
    assert result.precise_score == Fraction(275, 6)
    assert result.score == 46
    assert result.reference_week_start == REFERENCE_WEEK


def test_perfect_and_disjoint_pairs_stay_inside_zero_to_100() -> None:
    shared_interest = _catalog_preference(31, "music")
    shared_activity = _catalog_preference(41, "hiking")
    availability = _availability("UTC", start_minute=600, end_minute=720)
    current = _profile(
        3,
        StudentType.VIETNAMESE,
        interests=[shared_interest],
        activities=[shared_activity],
        languages=[_catalog_language("de")],
        availability=availability,
        major="Robotics",
    )
    perfect = _profile(
        4,
        StudentType.INTERNATIONAL,
        interests=[shared_interest],
        activities=[shared_activity],
        languages=[_catalog_language("de")],
        availability=availability,
        major="robotics",
    )
    disjoint = _profile(
        5,
        StudentType.INTERNATIONAL,
        interests=[_catalog_preference(32, "travel")],
        activities=[_catalog_preference(42, "chess")],
        languages=[_catalog_language("fr")],
        availability=None,
        major="Literature",
    )

    perfect_score = _score(current, perfect)
    disjoint_score = _score(current, disjoint)

    assert perfect_score.precise_score == 100
    assert perfect_score.score == 100
    assert disjoint_score.precise_score == 0
    assert disjoint_score.score == 0


def test_missing_optional_signals_score_zero_without_weight_renormalization() -> None:
    shared_interest = _catalog_preference(51, "music")
    current = _profile(
        6,
        StudentType.VIETNAMESE,
        interests=[shared_interest],
        languages=[_catalog_language("en")],
    )
    candidate = _profile(
        7,
        StudentType.INTERNATIONAL,
        interests=[shared_interest],
        languages=[_catalog_language("en")],
    )

    result = _score(current, candidate)

    assert result.precise_score == 45
    assert result.breakdown.activities.points == 0
    assert result.breakdown.availability.points == 0
    assert result.breakdown.major.points == 0


def test_custom_unicode_identities_and_normalized_major_are_exact_signals() -> None:
    current = _profile(
        8,
        StudentType.VIETNAMESE,
        interests=[_custom_preference("Straße")],
        activities=[_custom_preference("Ｃｈｅｓｓ")],
        languages=[_custom_language("Thai", LanguageProficiency.BEGINNER)],
        major="Data\tScience",
    )
    candidate = _profile(
        9,
        StudentType.INTERNATIONAL,
        interests=[_custom_preference("STRASSE")],
        activities=[_custom_preference("Chess")],
        languages=[_custom_language(" thai ", LanguageProficiency.NATIVE)],
        major="  DATA  SCIENCE ",
    )

    result = _score(current, candidate)

    assert result.precise_score == 85
    assert result.breakdown.interests.similarity == 1
    assert result.breakdown.activities.similarity == 1
    assert result.breakdown.languages.similarity == 1
    assert result.breakdown.major.similarity == 1


def test_catalog_and_custom_language_namespaces_do_not_globalize_custom_values() -> None:
    current = _profile(
        10,
        StudentType.VIETNAMESE,
        languages=[_catalog_language("th")],
    )
    candidate = _profile(
        11,
        StudentType.INTERNATIONAL,
        languages=[_custom_language("th")],
    )

    result = _score(current, candidate)

    assert result.breakdown.languages.similarity == 0


def test_availability_overlap_uses_iana_timezones_and_explicit_reference_week() -> None:
    berlin = _profile(
        12,
        StudentType.VIETNAMESE,
        availability=_availability("Europe/Berlin", start_minute=600, end_minute=660),
    )
    vietnam = _profile(
        13,
        StudentType.INTERNATIONAL,
        availability=_availability("Asia/Ho_Chi_Minh", start_minute=960, end_minute=1020),
    )

    winter = _score(berlin, vietnam, reference_week=date(2026, 1, 5))
    summer = _score(berlin, vietnam, reference_week=date(2026, 7, 6))

    assert winter.breakdown.availability.similarity == 1
    assert winter.breakdown.availability.points == 15
    assert summer.breakdown.availability.similarity == 0
    assert summer.breakdown.availability.points == 0


def test_score_is_symmetric_repeatable_and_profile_id_independent_for_ties() -> None:
    shared_interest = _custom_preference("Board Games")
    current = _profile(
        14,
        StudentType.VIETNAMESE,
        interests=[shared_interest],
        languages=[_catalog_language("en")],
    )
    first_candidate = _profile(
        15,
        StudentType.INTERNATIONAL,
        interests=[shared_interest],
        languages=[_catalog_language("en")],
    )
    tied_candidate = _profile(
        16,
        StudentType.INTERNATIONAL,
        interests=[shared_interest],
        languages=[_catalog_language("en")],
    )

    first = _score(current, first_candidate)
    repeated = _score(current, first_candidate)
    reversed_pair = score_eligible_pair(
        _principal(first_candidate, 202),
        _principal(current, 101),
        first_candidate,
        current,
        reference_week_start=REFERENCE_WEEK,
    )
    tie = _score(current, tied_candidate)

    assert first == repeated == reversed_pair == tie


@pytest.mark.parametrize(
    ("current_id", "candidate_id", "current_type", "candidate_type"),
    [
        (17, 17, StudentType.VIETNAMESE, StudentType.INTERNATIONAL),
        (17, 18, StudentType.VIETNAMESE, StudentType.VIETNAMESE),
        (17, 18, StudentType.INTERNATIONAL, StudentType.INTERNATIONAL),
    ],
)
def test_scorer_rejects_self_and_same_type_pairs(
    current_id: int,
    candidate_id: int,
    current_type: StudentType,
    candidate_type: StudentType,
) -> None:
    current = _profile(current_id, current_type)
    candidate = _profile(candidate_id, candidate_type)

    with pytest.raises(MatchingScoringError, match="eligible REC-001 pair"):
        _score(current, candidate)


def test_scorer_rejects_profile_principal_mismatch_and_non_monday_reference() -> None:
    current = _profile(19, StudentType.VIETNAMESE)
    candidate = _profile(20, StudentType.INTERNATIONAL)
    mismatched = EligibleMatchingPrincipal(
        user_id=UUID(int=303),
        profile_id=UUID(int=999),
        student_type=StudentType.INTERNATIONAL,
    )

    with pytest.raises(MatchingScoringError, match="eligible REC-001 pair"):
        score_eligible_pair(
            _principal(current, 101),
            mismatched,
            current,
            candidate,
            reference_week_start=REFERENCE_WEEK,
        )
    with pytest.raises(MatchingScoringError, match="Monday"):
        _score(current, candidate, reference_week=date(2026, 1, 6))


def test_oversized_major_is_bounded_and_cannot_create_a_positive_signal() -> None:
    oversized = "x" * 256
    current = _profile(21, StudentType.VIETNAMESE, major=oversized)
    candidate = _profile(22, StudentType.INTERNATIONAL, major=oversized)

    result = _score(current, candidate)

    assert result.breakdown.major.similarity == 0


def test_breakdown_exposes_no_profile_identity_or_normalized_signal_values() -> None:
    private_label = "Private Formula One Club"
    current = _profile(
        23,
        StudentType.VIETNAMESE,
        interests=[_custom_preference(private_label)],
    )
    candidate = _profile(
        24,
        StudentType.INTERNATIONAL,
        interests=[_custom_preference(private_label)],
    )

    result = _score(current, candidate)
    rendered = repr(result).lower()

    assert private_label.casefold() not in rendered
    assert str(current.id) not in rendered
    assert str(candidate.id) not in rendered
    assert "email" not in rendered
    assert "normalized_key" not in rendered
    assert tuple(signature(score_eligible_pair).parameters) == (
        "current",
        "candidate",
        "current_profile",
        "candidate_profile",
        "reference_week_start",
    )
