"""Profile completion and new-pair eligibility service tests."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from inspect import signature
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Interest, Language, StudentProfile, StudentType, User, UserRole
from app.schemas.profile_completion import (
    MatchingIneligibilityReason,
    ProfileCompletionResponse,
    ProfileCompletionStatus,
    ProfileMissingField,
)
from app.services.profile_completion import (
    derive_profile_completion,
    get_own_profile_completion,
)

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def _result(values: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _interest(identifier: int, code: str) -> Interest:
    return Interest(
        id=UUID(int=identifier),
        code=code,
        label_en=code.title(),
        label_de=f"{code.title()} DE",
        category="test",
    )


def _user(**overrides: object) -> User:
    values: dict[str, object] = {
        "id": USER_ID,
        "email": "student@example.com",
        "password_hash": "test-hash",
        "role": UserRole.USER,
        "is_active": True,
        "email_verified": False,
        "email_verified_at": datetime(2026, 9, 24, tzinfo=UTC),
    }
    values.update(overrides)
    return User(**values)


def _profile(**overrides: object) -> StudentProfile:
    values: dict[str, object] = {
        "id": PROFILE_ID,
        "user_id": USER_ID,
        "full_name": "Ready Student",
        "student_type": StudentType.INTERNATIONAL,
        "matching_opt_in": True,
        "version": 5,
    }
    values.update(overrides)
    return StudentProfile(**values)


def _derive(
    *,
    owner: User | None = None,
    profile: StudentProfile | None = None,
    ready_avatar_count: int = 1,
    valid_interest_count: int = 1,
    valid_language_count: int = 1,
) -> ProfileCompletionResponse:
    return derive_profile_completion(
        owner or _user(),
        profile or _profile(),
        ready_avatar_count=ready_avatar_count,
        valid_interest_count=valid_interest_count,
        valid_language_count=valid_language_count,
    )


@pytest.mark.parametrize(
    (
        "profile_overrides",
        "ready_avatar_count",
        "valid_interest_count",
        "valid_language_count",
        "expected_missing",
    ),
    [
        ({"full_name": None}, 1, 1, 1, ProfileMissingField.FULL_NAME),
        ({"full_name": "   "}, 1, 1, 1, ProfileMissingField.FULL_NAME),
        ({"student_type": None}, 1, 1, 1, ProfileMissingField.STUDENT_TYPE),
        ({}, 0, 1, 1, ProfileMissingField.AVATAR),
        ({}, 1, 0, 1, ProfileMissingField.INTERESTS),
        ({}, 1, 1, 0, ProfileMissingField.LANGUAGES),
    ],
)
def test_each_required_group_removal_prevents_complete(
    profile_overrides: dict[str, object],
    ready_avatar_count: int,
    valid_interest_count: int,
    valid_language_count: int,
    expected_missing: ProfileMissingField,
) -> None:
    completion = _derive(
        profile=_profile(**profile_overrides),
        ready_avatar_count=ready_avatar_count,
        valid_interest_count=valid_interest_count,
        valid_language_count=valid_language_count,
    )

    assert completion.status is ProfileCompletionStatus.INCOMPLETE
    assert completion.percentage == 80
    assert completion.missing_fields == [expected_missing]
    assert completion.matching_eligible is False
    assert completion.reasons == [MatchingIneligibilityReason.PROFILE_INCOMPLETE]


def test_all_required_groups_produce_complete_and_eligible_profile() -> None:
    completion = _derive()

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert completion.percentage == 100
    assert completion.missing_fields == []
    assert completion.matching_eligible is True
    assert completion.reasons == []


def test_existing_buddy_relationships_are_not_a_completion_reservation_gate() -> None:
    completion = _derive()

    assert "active_reservation_count" not in signature(derive_profile_completion).parameters
    assert "ACTIVE_MATCH_RESERVATION" not in MatchingIneligibilityReason.__members__
    assert completion.matching_eligible is True


def test_unverified_current_email_adds_reason_and_blocks_matching() -> None:
    completion = _derive(owner=_user(email_verified=True, email_verified_at=None))

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert completion.matching_eligible is False
    assert completion.reasons == [MatchingIneligibilityReason.EMAIL_VERIFICATION_REQUIRED]


@pytest.mark.parametrize(
    ("ready_avatar_count", "valid_interest_count", "valid_language_count"),
    [
        (2, 1, 1),
        (1, 21, 1),
        (1, 1, 11),
    ],
)
def test_invalid_required_group_counts_prevent_complete(
    ready_avatar_count: int,
    valid_interest_count: int,
    valid_language_count: int,
) -> None:
    completion = _derive(
        ready_avatar_count=ready_avatar_count,
        valid_interest_count=valid_interest_count,
        valid_language_count=valid_language_count,
    )

    assert completion.status is ProfileCompletionStatus.INCOMPLETE
    assert completion.matching_eligible is False


@pytest.mark.parametrize(
    ("owner", "profile", "expected_reason"),
    [
        (
            _user(is_active=False),
            _profile(),
            MatchingIneligibilityReason.ACCOUNT_INACTIVE,
        ),
        (
            _user(deleted_at=datetime(2026, 9, 20, tzinfo=UTC)),
            _profile(),
            MatchingIneligibilityReason.ACCOUNT_DELETED,
        ),
        (
            _user(),
            _profile(matching_opt_in=False),
            MatchingIneligibilityReason.MATCHING_OPT_IN_REQUIRED,
        ),
    ],
)
def test_complete_profile_can_still_be_ineligible_for_new_pairing(
    owner: User,
    profile: StudentProfile,
    expected_reason: MatchingIneligibilityReason,
) -> None:
    completion = _derive(owner=owner, profile=profile)

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert completion.percentage == 100
    assert completion.matching_eligible is False
    assert completion.reasons == [expected_reason]


@pytest.mark.anyio
async def test_service_filters_invalid_relations_and_records_first_completion_milestone() -> None:
    profile = _profile(onboarding_completed_at=None)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[profile, 1])
    mock.scalars = AsyncMock(
        side_effect=[
            _result([_interest(1, "music"), _interest(2, "travel")]),
            _result([]),
            _result([Language(code="en", label_en="English", label_de="Englisch")]),
            _result([]),
        ]
    )
    mock.flush = AsyncMock()
    session = cast(AsyncSession, mock)
    completion = await get_own_profile_completion(session, _user())

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert profile.onboarding_completed_at is not None
    mock.flush.assert_awaited_once_with()
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    avatar_sql = str(mock.scalar.await_args_list[1].args[0].compile(dialect=dialect)).lower()
    interest_sql = str(mock.scalars.await_args_list[0].args[0].compile(dialect=dialect)).lower()
    language_sql = str(mock.scalars.await_args_list[2].args[0].compile(dialect=dialect)).lower()
    assert "profile_photos.is_avatar is true" in avatar_sql
    assert "profile_photos.processing_status" in avatar_sql
    assert "profile_photos.deleted_at is null" in avatar_sql
    assert "join app_private.interests" in interest_sql
    assert "interests.is_active is true" in interest_sql
    assert "interests.deleted_at is null" in interest_sql
    assert "join app_private.languages" in language_sql
    assert "languages.is_active is true" in language_sql


@pytest.mark.anyio
async def test_draft_to_complete_transition_preserves_historical_milestone_after_removal() -> None:
    profile = _profile(onboarding_completed_at=None)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[profile, 1])
    mock.scalars = AsyncMock(
        side_effect=[
            _result([_interest(1, "music")]),
            _result([]),
            _result([Language(code="en", label_en="English", label_de="Englisch")]),
            _result([]),
        ]
    )
    mock.flush = AsyncMock()
    session = cast(AsyncSession, mock)
    completed = await get_own_profile_completion(session, _user())
    milestone = profile.onboarding_completed_at
    profile.full_name = None
    incomplete = _derive(profile=profile)

    assert completed.status is ProfileCompletionStatus.COMPLETE
    assert milestone is not None
    assert incomplete.status is ProfileCompletionStatus.INCOMPLETE
    assert profile.onboarding_completed_at == milestone


@pytest.mark.anyio
async def test_existing_completion_milestone_is_not_rewritten() -> None:
    milestone = datetime(2026, 9, 19, tzinfo=UTC)
    profile = _profile(onboarding_completed_at=milestone)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[profile, 1])
    mock.scalars = AsyncMock(
        side_effect=[
            _result([_interest(1, "music")]),
            _result([]),
            _result([Language(code="en", label_en="English", label_de="Englisch")]),
            _result([]),
        ]
    )
    mock.flush = AsyncMock()
    session = cast(AsyncSession, mock)

    completion = await get_own_profile_completion(session, _user())

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert profile.onboarding_completed_at == milestone
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_completion_counts_custom_signals_without_duplicate_or_activity_gate() -> None:
    profile = _profile(onboarding_completed_at=None)
    interests = [_interest(index, f"interest-{index}") for index in range(1, 21)]
    languages = [
        Language(
            code=f"qaa-{index:02d}",
            label_en=f"Language {index}",
            label_de=f"Sprache {index}",
        )
        for index in range(1, 11)
    ]
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[profile, 1])
    mock.scalars = AsyncMock(
        side_effect=[
            _result(interests),
            _result(["interest-1"]),
            _result(languages),
            _result(["language 1"]),
        ]
    )
    mock.flush = AsyncMock()
    session = cast(AsyncSession, mock)
    completion = await get_own_profile_completion(session, _user())

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert completion.percentage == 100
    assert mock.scalars.await_count == 4
    rendered = "\n".join(str(call.args[0]).lower() for call in mock.scalars.await_args_list)
    assert "profile_activities" not in rendered


@pytest.mark.anyio
async def test_custom_only_interest_and_language_satisfy_existing_completion_groups() -> None:
    profile = _profile(onboarding_completed_at=None)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[profile, 1])
    mock.scalars = AsyncMock(
        side_effect=[
            _result([]),
            _result(["formula 1"]),
            _result([]),
            _result(["swiss german"]),
        ]
    )
    mock.flush = AsyncMock()
    session = cast(AsyncSession, mock)
    completion = await get_own_profile_completion(session, _user())

    assert completion.status is ProfileCompletionStatus.COMPLETE
    assert completion.missing_fields == []
    assert completion.percentage == 100
