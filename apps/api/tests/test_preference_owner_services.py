"""PREF-003 atomic owner preference service acceptance tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Activity,
    Interest,
    Language,
    LanguageProficiency,
    PreferenceKind,
    ProfileActivity,
    ProfileCustomPreference,
    ProfileInterest,
    ProfileLanguage,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas.profile_catalog import ProfilePreferenceUpdate
from app.services.profile_catalogs import (
    get_own_preference_snapshot,
    replace_own_preferences,
)
from app.services.profiles import ProfileValidationError, ProfileVersionConflictError

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
INTEREST_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
ACTIVITY_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")


def _owner() -> User:
    return User(
        id=USER_ID,
        email="owner@example.test",
        password_hash="test-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
    )


def _profile(*, version: int = 3) -> StudentProfile:
    return StudentProfile(
        id=PROFILE_ID,
        user_id=USER_ID,
        full_name="Preference Owner",
        version=version,
    )


def _interest() -> Interest:
    return Interest(
        id=INTEREST_ID,
        code="photography",
        label_en="Photography",
        label_de="Fotografie",
        category="creative",
    )


def _language() -> Language:
    return Language(code="de", label_en="German", label_de="Deutsch")


def _activity() -> Activity:
    return Activity(
        id=ACTIVITY_ID,
        code="hiking",
        label_en="Hiking",
        label_de="Wandern",
    )


def _result(values: Sequence[object]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = values
    return result


def _session(profile: StudentProfile) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=profile)
    mock.scalars = AsyncMock()
    mock.execute = AsyncMock()
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _update(**overrides: object) -> ProfilePreferenceUpdate:
    values: dict[str, object] = {
        "version": 3,
        "interest_ids": [str(INTEREST_ID)],
        "custom_interests": [{"label": "  German  "}],
        "languages": [{"language_code": "de", "proficiency": "fluent"}],
        "custom_languages": [
            {"label": "Swiss   German", "proficiency": "intermediate"}
        ],
        "activity_ids": [str(ACTIVITY_ID)],
        "custom_activities": [{"label": "Night\tKayaking"}],
    }
    values.update(overrides)
    return ProfilePreferenceUpdate.model_validate(values)


@pytest.mark.anyio
async def test_combined_replacement_persists_all_groups_once_and_keeps_kind_namespaces() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.side_effect = [
        _result([_interest()]),
        _result([_language()]),
        _result([_activity()]),
        _result([]),
        _result([]),
        _result([]),
        _result([]),
    ]

    result = await replace_own_preferences(session, _owner(), _update())

    assert result.version == 4
    assert result.interest_ids == (INTEREST_ID,)
    assert [item.label for item in result.custom_interests] == ["German"]
    assert result.languages[0].proficiency is LanguageProficiency.FLUENT
    assert result.custom_languages[0].label == "Swiss German"
    assert result.custom_languages[0].proficiency is LanguageProficiency.INTERMEDIATE
    assert result.activity_ids == (ACTIVITY_ID,)
    assert result.custom_activities[0].label == "Night Kayaking"
    assert profile.version == 4
    assert "FOR UPDATE" in str(mock.scalar.await_args.args[0]).upper()
    assert mock.execute.await_count == 4
    mock.flush.assert_awaited_once_with()

    attached = [item for call in mock.add_all.call_args_list for item in call.args[0]]
    assert any(isinstance(item, ProfileInterest) for item in attached)
    assert any(isinstance(item, ProfileLanguage) for item in attached)
    assert any(isinstance(item, ProfileActivity) for item in attached)
    customs = [item for item in attached if isinstance(item, ProfileCustomPreference)]
    assert [(item.kind, item.normalized_key, item.proficiency) for item in customs] == [
        (PreferenceKind.INTEREST, "german", None),
        (
            PreferenceKind.LANGUAGE,
            "swiss german",
            LanguageProficiency.INTERMEDIATE,
        ),
        (PreferenceKind.ACTIVITY, "night kayaking", None),
    ]
    assert not any(isinstance(item, (Interest, Language, Activity)) for item in attached)


@pytest.mark.anyio
@pytest.mark.parametrize("label", [" photography ", "FOTOGRAFIE"])
async def test_custom_interest_matching_active_catalog_en_or_de_is_rejected(label: str) -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.return_value = _result([_interest()])

    with pytest.raises(ProfileValidationError, match="duplicates"):
        await replace_own_preferences(
            session,
            _owner(),
            _update(
                interest_ids=[],
                custom_interests=[{"label": label}],
            ),
        )

    assert profile.version == 3
    mock.execute.assert_not_awaited()
    mock.add_all.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_equivalent_custom_values_are_rejected_before_any_write() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.return_value = _result([_interest()])

    with pytest.raises(ProfileValidationError, match="duplicates"):
        await replace_own_preferences(
            session,
            _owner(),
            _update(
                interest_ids=[],
                custom_interests=[
                    {"label": "Formula 1"},
                    {"label": "  FORMULA   1  "},
                ],
            ),
        )

    mock.execute.assert_not_awaited()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_invalid_language_makes_combined_update_atomic() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.side_effect = [_result([_interest()]), _result([_language()])]

    with pytest.raises(ProfileValidationError, match="languages"):
        await replace_own_preferences(
            session,
            _owner(),
            _update(
                languages=[{"language_code": "en", "proficiency": "native"}],
            ),
        )

    assert profile.version == 3
    assert mock.scalars.await_count == 2
    mock.execute.assert_not_awaited()
    mock.add_all.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_interest_identifier_is_not_accepted_in_activity_namespace() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.side_effect = [
        _result([_interest()]),
        _result([_language()]),
        _result([_activity()]),
    ]

    with pytest.raises(ProfileValidationError, match="activities"):
        await replace_own_preferences(
            session,
            _owner(),
            _update(activity_ids=[str(INTEREST_ID)]),
        )

    assert profile.version == 3
    mock.execute.assert_not_awaited()
    mock.add_all.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_stale_combined_update_stops_before_catalog_reads() -> None:
    profile = _profile(version=8)
    mock, session = _session(profile)

    with pytest.raises(ProfileVersionConflictError, match="stale"):
        await replace_own_preferences(
            session,
            _owner(),
            _update(version=7),
        )

    mock.scalars.assert_not_awaited()
    mock.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_persisted_projection_round_trips_labels_kinds_and_language_proficiency() -> None:
    profile = _profile(version=4)
    custom_rows = [
        ProfileCustomPreference(
            profile_id=PROFILE_ID,
            kind=PreferenceKind.INTEREST,
            display_label="German",
            normalized_key="german",
        ),
        ProfileCustomPreference(
            profile_id=PROFILE_ID,
            kind=PreferenceKind.LANGUAGE,
            display_label="Swiss German",
            normalized_key="swiss german",
            proficiency=LanguageProficiency.INTERMEDIATE,
        ),
        ProfileCustomPreference(
            profile_id=PROFILE_ID,
            kind=PreferenceKind.ACTIVITY,
            display_label="Night Kayaking",
            normalized_key="night kayaking",
        ),
    ]
    language = ProfileLanguage(
        profile_id=PROFILE_ID,
        language_code="de",
        proficiency=LanguageProficiency.FLUENT,
    )
    mock, session = _session(profile)
    mock.scalars.side_effect = [
        _result(custom_rows),
        _result([INTEREST_ID]),
        _result([language]),
        _result([ACTIVITY_ID]),
    ]

    result = await get_own_preference_snapshot(session, _owner())

    assert result.version == 4
    assert result.interest_ids == (INTEREST_ID,)
    assert result.custom_interests[0].label == "German"
    assert result.languages[0].proficiency is LanguageProficiency.FLUENT
    assert result.custom_languages[0].proficiency is LanguageProficiency.INTERMEDIATE
    assert result.activity_ids == (ACTIVITY_ID,)
    assert result.custom_activities[0].label == "Night Kayaking"
