"""Persistence and concurrency tests for the own-profile service."""

from __future__ import annotations

import asyncio
import inspect
from datetime import date
from types import TracebackType
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, StudentProfile, StudentType, User, UserRole
from app.schemas import ProfileUpdate
from app.services import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
    get_or_create_own_profile,
    update_own_profile,
)


class _PostgresUniqueViolation(Exception):
    sqlstate = "23505"


class _RaceState:
    def __init__(self) -> None:
        self.profile: StudentProfile | None = None
        self.initial_reads = 0
        self.both_read = asyncio.Event()
        self.insert_lock = asyncio.Lock()


class _NestedTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False


class _RacingSession:
    def __init__(self, state: _RaceState) -> None:
        self.state = state
        self.initial_read_complete = False
        self.pending: StudentProfile | None = None

    async def scalar(self, statement: object) -> StudentProfile | None:
        del statement
        if not self.initial_read_complete:
            self.initial_read_complete = True
            self.state.initial_reads += 1
            if self.state.initial_reads == 2:
                self.state.both_read.set()
            await self.state.both_read.wait()
            return None
        return self.state.profile

    def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()

    def add(self, profile: StudentProfile) -> None:
        self.pending = profile

    async def flush(self) -> None:
        assert self.pending is not None
        async with self.state.insert_lock:
            if self.state.profile is not None:
                raise IntegrityError("insert", {}, _PostgresUniqueViolation())
            self.pending.id = uuid4()
            self.pending.version = 1
            self.state.profile = self.pending


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=uuid4(),
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=False,
    )


def _profile(owner: User, *, version: int = 1) -> StudentProfile:
    return StudentProfile(
        id=uuid4(),
        user_id=owner.id,
        full_name="Existing Student",
        display_name="Existing",
        version=version,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.scalars = AsyncMock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    return mock, cast(AsyncSession, mock)


def test_public_profile_services_require_server_user_instead_of_client_owner_id() -> None:
    get_parameters = inspect.signature(get_or_create_own_profile).parameters
    update_parameters = inspect.signature(update_own_profile).parameters

    assert tuple(get_parameters) == ("session", "owner")
    assert tuple(update_parameters) == ("session", "owner", "update")
    assert "user_id" not in get_parameters
    assert "user_id" not in update_parameters


@pytest.mark.anyio
async def test_two_concurrent_first_reads_converge_on_one_profile() -> None:
    owner = _user()
    state = _RaceState()
    first = cast(AsyncSession, _RacingSession(state))
    second = cast(AsyncSession, _RacingSession(state))

    first_result, second_result = await asyncio.gather(
        get_or_create_own_profile(first, owner),
        get_or_create_own_profile(second, owner),
    )

    assert state.profile is not None
    assert first_result is state.profile
    assert second_result is state.profile
    assert first_result.user_id == owner.id
    assert first_result.version == 1


@pytest.mark.anyio
async def test_existing_own_profile_is_returned_without_write_or_commit() -> None:
    owner = _user()
    existing = _profile(owner)
    mock, session = _session()
    mock.scalar.return_value = existing

    result = await get_or_create_own_profile(session, owner)

    assert result is existing
    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_profile_service_rejects_non_user_owner_before_database_access() -> None:
    mock, session = _session()

    with pytest.raises(ProfileAccessError, match="not permitted"):
        await get_or_create_own_profile(session, _user(role=UserRole.ADMIN))

    mock.scalar.assert_not_awaited()


@pytest.mark.anyio
async def test_partial_update_retains_omitted_fields_and_clears_optional_null() -> None:
    owner = _user()
    profile = _profile(owner, version=4)
    mock, session = _session()
    mock.scalar.return_value = profile
    update = ProfileUpdate.model_validate(
        {"version": 4, "display_name": None, "bio": "  Updated biography  "}
    )

    result = await update_own_profile(session, owner, update)

    assert result is profile
    assert profile.full_name == "Existing Student"
    assert profile.display_name is None
    assert profile.bio == "Updated biography"
    assert profile.version == 5
    statement = mock.scalar.await_args.args[0]
    rendered = str(statement).upper()
    assert "FOR UPDATE" in rendered
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_stale_profile_version_fails_before_mutation() -> None:
    owner = _user()
    profile = _profile(owner, version=5)
    mock, session = _session()
    mock.scalar.return_value = profile
    update = ProfileUpdate.model_validate({"version": 4, "full_name": "New Name"})

    with pytest.raises(ProfileVersionConflictError, match="stale"):
        await update_own_profile(session, owner, update)

    assert profile.full_name == "Existing Student"
    assert profile.version == 5
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_update_validates_merged_date_order_before_mutation() -> None:
    owner = _user()
    profile = _profile(owner, version=2)
    profile.arrival_date = date(2026, 10, 1)
    profile.departure_date = date(2026, 12, 1)
    mock, session = _session()
    mock.scalar.return_value = profile
    update = ProfileUpdate.model_validate({"version": 2, "arrival_date": "2027-01-01"})

    with pytest.raises(ProfileValidationError, match="dates"):
        await update_own_profile(session, owner, update)

    assert profile.arrival_date == date(2026, 10, 1)
    assert profile.version == 2
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_update_normalizes_availability_and_validates_active_activity_ids() -> None:
    owner = _user()
    profile = _profile(owner, version=3)
    activity_id = uuid4()
    activity = Activity(
        id=activity_id,
        code="night-market",
        label_en="Night market",
        label_de="Nachtmarkt",
    )
    mock, session = _session()
    mock.scalar.return_value = profile
    catalog_result = MagicMock()
    catalog_result.all.return_value = [activity]
    existing_result = MagicMock()
    existing_result.all.return_value = []
    mock.scalars.side_effect = [catalog_result, existing_result]
    update = ProfileUpdate.model_validate(
        {
            "version": 3,
            "availability": {
                "timezone": "Asia/Ho_Chi_Minh",
                "slots": [{"weekday": 5, "start_minute": 1320, "end_minute": 60}],
            },
            "preferences": {"preferred_activity_ids": [str(activity_id)]},
        }
    )

    await update_own_profile(session, owner, update)

    assert profile.availability == {
        "timezone": "Asia/Ho_Chi_Minh",
        "slots": [
            {"weekday": 5, "start_minute": 1320, "end_minute": 1440},
            {"weekday": 6, "start_minute": 0, "end_minute": 60},
        ],
    }
    assert profile.preferences is None
    assert profile.version == 4
    assert mock.scalars.await_count == 2
    attached = list(mock.add_all.call_args.args[0])
    assert [(item.profile_id, item.activity_id) for item in attached] == [
        (profile.id, activity_id)
    ]


@pytest.mark.anyio
async def test_unknown_or_inactive_activity_id_fails_before_mutation() -> None:
    owner = _user()
    profile = _profile(owner, version=7)
    activity_id = uuid4()
    mock, session = _session()
    mock.scalar.return_value = profile
    catalog_result = MagicMock()
    catalog_result.all.return_value = []
    mock.scalars.return_value = catalog_result
    update = ProfileUpdate.model_validate(
        {
            "version": 7,
            "display_name": "Must not be applied",
            "preferences": {"preferred_activity_ids": [str(activity_id)]},
        }
    )

    with pytest.raises(ProfileValidationError, match="preferences"):
        await update_own_profile(session, owner, update)

    assert profile.preferences is None
    assert profile.display_name == "Existing"
    assert profile.version == 7
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_student_type_and_matching_opt_in_use_validated_domain_values() -> None:
    owner = _user()
    profile = _profile(owner, version=1)
    mock, session = _session()
    mock.scalar.return_value = profile
    update = ProfileUpdate.model_validate(
        {
            "version": 1,
            "student_type": "VIETNAMESE",
            "matching_opt_in": True,
        }
    )

    await update_own_profile(session, owner, update)

    assert profile.student_type is StudentType.VIETNAMESE
    assert profile.matching_opt_in is True
    assert profile.version == 2
