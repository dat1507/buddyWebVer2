"""Authorization, transaction, and response-contract tests for own-profile endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import (
    LanguageProficiency,
    ProfileLanguage,
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
        trusted_origins=("http://testserver",),
    )


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _profile(*, version: int = 3) -> StudentProfile:
    return StudentProfile(
        id=PROFILE_ID,
        user_id=USER_ID,
        full_name="Existing Student",
        display_name="Existing",
        student_type=StudentType.VIETNAMESE,
        major="Computer Science",
        matching_opt_in=False,
        version=version,
    )


def _session(*scalar_values: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=scalar_values)
    mock.scalars = AsyncMock()
    empty_scalars = MagicMock()
    empty_scalars.all.return_value = []
    mock.scalars.return_value = empty_scalars
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    mock.execute = AsyncMock(return_value=empty_result)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(session: AsyncSession) -> tuple[AuthTokenSettings, CsrfSettings]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    return auth_settings, csrf_settings


def _session_evidence(
    role: UserRole = UserRole.USER,
) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()
    pair = create_token_pair(USER_ID, role, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    cookies = {
        DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
        csrf_cookie_name(csrf_settings): csrf.value,
    }
    headers = {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value}
    return cookies, headers


def _expected_profile(profile: StudentProfile) -> dict[str, object]:
    return {
        "id": str(PROFILE_ID),
        "full_name": profile.full_name,
        "display_name": profile.display_name,
        "student_type": profile.student_type.value if profile.student_type else None,
        "nationality": profile.nationality,
        "major": profile.major,
        "study_year": profile.study_year,
        "bio": profile.bio,
        "home_university": profile.home_university,
        "arrival_date": profile.arrival_date.isoformat() if profile.arrival_date else None,
        "departure_date": profile.departure_date.isoformat() if profile.departure_date else None,
        "availability": profile.availability,
        "preferences": profile.preferences,
        "matching_opt_in": profile.matching_opt_in,
        "version": profile.version,
        "avatar": None,
        "interest_ids": [],
        "languages": [],
    }


@pytest.mark.anyio
async def test_get_lazily_creates_and_commits_one_private_draft() -> None:
    user = _user()
    mock, session = _session(user, None)
    nested = MagicMock(spec=AbstractAsyncContextManager[None])
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=False)
    mock.begin_nested.return_value = nested

    async def assign_database_defaults() -> None:
        draft = mock.add.call_args.args[0]
        draft.id = PROFILE_ID
        draft.version = 1
        draft.matching_opt_in = False

    mock.flush.side_effect = assign_database_defaults
    auth_settings, _csrf_settings_value = _install(session)
    pair = create_token_pair(USER_ID, UserRole.USER, auth_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        response = await client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["id"] == str(PROFILE_ID)
    assert response.json()["version"] == 1
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert mock.add.call_count == 1
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_get_attaches_safe_avatar_metadata_without_storage_reference() -> None:
    user = _user()
    profile = _profile()
    photo = ProfilePhoto(
        id=uuid4(),
        profile_id=PROFILE_ID,
        bucket="profile-images",
        object_key="cccccccc-cccc-4ccc-8ccc-cccccccccccc.png",
        mime_type="image/png",
        byte_size=120,
        width=12,
        height=10,
        is_avatar=True,
        processing_status=ProfilePhotoProcessingStatus.READY,
        created_at=datetime(2026, 9, 20, 10, 30, tzinfo=UTC),
    )
    mock, session = _session(user, profile)
    photo_result = MagicMock()
    photo_result.scalar_one_or_none.return_value = photo
    mock.execute.return_value = photo_result
    _install(session)
    cookies, _headers = _session_evidence()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["avatar"] == {
        "id": str(photo.id),
        "mime_type": "image/png",
        "byte_size": 120,
        "width": 12,
        "height": 10,
        "processing_status": "READY",
        "created_at": "2026-09-20T10:30:00Z",
    }
    assert photo.object_key not in response.text
    assert photo.bucket not in response.text


@pytest.mark.anyio
async def test_get_attaches_normalized_catalog_selections_for_resume() -> None:
    user = _user()
    profile = _profile()
    interest_id = uuid4()
    language = ProfileLanguage(
        profile_id=PROFILE_ID,
        language_code="de",
        proficiency=LanguageProficiency.INTERMEDIATE,
    )
    mock, session = _session(user, profile)
    interest_result = MagicMock()
    interest_result.all.return_value = [interest_id]
    language_result = MagicMock()
    language_result.all.return_value = [language]
    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock.scalars.side_effect = [
        empty_result,
        interest_result,
        language_result,
        empty_result,
    ]
    _install(session)
    cookies, _headers = _session_evidence()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/profile")

    assert response.status_code == 200
    assert response.json()["interest_ids"] == [str(interest_id)]
    assert response.json()["languages"] == [{"language_code": "de", "proficiency": "intermediate"}]


@pytest.mark.anyio
async def test_put_then_get_saves_and_reloads_partial_onboarding_fields() -> None:
    user = _user()
    profile = _profile()
    mock, session = _session(user, profile, user, profile)
    _install(session)
    cookies, headers = _session_evidence()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        updated = await client.put(
            "/api/profile",
            headers=headers,
            json={
                "version": 3,
                "full_name": "  Updated Student  ",
                "display_name": None,
                "study_year": 2,
            },
        )
        reloaded = await client.get("/api/profile")

    assert updated.status_code == 200
    assert reloaded.status_code == 200
    assert profile.full_name == "Updated Student"
    assert profile.display_name is None
    assert profile.major == "Computer Science"
    assert profile.version == 4
    assert updated.json() == _expected_profile(profile)
    assert reloaded.json() == _expected_profile(profile)
    assert updated.headers["cache-control"] == "no-store"
    assert reloaded.headers["cache-control"] == "no-store"
    assert mock.commit.await_count == 2
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["GET", "PUT"])
async def test_profile_endpoints_reject_anonymous_before_database_access(method: str) -> None:
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = _auth_settings
    app.dependency_overrides[get_csrf_settings] = _csrf_settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.request(
            method,
            "/api/profile",
            json={"version": 1, "full_name": "Student"} if method == "PUT" else None,
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["cache-control"] == "no-store"
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize("method", ["GET", "PUT"])
async def test_profile_endpoints_reject_admin(method: str) -> None:
    mock, session = _session(_user(role=UserRole.ADMIN))
    _install(session)
    cookies, headers = _session_evidence(UserRole.USER)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.request(
            method,
            "/api/profile",
            headers=headers,
            json={"version": 1, "full_name": "Student"} if method == "PUT" else None,
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}
    assert response.headers["cache-control"] == "no-store"
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("csrf_evidence", ["missing", "other-session"])
async def test_put_requires_session_bound_csrf_before_profile_work(csrf_evidence: str) -> None:
    mock, session = _session(_user())
    auth_settings, csrf_settings = _install(session)
    pair = create_token_pair(USER_ID, UserRole.USER, auth_settings)
    cookies = {DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token}
    headers: dict[str, str] = {}
    if csrf_evidence == "other-session":
        other_pair = create_token_pair(uuid4(), UserRole.USER, auth_settings)
        other_csrf = create_session_csrf_token(other_pair.session_id, csrf_settings)
        cookies[csrf_cookie_name(csrf_settings)] = other_csrf.value
        headers = {"Origin": "http://testserver", CSRF_HEADER_NAME: other_csrf.value}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.put(
            "/api/profile",
            headers=headers,
            json={"version": 1, "full_name": "Student"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    assert response.headers["cache-control"] == "no-store"
    assert mock.scalar.await_count == 1
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("field_name", ["user_id", "role", "completion", "onboarding_completed_at"])
async def test_put_rejects_cross_user_and_derived_fields(field_name: str) -> None:
    mock, session = _session(_user())
    _install(session)
    cookies, headers = _session_evidence()

    untrusted_value = "untrusted-cross-user-value"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile",
            headers=headers,
            json={"version": 1, "full_name": "Student", field_name: untrusted_value},
        )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert untrusted_value not in response.text
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_stale_version_returns_409_without_mutation() -> None:
    user = _user()
    profile = _profile(version=5)
    mock, session = _session(user, profile)
    _install(session)
    cookies, headers = _session_evidence()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile",
            headers=headers,
            json={"version": 4, "full_name": "Must not be applied"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Profile version is stale."}
    assert response.headers["cache-control"] == "no-store"
    assert profile.full_name == "Existing Student"
    assert profile.version == 5
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_catalog_validation_failure_does_not_apply_other_fields() -> None:
    user = _user()
    profile = _profile(version=7)
    mock, session = _session(user, profile)
    catalog_result = MagicMock()
    catalog_result.all.return_value = []
    mock.scalars.return_value = catalog_result
    _install(session)
    cookies, headers = _session_evidence()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            "/api/profile",
            headers=headers,
            json={
                "version": 7,
                "display_name": "Must not be applied",
                "preferences": {"preferred_activity_ids": [str(uuid4())]},
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Profile update is invalid."}
    assert response.headers["cache-control"] == "no-store"
    assert profile.display_name == "Existing"
    assert profile.preferences is None
    assert profile.version == 7
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_commit_failure_rolls_back_and_produces_no_success_response() -> None:
    user = _user()
    profile = _profile()
    mock, session = _session(user, profile)
    mock.commit.side_effect = RuntimeError("database unavailable")
    auth_settings, _csrf_settings_value = _install(session)
    pair = create_token_pair(USER_ID, UserRole.USER, auth_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        with pytest.raises(RuntimeError, match="database unavailable"):
            await client.get("/api/profile")

    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_openapi_exposes_only_own_profile_dto_and_allowlisted_update() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    document = response.json()
    operations = document["paths"]["/api/profile"]
    response_properties = document["components"]["schemas"]["OwnProfileResponse"]["properties"]
    update_schema = document["components"]["schemas"]["ProfileUpdate"]
    forbidden = {
        "user_id",
        "role",
        "email",
        "completion",
        "onboarding_completed_at",
        "password",
        "password_hash",
    }

    assert set(operations) == {"get", "put"}
    assert forbidden.isdisjoint(response_properties)
    assert forbidden.isdisjoint(update_schema["properties"])
    assert update_schema["additionalProperties"] is False
    assert operations["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OwnProfileResponse"
    }
