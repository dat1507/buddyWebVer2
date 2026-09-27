"""REC-003 API authorization, rate, privacy, and response-contract tests."""

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
import app.core.rate_limits as rate_limits
from app.api.dependencies import require_auth, require_matching_eligibility
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import LanguageProficiency, StudentType, User, UserRole
from app.schemas.matching import (
    CompatibilityExplanation,
    CompatibilitySignalExplanation,
    MatchingRecommendation,
    MatchingRecommendationListResponse,
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.services.matching_eligibility import EligibleMatchingPrincipal
from app.services.matching_recommendations import (
    MatchingRecommendationCapacityError,
    MatchingRecommendationStateError,
)

USER_ID = UUID("10000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
CANDIDATE_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000001")
REFERENCE_WEEK = date(2026, 9, 21)
NOW = datetime(2026, 9, 27, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)


def _user(*, role: UserRole = UserRole.USER, verified: bool = True) -> User:
    return User(
        id=USER_ID,
        email="private@example.com",
        password_hash="private-hash",
        role=role,
        is_active=True,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
    )


def _principal() -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=USER_ID,
        profile_id=PROFILE_ID,
        student_type=StudentType.VIETNAMESE,
    )


def _profile() -> SafeMatchingProfile:
    return SafeMatchingProfile(
        id=CANDIDATE_PROFILE_ID,
        display_name="Alex",
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=SafeMatchingAvatar(id=UUID(int=91), width=640, height=480),
        interests=[
            SafeMatchingPreference(
                id=UUID(int=92),
                code="music",
                label="Music",
                is_custom=False,
            ),
            SafeMatchingPreference(
                id=None,
                code=None,
                label="Formula 1",
                is_custom=True,
            ),
        ],
        languages=[
            SafeMatchingLanguage(
                code=None,
                label="Thai",
                proficiency=LanguageProficiency.INTERMEDIATE,
                is_custom=True,
            )
        ],
        activities=[],
        availability=None,
    )


def _response() -> MatchingRecommendationListResponse:
    return MatchingRecommendationListResponse(
        items=[
            MatchingRecommendation(
                profile=_profile(),
                score=45,
                explanation=CompatibilityExplanation(
                    interests=CompatibilitySignalExplanation(
                        similarity=1,
                        weight=40,
                        points=40,
                    ),
                    activities=CompatibilitySignalExplanation(
                        similarity=0,
                        weight=35,
                        points=0,
                    ),
                    availability=CompatibilitySignalExplanation(
                        similarity=0,
                        weight=15,
                        points=0,
                    ),
                    languages=CompatibilitySignalExplanation(
                        similarity=1,
                        weight=5,
                        points=5,
                    ),
                    major=CompatibilitySignalExplanation(
                        similarity=0,
                        weight=5,
                        points=0,
                    ),
                ),
            )
        ],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
        reference_week_start=REFERENCE_WEEK,
    )


def _install_eligible() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    session = cast(AsyncSession, mock)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_auth] = _user
    app.dependency_overrides[require_matching_eligibility] = _principal
    return mock, session


@pytest.mark.anyio
async def test_recommendation_api_returns_private_safe_ranked_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _install_eligible()
    service = AsyncMock(return_value=_response())
    monkeypatch.setattr(matching_api, "list_ranked_matching_recommendations", service)
    monkeypatch.setattr(
        matching_api,
        "current_reference_week_start",
        lambda: REFERENCE_WEEK,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/matching/recommendations?page=1&page_size=20&locale=en"
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    body = response.json()
    assert body["items"][0]["profile"]["display_name"] == "Alex"
    assert body["items"][0]["score"] == 45
    assert body["reference_week_start"] == "2026-09-21"
    for forbidden in (
        "private@example.com",
        "private-hash",
        "normalized_key",
        "object_key",
        "bucket",
        str(USER_ID),
    ):
        assert forbidden not in response.text
    service.assert_awaited_once_with(
        session,
        _principal(),
        locale="en",
        page=1,
        page_size=20,
        reference_week_start=REFERENCE_WEEK,
    )
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_anonymous_request_stops_before_database_and_recommendation_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_called = False
    service = AsyncMock()

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_called
        database_called = True
        raise AssertionError("database dependency must not run")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = _settings
    monkeypatch.setattr(matching_api, "list_ranked_matching_recommendations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/recommendations")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert database_called is False
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "actor",
    [_user(role=UserRole.ADMIN), _user(verified=False)],
)
async def test_non_user_or_unverified_actor_is_denied_before_recommendation_query(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MagicMock(spec=AsyncSession)
    session = cast(AsyncSession, mock)
    service = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_auth] = lambda: actor
    monkeypatch.setattr(matching_api, "list_ranked_matching_recommendations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/recommendations")

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            MatchingRecommendationStateError(),
            409,
            "Matching eligibility changed. Refresh and try again.",
        ),
        (
            MatchingRecommendationCapacityError(),
            503,
            "Recommendations are temporarily unavailable.",
        ),
    ],
)
async def test_read_failures_are_sanitized_and_private(
    error: Exception,
    expected_status: int,
    expected_detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_eligible()
    monkeypatch.setattr(
        matching_api,
        "list_ranked_matching_recommendations",
        AsyncMock(side_effect=error),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/recommendations")

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert response.headers["cache-control"] == "private, no-store"
    assert "candidate" not in response.text.lower()


@pytest.mark.anyio
async def test_page_bounds_are_validated_without_calling_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_eligible()
    service = AsyncMock()
    monkeypatch.setattr(matching_api, "list_ranked_matching_recommendations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/recommendations?page_size=51")

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_recommendation_route_is_ip_rate_limited_before_second_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_eligible()
    service = AsyncMock(return_value=_response())
    monkeypatch.setattr(matching_api, "list_ranked_matching_recommendations", service)
    monkeypatch.setattr(rate_limits, "USER_REQUESTS_PER_MINUTE", 1)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        first = await client.get("/api/matching/recommendations")
        second = await client.get("/api/matching/recommendations")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["cache-control"] == "no-store"
    service.assert_awaited_once()


@pytest.mark.anyio
async def test_openapi_exposes_only_read_only_bounded_safe_recommendations() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    route = document["paths"]["/api/matching/recommendations"]
    assert set(route) == {"get"}
    operation = route["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters["page_size"]["schema"]["maximum"] == 50
    schemas = document["components"]["schemas"]
    forbidden = {
        "email",
        "password",
        "password_hash",
        "normalized_key",
        "object_key",
        "bucket",
        "user_id",
    }
    for schema_name in (
        "SafeMatchingAvatar",
        "SafeMatchingPreference",
        "SafeMatchingLanguage",
        "SafeMatchingProfile",
        "CompatibilitySignalExplanation",
        "CompatibilityExplanation",
        "MatchingRecommendation",
        "MatchingRecommendationListResponse",
    ):
        assert forbidden.isdisjoint(schemas[schema_name].get("properties", {}))
