"""Security and response-contract tests for the current-session endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(
        signing_key=SecretBytes(TEST_SIGNING_KEY),
        secure_cookies=False,
    )


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=TEST_USER_ID,
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=True,
        email_verified=True,
    )


def _session(user: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=user)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install_dependencies(session: AsyncSession, settings: AuthTokenSettings) -> None:
    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings


@pytest.mark.anyio
@pytest.mark.parametrize("current_role", [UserRole.USER, UserRole.ADMIN])
async def test_me_returns_only_sanitized_current_database_user(current_role: UserRole) -> None:
    settings = _settings()
    current_user = _user(role=current_role)
    mock, session = _session(current_user)
    _install_dependencies(session, settings)
    pair = create_token_pair(TEST_USER_ID, UserRole.ADMIN, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(TEST_USER_ID),
        "email": "student@example.com",
        "role": current_role.value,
        "email_verified": True,
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers.get_list("set-cookie") == []
    assert TEST_PASSWORD_HASH not in response.text
    assert pair.access_token not in response.text
    assert pair.refresh_token not in response.text
    mock.scalar.assert_awaited_once()
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("credential", ["missing", "malformed", "expired", "refresh-token"])
async def test_me_rejects_invalid_access_cookie_before_database(credential: str) -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, settings)
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run for an invalid access cookie")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    cookies: dict[str, str] = {}
    if credential == "malformed":
        cookies[DEVELOPMENT_ACCESS_COOKIE_NAME] = "not-a-jwt"
    elif credential == "expired":
        expired_pair = create_token_pair(
            TEST_USER_ID,
            UserRole.USER,
            settings,
            now=datetime.now(UTC) - timedelta(hours=1),
        )
        cookies[DEVELOPMENT_ACCESS_COOKIE_NAME] = expired_pair.access_token
    elif credential == "refresh-token":
        cookies[DEVELOPMENT_ACCESS_COOKIE_NAME] = pair.refresh_token

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert database_dependency_called is False


@pytest.mark.anyio
async def test_me_is_a_safe_read_that_does_not_require_csrf_or_profile_state() -> None:
    settings = _settings()
    current_user = _user()
    mock, session = _session(current_user)
    _install_dependencies(session, settings)
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(TEST_USER_ID)
    mock.scalar.assert_awaited_once()


@pytest.mark.anyio
async def test_openapi_me_contract_has_no_input_or_secret_response_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/openapi.json")

    document = response.json()
    operation = document["paths"]["/api/auth/me"]["get"]
    response_schema = document["components"]["schemas"]["SanitizedUserResponse"]
    assert "requestBody" not in operation
    assert set(response_schema["properties"]) == {"id", "email", "role", "email_verified"}
    assert "password" not in response_schema["properties"]
    assert "password_hash" not in response_schema["properties"]
    assert "access_token" not in response_schema["properties"]
    assert "refresh_token" not in response_schema["properties"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SanitizedUserResponse"
    }
