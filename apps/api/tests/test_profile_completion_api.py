"""Transport and authorization tests for the profile completion read model."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import profile as profile_api
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.schemas.profile_completion import (
    MatchingIneligibilityReason,
    ProfileCompletionResponse,
    ProfileCompletionStatus,
    ProfileMissingField,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _user(role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=False,
    )


def _session(actor: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=actor)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(session: AsyncSession, role: UserRole = UserRole.USER) -> dict[str, str]:
    settings = _settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    pair = create_token_pair(USER_ID, role, settings)
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token}


@pytest.mark.anyio
async def test_user_reads_private_backend_derived_completion_without_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies = _install(session)
    service = AsyncMock(
        return_value=ProfileCompletionResponse(
            status=ProfileCompletionStatus.INCOMPLETE,
            percentage=60,
            missing_fields=[ProfileMissingField.AVATAR, ProfileMissingField.LANGUAGES],
            matching_eligible=False,
            reasons=[
                MatchingIneligibilityReason.PROFILE_INCOMPLETE,
                MatchingIneligibilityReason.MATCHING_OPT_IN_REQUIRED,
            ],
        )
    )
    monkeypatch.setattr(profile_api, "get_own_profile_completion", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/profile/completion")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.json() == {
        "status": "INCOMPLETE",
        "percentage": 60,
        "missing_fields": ["AVATAR", "LANGUAGES"],
        "matching_eligible": False,
        "reasons": ["PROFILE_INCOMPLETE", "MATCHING_OPT_IN_REQUIRED"],
    }
    service.assert_awaited_once_with(session, actor)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_cannot_read_student_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _user(UserRole.ADMIN)
    mock, session = _session(actor)
    cookies = _install(session, UserRole.ADMIN)
    service = AsyncMock()
    monkeypatch.setattr(profile_api, "get_own_profile_completion", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/profile/completion")

    assert response.status_code == 403
    service.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_anonymous_request_stops_before_database_access() -> None:
    mock, session = _session(_user())
    _install(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/profile/completion")

    assert response.status_code == 401
    mock.scalar.assert_not_awaited()


@pytest.mark.anyio
async def test_completion_failure_rolls_back_without_false_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    cookies = _install(session)
    monkeypatch.setattr(
        profile_api,
        "get_own_profile_completion",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
        ) as client:
            await client.get("/api/profile/completion")

    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_openapi_exposes_read_only_completion_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    operation = document["paths"]["/api/profile/completion"]
    assert set(operation) == {"get"}
    assert "requestBody" not in operation["get"]
    properties = document["components"]["schemas"]["ProfileCompletionResponse"]["properties"]
    assert set(properties) == {
        "status",
        "percentage",
        "missing_fields",
        "matching_eligible",
        "reasons",
    }
