"""BUDDY-002 HTTP authorization, ownership, privacy, and pagination tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.matching as matching_api
from app.api.dependencies import require_auth, require_verified_buddy_capability
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import LanguageProficiency, StudentProfile, StudentType, User, UserRole
from app.schemas.matching import (
    CompatibilityExplanation,
    CompatibilitySignalExplanation,
    CurrentBuddy,
    CurrentBuddyListResponse,
    SafeInvitationProfile,
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
)
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.current_buddies import CurrentBuddyReadStateError

NOW = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
USER_ID = UUID("10000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
BUDDY_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
MATCH_ID = UUID("30000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("40000000-0000-4000-8000-000000000001")
PHOTO_ID = UUID("50000000-0000-4000-8000-000000000001")
INTEREST_ID = UUID("60000000-0000-4000-8000-000000000001")
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(*, verified: bool = True, active: bool = True, deleted: bool = False) -> User:
    return User(
        id=USER_ID,
        email="private@example.invalid",
        password_hash="private-test-hash",
        role=UserRole.USER,
        is_active=active,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
        deleted_at=NOW if deleted else None,
    )


def _principal() -> VerifiedBuddyPrincipal:
    return VerifiedBuddyPrincipal(
        user=_user(),
        profile=StudentProfile(
            id=PROFILE_ID,
            user_id=USER_ID,
            full_name="Private Current Name",
            student_type=StudentType.VIETNAMESE,
        ),
    )


def _response() -> CurrentBuddyListResponse:
    explanation = CompatibilityExplanation(
        interests=CompatibilitySignalExplanation(similarity=1, weight=40, points=40),
        activities=CompatibilitySignalExplanation(similarity=0.5, weight=35, points=17.5),
        availability=CompatibilitySignalExplanation(similarity=0, weight=15, points=0),
        languages=CompatibilitySignalExplanation(similarity=1, weight=5, points=5),
        major=CompatibilitySignalExplanation(similarity=0, weight=5, points=0),
    )
    profile = SafeInvitationProfile(
        id=BUDDY_PROFILE_ID,
        display_name="Buddy",
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=SafeMatchingAvatar(id=PHOTO_ID, width=640, height=480),
        interests=[
            SafeMatchingPreference(
                id=INTEREST_ID,
                code="music",
                label="Music",
                is_custom=False,
            )
        ],
        languages=[
            SafeMatchingLanguage(
                code="en",
                label="English",
                proficiency=LanguageProficiency.FLUENT,
                is_custom=False,
            )
        ],
        activities=[],
        availability=None,
    )
    return CurrentBuddyListResponse(
        items=[
            CurrentBuddy(
                match_id=MATCH_ID,
                conversation_id=CONVERSATION_ID,
                buddy=profile,
                score=63,
                explanation=explanation,
                reference_week_start=date(2026, 9, 28),
            )
        ],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install_verified(session: AsyncSession) -> VerifiedBuddyPrincipal:
    principal = _principal()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_verified_buddy_capability] = lambda: principal
    return principal


@pytest.mark.anyio
async def test_current_buddies_returns_only_private_owner_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    principal = _install_verified(session)
    service = AsyncMock(return_value=_response())
    monkeypatch.setattr(matching_api, "list_current_buddies", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/matching/buddies?locale=de&page=1&page_size=20&user_id={UUID(int=99)}"
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    body = response.json()
    assert body["items"][0]["match_id"] == str(MATCH_ID)
    assert body["items"][0]["conversation_id"] == str(CONVERSATION_ID)
    assert body["items"][0]["buddy"]["id"] == str(BUDDY_PROFILE_ID)
    assert body["items"][0]["score"] == 63
    assert body["items"][0]["reference_week_start"] == "2026-09-28"
    for forbidden in (
        "private@example.invalid",
        "private-test-hash",
        str(USER_ID),
        "normalized_key",
        "object_key",
        "bucket",
        "accepted_invitation_id",
        "semester_id",
        "score_breakdown",
        "version",
    ):
        assert forbidden not in response.text
    service.assert_awaited_once_with(
        session,
        principal,
        locale="de",
        page=1,
        page_size=20,
    )
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_anonymous_request_is_rejected_before_database_or_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_called = False
    service = AsyncMock()

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_called
        database_called = True
        raise AssertionError("database dependency must not run")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: AuthTokenSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
    )
    monkeypatch.setattr(matching_api, "list_current_buddies", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/buddies")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert database_called is False
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "actor",
    (_user(verified=False), _user(active=False), _user(deleted=True)),
)
async def test_unverified_inactive_or_deleted_user_is_locked_before_service(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_auth] = lambda: actor
    service = AsyncMock()
    monkeypatch.setattr(matching_api, "list_current_buddies", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/buddies")

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_pagination_validation_stops_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    _install_verified(session)
    service = AsyncMock()
    monkeypatch.setattr(matching_api, "list_current_buddies", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/buddies?page_size=51")

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_invalid_relationship_state_is_sanitized_and_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    _install_verified(session)
    monkeypatch.setattr(
        matching_api,
        "list_current_buddies",
        AsyncMock(side_effect=CurrentBuddyReadStateError("private match id")),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/buddies")

    assert response.status_code == 409
    assert response.json() == {"detail": "Current Buddies changed. Refresh and try again."}
    assert response.headers["cache-control"] == "private, no-store"
    assert "private match id" not in response.text


@pytest.mark.anyio
async def test_openapi_exposes_bounded_route_and_only_safe_dto_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    operation = document["paths"]["/api/matching/buddies"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters["page_size"]["schema"]["default"] == 20
    assert parameters["page_size"]["schema"]["maximum"] == 50
    schemas = document["components"]["schemas"]
    assert "CurrentBuddyListResponse" in schemas
    assert set(schemas["CurrentBuddy"]["properties"]) == {
        "match_id",
        "conversation_id",
        "buddy",
        "score",
        "explanation",
        "reference_week_start",
    }
    forbidden = {
        "email",
        "user_id",
        "password_hash",
        "normalized_key",
        "object_key",
        "bucket",
        "accepted_invitation_id",
        "semester_id",
        "score_breakdown",
        "version",
    }
    for schema_name in ("CurrentBuddy", "CurrentBuddyListResponse", "SafeInvitationProfile"):
        assert forbidden.isdisjoint(schemas[schema_name].get("properties", {}))
