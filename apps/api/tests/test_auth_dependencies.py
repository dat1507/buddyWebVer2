"""Security tests for the verified-current-user authentication dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AUTHENTICATION_REQUIRED_MESSAGE, require_auth
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.models import User, UserRole
from app.services.tokens import (
    DEVELOPMENT_ACCESS_COOKIE_NAME,
    PRODUCTION_ACCESS_COOKIE_NAME,
    access_cookie_name,
    create_token_pair,
)

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CLIENT_SUPPLIED_USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings(*, secure_cookies: bool = False) -> AuthTokenSettings:
    return AuthTokenSettings(
        signing_key=SecretBytes(TEST_SIGNING_KEY),
        secure_cookies=secure_cookies,
    )


def _user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    deleted: bool = False,
) -> User:
    return User(
        id=TEST_USER_ID,
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=is_active,
        email_verified=True,
        deleted_at=datetime.now(UTC) if deleted else None,
    )


def _session(return_value: User | None) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=return_value)
    return mock, cast(AsyncSession, mock)


def _probe_app(
    session_dependency: Callable[..., object],
    settings: AuthTokenSettings,
) -> FastAPI:
    probe = FastAPI()
    probe.dependency_overrides[get_database_session] = session_dependency
    probe.dependency_overrides[get_auth_token_settings] = lambda: settings

    @probe.post("/protected")
    async def protected(
        current_user: Annotated[User, Depends(require_auth)],
    ) -> dict[str, str]:
        return {"id": str(current_user.id), "role": current_user.role.value}

    return probe


def _cookie(token: str) -> dict[str, str]:
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: token}


def test_access_cookie_name_matches_environment_security_mode() -> None:
    assert access_cookie_name(_settings()) == DEVELOPMENT_ACCESS_COOKIE_NAME
    assert access_cookie_name(_settings(secure_cookies=True)) == PRODUCTION_ACCESS_COOKIE_NAME


@pytest.mark.anyio
async def test_dependency_uses_signed_subject_and_current_database_role_only() -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.ADMIN, settings)
    current_user = _user(role=UserRole.USER)
    mock, session = _session(current_user)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post(
            f"/protected?user_id={CLIENT_SUPPLIED_USER_ID}",
            json={"user_id": str(CLIENT_SUPPLIED_USER_ID), "role": "ADMIN"},
        )

    assert response.status_code == 200
    assert response.json() == {"id": str(TEST_USER_ID), "role": "USER"}
    statement = mock.scalar.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    compiled = statement.compile(dialect=dialect)
    sql = str(compiled)
    assert TEST_USER_ID in compiled.params.values()
    assert CLIENT_SUPPLIED_USER_ID not in compiled.params.values()
    assert "users.is_active IS true" in sql
    assert "users.deleted_at IS NULL" in sql


@pytest.mark.anyio
@pytest.mark.parametrize("credential", ["missing", "malformed", "expired", "refresh-token"])
async def test_invalid_access_cookie_returns_generic_401_before_database(
    credential: str,
) -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, settings)
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run before access verification")

    cookies: dict[str, str] = {}
    if credential == "malformed":
        cookies = _cookie("not-a-jwt")
    elif credential == "expired":
        expired_pair = create_token_pair(
            TEST_USER_ID,
            UserRole.USER,
            settings,
            now=datetime.now(UTC) - timedelta(hours=1),
        )
        cookies = _cookie(expired_pair.access_token)
    elif credential == "refresh-token":
        cookies = _cookie(pair.refresh_token)

    probe = _probe_app(forbidden_database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post("/protected")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTHENTICATION_REQUIRED_MESSAGE}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize("account_state", ["missing", "inactive", "deleted"])
async def test_missing_or_ineligible_database_user_returns_same_401(account_state: str) -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, settings)
    user = None
    if account_state == "inactive":
        user = _user(is_active=False)
    elif account_state == "deleted":
        user = _user(deleted=True)
    mock, session = _session(user)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post("/protected")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTHENTICATION_REQUIRED_MESSAGE}
    assert response.headers["cache-control"] == "no-store"
    mock.scalar.assert_awaited_once()


@pytest.mark.anyio
async def test_unknown_signed_subject_cannot_be_replaced_by_client_identity() -> None:
    settings = _settings()
    unknown_pair = create_token_pair(uuid4(), UserRole.USER, settings)
    mock, session = _session(None)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(unknown_pair.access_token),
    ) as client:
        response = await client.post(
            f"/protected?user_id={TEST_USER_ID}",
            json={"user_id": str(TEST_USER_ID)},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": AUTHENTICATION_REQUIRED_MESSAGE}
    mock.scalar.assert_awaited_once()
