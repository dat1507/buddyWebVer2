"""REC-003 ranking, pagination, bounds, and privacy tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LanguageProficiency, StudentType
from app.schemas.matching import (
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.services import matching_recommendations as recommendation_service
from app.services.matching_eligibility import (
    EligibleMatchingCandidate,
    EligibleMatchingPrincipal,
)
from app.services.matching_recommendations import (
    MAX_RECOMMENDATION_CANDIDATES,
    MatchingRecommendationCapacityError,
    MatchingRecommendationStateError,
    current_reference_week_start,
    list_ranked_matching_recommendations,
)

REFERENCE_WEEK = date(2026, 9, 21)


def _catalog_preference(identifier: int, code: str) -> SafeMatchingPreference:
    return SafeMatchingPreference(
        id=UUID(int=identifier),
        code=code,
        label=code.title(),
        is_custom=False,
    )


def _custom_preference(label: str) -> SafeMatchingPreference:
    return SafeMatchingPreference(id=None, code=None, label=label, is_custom=True)


def _language(code: str) -> SafeMatchingLanguage:
    return SafeMatchingLanguage(
        code=code,
        label=code.upper(),
        proficiency=LanguageProficiency.INTERMEDIATE,
        is_custom=False,
    )


def _profile(
    identifier: int,
    student_type: StudentType,
    *,
    interests: list[SafeMatchingPreference] | None = None,
    activities: list[SafeMatchingPreference] | None = None,
    languages: list[SafeMatchingLanguage] | None = None,
    major: str | None = None,
) -> SafeMatchingProfile:
    return SafeMatchingProfile(
        id=UUID(int=identifier),
        display_name=f"Buddy {identifier}",
        student_type=student_type,
        major=major,
        avatar=SafeMatchingAvatar(id=UUID(int=10_000 + identifier), width=640, height=480),
        interests=interests or [_catalog_preference(20_000 + identifier, "fallback")],
        languages=languages or [_language(f"q{identifier}")],
        activities=activities or [],
        availability=None,
    )


def _principal(profile: SafeMatchingProfile, user_identifier: int) -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=UUID(int=user_identifier),
        profile_id=profile.id,
        student_type=profile.student_type,
    )


def _candidate(profile: SafeMatchingProfile, user_identifier: int) -> EligibleMatchingCandidate:
    return EligibleMatchingCandidate(
        principal=_principal(profile, user_identifier),
        profile=profile,
    )


@pytest.mark.anyio
async def test_ranking_uses_exact_score_then_stable_profile_id_and_paginates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_catalog = _catalog_preference(100, "music")
    current = _profile(
        1,
        StudentType.VIETNAMESE,
        interests=[shared_catalog, _custom_preference("Formula 1")],
        activities=[_custom_preference("Board Games")],
        languages=[_language("en")],
        major="Computer Science",
    )
    best = _profile(
        20,
        StudentType.INTERNATIONAL,
        interests=[shared_catalog, _custom_preference(" formula   1 ")],
        activities=[_custom_preference("board games")],
        languages=[_language("en")],
        major="computer science",
    )
    tied_later = _profile(
        40,
        StudentType.INTERNATIONAL,
        interests=[shared_catalog],
        languages=[_language("en")],
    )
    tied_earlier = _profile(
        30,
        StudentType.INTERNATIONAL,
        interests=[shared_catalog],
        languages=[_language("en")],
    )
    loader = AsyncMock(
        return_value=(
            current,
            (
                _candidate(tied_later, 140),
                _candidate(best, 120),
                _candidate(tied_earlier, 130),
            ),
        )
    )
    monkeypatch.setattr(recommendation_service, "load_matching_scoring_profiles", loader)
    mock = MagicMock(spec=AsyncSession)

    result = await list_ranked_matching_recommendations(
        cast(AsyncSession, mock),
        _principal(current, 101),
        locale="en",
        page=1,
        page_size=2,
        reference_week_start=REFERENCE_WEEK,
    )

    assert [item.profile.id for item in result.items] == [best.id, tied_earlier.id]
    assert [item.score for item in result.items] == [85, 25]
    assert result.total == 3
    assert result.total_pages == 2
    assert result.reference_week_start == REFERENCE_WEEK
    assert result.items[0].explanation.interests.weight == 40
    assert result.items[0].explanation.activities.weight == 35
    assert result.items[0].explanation.availability.weight == 15
    assert result.items[0].explanation.languages.weight == 5
    assert result.items[0].explanation.major.weight == 5
    assert result.items[0].explanation.interests.points == 40
    assert result.items[0].explanation.activities.points == 35
    assert result.items[0].explanation.availability.points == 0
    assert result.items[0].explanation.languages.points == 5
    assert result.items[0].explanation.major.points == 5
    assert result.items[1].explanation.interests.points == 20
    assert result.items[1].explanation.activities.points == 0
    loader.assert_awaited_once_with(
        cast(AsyncSession, mock),
        _principal(current, 101),
        locale="en",
        candidate_limit=MAX_RECOMMENDATION_CANDIDATES + 1,
    )
    mock.commit.assert_not_called()
    rendered = result.model_dump_json().lower()
    for forbidden in (
        "email",
        "password",
        "normalized_key",
        "object_key",
        "bucket",
        str(UUID(int=120)),
    ):
        assert forbidden not in rendered


@pytest.mark.anyio
async def test_empty_and_out_of_range_pages_are_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _profile(2, StudentType.VIETNAMESE)
    monkeypatch.setattr(
        recommendation_service,
        "load_matching_scoring_profiles",
        AsyncMock(return_value=(current, ())),
    )

    result = await list_ranked_matching_recommendations(
        cast(AsyncSession, MagicMock(spec=AsyncSession)),
        _principal(current, 102),
        locale="de",
        page=9,
        page_size=50,
        reference_week_start=REFERENCE_WEEK,
    )

    assert result.items == []
    assert result.total == 0
    assert result.total_pages == 0
    assert result.page == 9


@pytest.mark.anyio
async def test_candidate_capacity_fails_closed_instead_of_truncating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _profile(3, StudentType.VIETNAMESE)
    candidates = tuple(
        _candidate(_profile(1_000 + index, StudentType.INTERNATIONAL), 5_000 + index)
        for index in range(MAX_RECOMMENDATION_CANDIDATES + 1)
    )
    monkeypatch.setattr(
        recommendation_service,
        "load_matching_scoring_profiles",
        AsyncMock(return_value=(current, candidates)),
    )

    with pytest.raises(MatchingRecommendationCapacityError):
        await list_ranked_matching_recommendations(
            cast(AsyncSession, MagicMock(spec=AsyncSession)),
            _principal(current, 103),
            locale="en",
            page=1,
            page_size=20,
            reference_week_start=REFERENCE_WEEK,
        )


@pytest.mark.anyio
async def test_changed_current_profile_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    current = _profile(4, StudentType.VIETNAMESE)
    monkeypatch.setattr(
        recommendation_service,
        "load_matching_scoring_profiles",
        AsyncMock(return_value=(None, ())),
    )

    with pytest.raises(MatchingRecommendationStateError):
        await list_ranked_matching_recommendations(
            cast(AsyncSession, MagicMock(spec=AsyncSession)),
            _principal(current, 104),
            locale="en",
            page=1,
            page_size=20,
            reference_week_start=REFERENCE_WEEK,
        )


@pytest.mark.parametrize(
    ("page", "page_size", "week", "message"),
    [
        (0, 20, REFERENCE_WEEK, "page"),
        (1, 0, REFERENCE_WEEK, "page size"),
        (1, 51, REFERENCE_WEEK, "page size"),
        (1, 20, date(2026, 9, 22), "Monday"),
    ],
)
@pytest.mark.anyio
async def test_service_rejects_invalid_bounds_before_query(
    page: int,
    page_size: int,
    week: date,
    message: str,
) -> None:
    current = _profile(5, StudentType.VIETNAMESE)
    mock = MagicMock(spec=AsyncSession)

    with pytest.raises(ValueError, match=message):
        await list_ranked_matching_recommendations(
            cast(AsyncSession, mock),
            _principal(current, 105),
            locale="en",
            page=page,
            page_size=page_size,
            reference_week_start=week,
        )

    mock.execute.assert_not_called()


def test_reference_week_is_current_utc_monday() -> None:
    assert current_reference_week_start(datetime(2026, 9, 27, 23, 59, tzinfo=UTC)) == date(
        2026, 9, 21
    )
    assert current_reference_week_start(datetime(2026, 9, 28, 0, 0, tzinfo=UTC)) == date(
        2026, 9, 28
    )
