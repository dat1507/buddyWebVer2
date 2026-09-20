"""Catalog query, ownership, and optimistic relation service tests."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Interest,
    Language,
    LanguageProficiency,
    ProfileLanguage,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas.profile_catalog import ProfileInterestUpdate, ProfileLanguageUpdate
from app.services.profile_catalogs import (
    get_own_catalog_selections,
    list_active_interests,
    list_active_languages,
    replace_own_interests,
    replace_own_languages,
)
from app.services.profiles import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
)

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
INTEREST_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


def _owner() -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
    )


def _profile(*, version: int = 3) -> StudentProfile:
    return StudentProfile(
        id=PROFILE_ID,
        user_id=USER_ID,
        full_name="Unrelated Name",
        matching_opt_in=True,
        version=version,
    )


def _result(values: list[object]) -> MagicMock:
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


@pytest.mark.anyio
async def test_catalog_reads_filter_inactive_values_and_use_stable_order() -> None:
    interest = Interest(
        id=INTEREST_ID,
        code="music",
        label_en="Music",
        label_de="Musik",
        category="culture",
    )
    language = Language(code="de", label_en="German", label_de="Deutsch")
    mock, session = _session(_profile())
    mock.scalars.side_effect = [_result([interest]), _result([language])]

    assert await list_active_interests(session) == (interest,)
    assert await list_active_languages(session) == (language,)

    interest_sql = str(mock.scalars.await_args_list[0].args[0]).lower()
    language_sql = str(mock.scalars.await_args_list[1].args[0]).lower()
    assert "interests.is_active is true" in interest_sql
    assert "interests.deleted_at is null" in interest_sql
    assert "order by" in interest_sql
    assert "languages.is_active is true" in language_sql
    assert "order by" in language_sql


@pytest.mark.anyio
async def test_interest_replacement_is_exact_versioned_and_preserves_unrelated_fields() -> None:
    profile = _profile()
    old_interest_id = uuid4()
    mock, session = _session(profile)
    mock.scalars.side_effect = [
        _result([INTEREST_ID]),
        _result([old_interest_id]),
    ]

    result = await replace_own_interests(
        session,
        _owner(),
        ProfileInterestUpdate(version=3, interest_ids=[INTEREST_ID]),
    )

    assert result.version == 4
    assert result.interest_ids == (INTEREST_ID,)
    assert profile.version == 4
    assert profile.full_name == "Unrelated Name"
    assert profile.matching_opt_in is True
    assert "FOR UPDATE" in str(mock.scalar.await_args.args[0]).upper()
    assert "DELETE FROM" in str(mock.execute.await_args.args[0]).upper()
    attached = list(mock.add_all.call_args.args[0])
    assert [(item.profile_id, item.interest_id) for item in attached] == [(PROFILE_ID, INTEREST_ID)]
    mock.flush.assert_awaited_once_with()


@pytest.mark.anyio
async def test_identical_interest_replacement_is_a_noop_without_version_churn() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.side_effect = [_result([INTEREST_ID]), _result([INTEREST_ID])]

    result = await replace_own_interests(
        session,
        _owner(),
        ProfileInterestUpdate(version=3, interest_ids=[INTEREST_ID]),
    )

    assert result.version == 3
    mock.execute.assert_not_awaited()
    mock.add_all.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_unknown_or_inactive_interest_fails_before_existing_relation_mutation() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.return_value = _result([])

    with pytest.raises(ProfileValidationError, match="interests"):
        await replace_own_interests(
            session,
            _owner(),
            ProfileInterestUpdate(version=3, interest_ids=[INTEREST_ID]),
        )

    assert profile.version == 3
    assert mock.scalars.await_count == 1
    mock.execute.assert_not_awaited()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_stale_relation_version_fails_before_catalog_read() -> None:
    profile = _profile(version=7)
    mock, session = _session(profile)

    with pytest.raises(ProfileVersionConflictError, match="stale"):
        await replace_own_interests(
            session,
            _owner(),
            ProfileInterestUpdate(version=6, interest_ids=[]),
        )

    mock.scalars.assert_not_awaited()
    mock.execute.assert_not_awaited()
    assert profile.version == 7


@pytest.mark.anyio
async def test_language_replacement_validates_codes_and_updates_proficiency_atomically() -> None:
    profile = _profile(version=5)
    old = ProfileLanguage(
        profile_id=PROFILE_ID,
        language_code="en",
        proficiency=LanguageProficiency.BEGINNER,
    )
    mock, session = _session(profile)
    mock.scalars.side_effect = [_result(["de", "en"]), _result([old])]
    payload = ProfileLanguageUpdate.model_validate(
        {
            "version": 5,
            "languages": [
                {"language_code": "en", "proficiency": "fluent"},
                {"language_code": "de", "proficiency": "intermediate"},
            ],
        }
    )

    result = await replace_own_languages(session, _owner(), payload)

    assert result.version == 6
    assert [selection.language_code for selection in result.languages] == ["de", "en"]
    assert profile.version == 6
    attached = list(mock.add_all.call_args.args[0])
    assert [(item.language_code, item.proficiency) for item in attached] == [
        ("de", LanguageProficiency.INTERMEDIATE),
        ("en", LanguageProficiency.FLUENT),
    ]
    mock.flush.assert_awaited_once_with()


@pytest.mark.anyio
async def test_unknown_language_fails_without_replacing_existing_relations() -> None:
    profile = _profile()
    mock, session = _session(profile)
    mock.scalars.return_value = _result([])
    payload = ProfileLanguageUpdate.model_validate(
        {
            "version": 3,
            "languages": [{"language_code": "en", "proficiency": "native"}],
        }
    )

    with pytest.raises(ProfileValidationError, match="languages"):
        await replace_own_languages(session, _owner(), payload)

    mock.execute.assert_not_awaited()
    mock.flush.assert_not_awaited()
    assert profile.version == 3


@pytest.mark.anyio
async def test_owner_selection_read_returns_canonical_relations() -> None:
    profile = _profile()
    language = ProfileLanguage(
        profile_id=PROFILE_ID,
        language_code="en",
        proficiency=LanguageProficiency.FLUENT,
    )
    mock, session = _session(profile)
    mock.scalars.side_effect = [_result([INTEREST_ID]), _result([language])]

    result = await get_own_catalog_selections(session, _owner(), profile)

    assert result.interest_ids == (INTEREST_ID,)
    assert result.languages[0].language_code == "en"
    assert result.languages[0].proficiency is LanguageProficiency.FLUENT


@pytest.mark.anyio
async def test_selection_read_rejects_a_profile_owned_by_another_user() -> None:
    profile = _profile()
    profile.user_id = uuid4()
    mock, session = _session(profile)

    with pytest.raises(ProfileAccessError, match="not permitted"):
        await get_own_catalog_selections(session, _owner(), profile)

    mock.scalars.assert_not_awaited()
