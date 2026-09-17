"""Security tests for the exact database-role authorization dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Annotated, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AUTHENTICATION_REQUIRED_MESSAGE,
    AUTHORIZATION_REQUIRED_MESSAGE,
    require_role,
)
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.models import User, UserRole
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(
        signing_key=SecretBytes(TEST_SIGNING_KEY),
        secure_cookies=False,
    )


def _user(
    *,
    role: UserRole,
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

    @probe.post("/admin")
    async def admin_only(
        current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    ) -> dict[str, str]:
        return {"id": str(current_user.id), "role": current_user.role.value}

    @probe.post("/user")
    async def user_only(
        current_user: Annotated[User, Depends(require_role(UserRole.USER))],
    ) -> dict[str, str]:
        return {"id": str(current_user.id), "role": current_user.role.value}

    return probe


def _cookie(token: str) -> dict[str, str]:
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: token}


@pytest.mark.anyio
async def test_admin_gate_uses_current_database_role_not_stale_token_claim() -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, settings)
    mock, session = _session(_user(role=UserRole.ADMIN))

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post("/admin")

    assert response.status_code == 200
    assert response.json() == {"id": str(TEST_USER_ID), "role": "ADMIN"}
    mock.scalar.assert_awaited_once()


@pytest.mark.anyio
async def test_admin_gate_rejects_current_user_role_despite_admin_token_and_client_input() -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.ADMIN, settings)
    mock, session = _session(_user(role=UserRole.USER))

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post(
            "/admin?role=ADMIN",
            json={"role": "ADMIN", "user_id": str(TEST_USER_ID)},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": AUTHORIZATION_REQUIRED_MESSAGE}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert "set-cookie" not in response.headers
    assert "USER" not in response.text
    assert "ADMIN" not in response.text
    mock.scalar.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("database_role", "path", "expected_status"),
    [
        (UserRole.USER, "/user", 200),
        (UserRole.ADMIN, "/user", 403),
        (UserRole.USER, "/admin", 403),
        (UserRole.ADMIN, "/admin", 200),
    ],
)
async def test_role_gate_uses_exact_role_semantics(
    database_role: UserRole,
    path: str,
    expected_status: int,
) -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, database_role, settings)
    _, session = _session(_user(role=database_role))

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post(path)

    assert response.status_code == expected_status


@pytest.mark.anyio
async def test_missing_access_cookie_stays_an_authentication_failure() -> None:
    settings = _settings()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run before access verification")

    probe = _probe_app(forbidden_database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
    ) as client:
        response = await client.post("/admin")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTHENTICATION_REQUIRED_MESSAGE}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize("account_state", ["inactive", "deleted"])
async def test_ineligible_user_stays_an_authentication_failure(account_state: str) -> None:
    settings = _settings()
    pair = create_token_pair(TEST_USER_ID, UserRole.ADMIN, settings)
    user = _user(
        role=UserRole.ADMIN,
        is_active=account_state != "inactive",
        deleted=account_state == "deleted",
    )
    mock, session = _session(user)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, settings)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(pair.access_token),
    ) as client:
        response = await client.post("/admin")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTHENTICATION_REQUIRED_MESSAGE}
    mock.scalar.assert_awaited_once()


def test_role_factory_rejects_non_enum_configuration() -> None:
    with pytest.raises(TypeError, match="^required_role must be a UserRole\\.$"):
        require_role(cast(UserRole, "ADMIN"))
