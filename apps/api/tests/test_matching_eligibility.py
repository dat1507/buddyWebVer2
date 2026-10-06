"""REC-001 current-user gates, candidate policy, and batch projection tests."""

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

from app.models import (
    Activity,
    Interest,
    Language,
    LanguageProficiency,
    PreferenceKind,
    ProfileCustomPreference,
    ProfilePhoto,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.schemas.profile_completion import (
    MatchingIneligibilityReason,
    ProfileCompletionResponse,
    ProfileCompletionStatus,
    ProfileMissingField,
)
from app.services import matching_eligibility as matching_service
from app.services.buddy_access import BuddyCapabilityError, VerifiedBuddyPrincipal
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    eligible_candidate_statement,
    get_eligible_candidate_avatar,
    get_eligible_matching_principal,
    list_eligible_matching_profiles,
    load_matching_scoring_profiles,
    matching_pair_is_eligible,
)

CURRENT_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
CURRENT_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
SEMESTER_ID = UUID("10000000-0000-4000-8000-000000000003")
CANDIDATE_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000001")
CUSTOM_PROFILE_ID = UUID("30000000-0000-4000-8000-000000000001")
INTEREST_ID = UUID("40000000-0000-4000-8000-000000000001")
ACTIVITY_ID = UUID("50000000-0000-4000-8000-000000000001")
PHOTO_ID = UUID("60000000-0000-4000-8000-000000000001")
CUSTOM_PHOTO_ID = UUID("70000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 9, 27, tzinfo=UTC)


def _user(**overrides: object) -> User:
    values: dict[str, object] = {
        "id": CURRENT_USER_ID,
        "email": "student@example.com",
        "password_hash": "not-projected",
        "role": UserRole.USER,
        "is_active": True,
        "email_verified": True,
        "email_verified_at": NOW,
        "semester_id": SEMESTER_ID,
    }
    values.update(overrides)
    return User(**values)


def _profile(**overrides: object) -> StudentProfile:
    values: dict[str, object] = {
        "id": CURRENT_PROFILE_ID,
        "user_id": CURRENT_USER_ID,
        "full_name": "Current Student",
        "display_name": "Current",
        "student_type": StudentType.VIETNAMESE,
        "matching_opt_in": True,
        "version": 1,
    }
    values.update(overrides)
    return StudentProfile(**values)


def _completion(
    *,
    eligible: bool,
    reason: MatchingIneligibilityReason | None = None,
) -> ProfileCompletionResponse:
    return ProfileCompletionResponse(
        status=(
            ProfileCompletionStatus.COMPLETE if eligible else ProfileCompletionStatus.INCOMPLETE
        ),
        percentage=100 if eligible else 80,
        missing_fields=[] if eligible else [ProfileMissingField.INTERESTS],
        matching_eligible=eligible,
        reasons=[] if reason is None else [reason],
    )


def _principal(
    *,
    user_id: UUID = CURRENT_USER_ID,
    profile_id: UUID = CURRENT_PROFILE_ID,
    student_type: StudentType = StudentType.VIETNAMESE,
    semester_id: UUID | None = SEMESTER_ID,
) -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=user_id,
        profile_id=profile_id,
        student_type=student_type,
        semester_id=semester_id,
    )


def _candidate_profile(
    *,
    profile_id: UUID,
    display_name: str,
    availability: dict[str, object] | None = None,
) -> StudentProfile:
    return StudentProfile(
        id=profile_id,
        user_id=UUID(int=profile_id.int + 100),
        full_name=f"{display_name} Legal Name",
        display_name=display_name,
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        availability=availability,
        matching_opt_in=True,
        version=2,
    )


def _avatar(profile_id: UUID, photo_id: UUID) -> ProfilePhoto:
    return ProfilePhoto(
        id=photo_id,
        profile_id=profile_id,
        bucket="profile-images",
        object_key=f"{photo_id}.webp",
        mime_type="image/webp",
        byte_size=1024,
        width=640,
        height=480,
        is_avatar=True,
    )


def _tuple_result(rows: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.tuples.return_value.all.return_value = rows
    return result


def _scalar_result(rows: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


@pytest.mark.anyio
async def test_verified_complete_opted_in_user_passes_current_eligibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    profile = _profile()
    reader = AsyncMock(return_value=_completion(eligible=True))
    monkeypatch.setattr(matching_service, "get_profile_completion", reader)

    result = await get_eligible_matching_principal(
        cast(AsyncSession, MagicMock(spec=AsyncSession)),
        VerifiedBuddyPrincipal(user=user, profile=profile),
    )

    assert result == _principal()
    reader.assert_awaited_once()
    assert "student@example.com" not in repr(result)


@pytest.mark.anyio
async def test_incomplete_current_profile_is_denied_with_stable_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = AsyncMock(
        return_value=_completion(
            eligible=False,
            reason=MatchingIneligibilityReason.PROFILE_INCOMPLETE,
        )
    )
    monkeypatch.setattr(matching_service, "get_profile_completion", reader)

    with pytest.raises(BuddyCapabilityError) as denied:
        await get_eligible_matching_principal(
            cast(AsyncSession, MagicMock(spec=AsyncSession)),
            VerifiedBuddyPrincipal(user=_user(), profile=_profile()),
        )

    assert denied.value.reason is MatchingIneligibilityReason.PROFILE_INCOMPLETE


@pytest.mark.anyio
async def test_current_user_without_semester_fails_closed_before_completion_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = AsyncMock(return_value=_completion(eligible=True))
    monkeypatch.setattr(matching_service, "get_profile_completion", reader)

    with pytest.raises(BuddyCapabilityError):
        await get_eligible_matching_principal(
            cast(AsyncSession, MagicMock(spec=AsyncSession)),
            VerifiedBuddyPrincipal(user=_user(semester_id=None), profile=_profile()),
        )

    reader.assert_not_awaited()


def test_pair_policy_excludes_self_and_same_type_but_not_unmodeled_relationship_state() -> None:
    current = _principal()
    opposite = _principal(
        user_id=UUID(int=CURRENT_USER_ID.int + 10),
        profile_id=CANDIDATE_PROFILE_ID,
        student_type=StudentType.INTERNATIONAL,
    )
    same_type = _principal(
        user_id=UUID(int=CURRENT_USER_ID.int + 11),
        profile_id=UUID(int=CANDIDATE_PROFILE_ID.int + 1),
        student_type=StudentType.VIETNAMESE,
    )

    assert matching_pair_is_eligible(current, opposite) is True
    assert matching_pair_is_eligible(current, current) is False
    assert matching_pair_is_eligible(current, same_type) is False
    assert tuple(signature(matching_pair_is_eligible).parameters) == ("current", "candidate")


def test_candidate_query_is_bounded_deterministic_and_enforces_all_rec_001_gates() -> None:
    statement = eligible_candidate_statement(_principal(), limit=25)
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    sql = str(compiled).lower()

    assert "users.role =" in sql
    assert "users.semester_id =" in sql
    assert "users.is_active is true" in sql
    assert "users.deleted_at is null" in sql
    assert "users.email_verified_at is not null" in sql
    assert "student_profiles.deleted_at is null" in sql
    assert "student_profiles.user_id !=" in sql
    assert "student_profiles.id !=" in sql
    assert "student_profiles.student_type !=" in sql
    assert "student_profiles.matching_opt_in is true" in sql
    assert "profile_photos.processing_status" in sql
    assert "interests.is_active is true" in sql
    assert "languages.is_active is true" in sql
    assert "profile_custom_preferences.deleted_at is null" in sql
    assert "order by app_private.student_profiles.id" in sql
    assert "limit" in sql
    assert CURRENT_USER_ID in compiled.params.values()
    assert CURRENT_PROFILE_ID in compiled.params.values()
    assert SEMESTER_ID in compiled.params.values()
    assert "app_private.users.email," not in sql
    assert "users.password_hash" not in sql
    assert "matches" not in sql
    assert "invitations" not in sql


def test_candidate_query_rejects_an_unbounded_or_empty_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        eligible_candidate_statement(_principal(), limit=0)


def test_candidate_query_fails_closed_when_current_semester_is_missing() -> None:
    statement = eligible_candidate_statement(_principal(semester_id=None), limit=25)
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    sql = str(compiled).lower()

    assert "users.role =" in sql
    assert "users.semester_id is null" in sql


@pytest.mark.anyio
async def test_candidate_projection_batches_catalog_and_custom_preferences_without_n_plus_one() -> (
    None
):
    catalog_profile = _candidate_profile(
        profile_id=CANDIDATE_PROFILE_ID,
        display_name="Alex",
        availability={
            "timezone": "Europe/Berlin",
            "slots": [{"weekday": 2, "start_minute": 1080, "end_minute": 1200}],
        },
    )
    custom_profile = _candidate_profile(
        profile_id=CUSTOM_PROFILE_ID,
        display_name="Sam",
    )
    catalog_avatar = _avatar(CANDIDATE_PROFILE_ID, PHOTO_ID)
    custom_avatar = _avatar(CUSTOM_PROFILE_ID, CUSTOM_PHOTO_ID)
    interest = Interest(
        id=INTEREST_ID,
        code="music",
        label_en="Music",
        label_de="Musik",
        category="culture",
    )
    language = Language(code="de", label_en="German", label_de="Deutsch")
    activity = Activity(
        id=ACTIVITY_ID,
        code="hiking",
        label_en="Hiking",
        label_de="Wandern",
    )
    custom_values = [
        ProfileCustomPreference(
            profile_id=CUSTOM_PROFILE_ID,
            kind=PreferenceKind.INTEREST,
            display_label="Formula 1",
            normalized_key="formula 1",
        ),
        ProfileCustomPreference(
            profile_id=CUSTOM_PROFILE_ID,
            kind=PreferenceKind.LANGUAGE,
            display_label="Thai",
            normalized_key="thai",
            proficiency=LanguageProficiency.INTERMEDIATE,
        ),
        ProfileCustomPreference(
            profile_id=CANDIDATE_PROFILE_ID,
            kind=PreferenceKind.ACTIVITY,
            display_label="Board Games",
            normalized_key="board games",
        ),
    ]
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock(
        side_effect=[
            _tuple_result(
                [
                    (catalog_profile, catalog_avatar),
                    (custom_profile, custom_avatar),
                ]
            ),
            _tuple_result([(CANDIDATE_PROFILE_ID, interest)]),
            _tuple_result([(CANDIDATE_PROFILE_ID, language, LanguageProficiency.FLUENT)]),
            _tuple_result([(CANDIDATE_PROFILE_ID, activity)]),
            _scalar_result(custom_values),
        ]
    )
    session = cast(AsyncSession, mock)

    result = await list_eligible_matching_profiles(
        session,
        _principal(),
        locale="de",
        limit=25,
    )

    assert mock.execute.await_count == 5
    assert [candidate.id for candidate in result] == [
        CANDIDATE_PROFILE_ID,
        CUSTOM_PROFILE_ID,
    ]
    assert [value.label for value in result[0].interests] == ["Musik"]
    assert [value.label for value in result[0].languages] == ["Deutsch"]
    assert [value.label for value in result[0].activities] == ["Wandern", "Board Games"]
    assert [value.label for value in result[1].interests] == ["Formula 1"]
    assert result[1].languages[0].proficiency is LanguageProficiency.INTERMEDIATE
    assert result[0].availability is not None
    assert result[0].availability.timezone == "Europe/Berlin"
    assert result[1].availability is None
    rendered = repr([candidate.model_dump() for candidate in result]).lower()
    assert "normalized_key" not in rendered
    assert "email" not in rendered
    assert "password" not in rendered


@pytest.mark.anyio
async def test_empty_candidate_batch_does_not_issue_preference_queries() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock(return_value=_tuple_result([]))

    result = await list_eligible_matching_profiles(
        cast(AsyncSession, mock),
        _principal(),
        locale="en",
        limit=25,
    )

    assert result == ()
    mock.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_scoring_context_projects_current_and_candidates_in_fixed_query_count() -> None:
    current_profile = _profile()
    candidate_profile = _candidate_profile(
        profile_id=CANDIDATE_PROFILE_ID,
        display_name="Alex",
    )
    current_avatar = _avatar(CURRENT_PROFILE_ID, UUID(int=PHOTO_ID.int + 1))
    candidate_avatar = _avatar(CANDIDATE_PROFILE_ID, PHOTO_ID)
    interest = Interest(
        id=INTEREST_ID,
        code="music",
        label_en="Music",
        label_de="Musik",
        category="culture",
    )
    language = Language(code="en", label_en="English", label_de="Englisch")
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock(
        side_effect=[
            _tuple_result([(current_profile, current_avatar)]),
            _tuple_result([(candidate_profile, candidate_avatar)]),
            _tuple_result(
                [
                    (CURRENT_PROFILE_ID, interest),
                    (CANDIDATE_PROFILE_ID, interest),
                ]
            ),
            _tuple_result(
                [
                    (CURRENT_PROFILE_ID, language, LanguageProficiency.NATIVE),
                    (CANDIDATE_PROFILE_ID, language, LanguageProficiency.FLUENT),
                ]
            ),
            _tuple_result([]),
            _scalar_result([]),
        ]
    )

    current, candidates = await load_matching_scoring_profiles(
        cast(AsyncSession, mock),
        _principal(),
        locale="en",
        candidate_limit=501,
    )

    assert mock.execute.await_count == 6
    assert current is not None
    assert current.id == CURRENT_PROFILE_ID
    assert len(candidates) == 1
    assert candidates[0].profile.id == CANDIDATE_PROFILE_ID
    assert candidates[0].principal.user_id == candidate_profile.user_id
    assert candidates[0].principal.student_type is StudentType.INTERNATIONAL
    assert candidates[0].principal.semester_id == SEMESTER_ID
    assert str(candidate_profile.user_id) not in repr(candidates[0])


@pytest.mark.anyio
async def test_candidate_avatar_lookup_reuses_the_exact_eligibility_predicates() -> None:
    photo = _avatar(CANDIDATE_PROFILE_ID, PHOTO_ID)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=photo)

    result = await get_eligible_candidate_avatar(
        cast(AsyncSession, mock),
        _principal(),
        PHOTO_ID,
    )

    assert result is photo
    statement = mock.scalar.await_args.args[0]
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    sql = str(compiled).lower()
    assert PHOTO_ID in compiled.params.values()
    assert "users.email_verified_at is not null" in sql
    assert "student_profiles.matching_opt_in is true" in sql
    assert "student_profiles.student_type !=" in sql
    assert "profile_photos.is_avatar is true" in sql
