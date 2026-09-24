"""Security and behavior tests for refresh-token rotation and reuse detection."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
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
from app.models import RefreshSession, User, UserRole
from app.services.csrf import (
    CSRF_HEADER_NAME,
    DEVELOPMENT_CSRF_COOKIE_NAME,
    create_preauth_csrf_token,
    create_session_csrf_token,
    csrf_cookie_name,
    verify_csrf_token,
)
from app.services.tokens import (
    DEVELOPMENT_ACCESS_COOKIE_NAME,
    DEVELOPMENT_REFRESH_COOKIE_NAME,
    TokenPair,
    create_token_pair,
    verify_access_token,
    verify_refresh_token,
)

ALLOWED_ORIGIN = "https://app.example.com"
TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
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


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(bytes(reversed(range(32)))),
        secure_cookies=False,
        trusted_origins=(ALLOWED_ORIGIN,),
    )


def _token_settings() -> AuthTokenSettings:
    return AuthTokenSettings(
        signing_key=SecretBytes(TEST_SIGNING_KEY),
        secure_cookies=False,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.flush = AsyncMock()
    mock.rollback = AsyncMock()
    mock.commit = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        id=TEST_USER_ID,
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=is_active,
        email_verified=True,
        deleted_at=deleted_at,
    )


def _pair() -> TokenPair:
    return create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _token_settings(),
        session_id=TEST_SESSION_ID,
        now=datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=1),
    )


def _persisted_session(
    pair: TokenPair,
    *,
    refresh_token_id: UUID | None = None,
    revoked_at: datetime | None = None,
) -> RefreshSession:
    return RefreshSession(
        id=pair.session_id,
        user_id=TEST_USER_ID,
        refresh_token_id=refresh_token_id or pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
        revoked_at=revoked_at,
    )


def _install_dependencies(
    session: AsyncSession,
    csrf_settings: CsrfSettings,
    token_settings: AuthTokenSettings,
) -> None:
    async def override_database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_auth_token_settings] = lambda: token_settings


def _session_evidence(
    pair: TokenPair,
    csrf_settings: CsrfSettings,
) -> tuple[dict[str, str], dict[str, str]]:
    token = create_session_csrf_token(pair.session_id, csrf_settings)
    headers = {"Origin": ALLOWED_ORIGIN, CSRF_HEADER_NAME: token.value}
    cookies = {
        DEVELOPMENT_REFRESH_COOKIE_NAME: pair.refresh_token,
        csrf_cookie_name(csrf_settings): token.value,
    }
    return headers, cookies


@pytest.mark.anyio
async def test_refresh_atomically_rotates_cookies_jti_csrf_and_current_role() -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    stored = _persisted_session(pair)
    user = _user(role=UserRole.ADMIN)
    mock, session = _session()
    mock.scalar.side_effect = [stored, user]
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _session_evidence(pair, csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": str(TEST_USER_ID),
        "email": "student@example.com",
        "role": "ADMIN",
        "email_verified": True,
        "email_verified_at": None,
    }
    assert set(body) == {"user", "csrf_token"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"

    access_token = response.cookies[DEVELOPMENT_ACCESS_COOKIE_NAME]
    refresh_token = response.cookies[DEVELOPMENT_REFRESH_COOKIE_NAME]
    csrf_token = response.cookies[DEVELOPMENT_CSRF_COOKIE_NAME]
    access_claims = verify_access_token(access_token, token_settings)
    refresh_claims = verify_refresh_token(refresh_token, token_settings)
    verify_csrf_token(
        csrf_token,
        csrf_settings,
        expected_scope="session",
        session_id=refresh_claims.session_id,
    )

    assert access_claims.role is UserRole.ADMIN
    assert access_claims.session_id == refresh_claims.session_id == TEST_SESSION_ID
    assert refresh_claims.token_id != pair.refresh_token_id
    assert stored.refresh_token_id == refresh_claims.token_id
    assert stored.expires_at == refresh_claims.expires_at
    assert body["csrf_token"] == csrf_token
    assert access_token not in response.text
    assert refresh_token not in response.text
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("supplied", ["missing", "malformed", "access-token"])
async def test_invalid_refresh_cookie_returns_generic_401_before_database(supplied: str) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run for an invalid refresh cookie")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_auth_token_settings] = lambda: token_settings
    headers, cookies = _session_evidence(pair, csrf_settings)
    if supplied == "missing":
        cookies.pop(DEVELOPMENT_REFRESH_COOKIE_NAME)
    elif supplied == "malformed":
        cookies[DEVELOPMENT_REFRESH_COOKIE_NAME] = "not-a-jwt"
    else:
        cookies[DEVELOPMENT_REFRESH_COOKIE_NAME] = pair.access_token

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Session is invalid or expired."}
    assert response.headers["cache-control"] == "no-store"
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failure", ["missing", "mismatched", "wrong-origin", "preauth", "wrong-session"]
)
async def test_refresh_rejects_invalid_csrf_before_database(failure: str) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run before CSRF validation")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_auth_token_settings] = lambda: token_settings
    headers, cookies = _session_evidence(pair, csrf_settings)
    if failure == "missing":
        headers.pop(CSRF_HEADER_NAME)
    elif failure == "mismatched":
        headers[CSRF_HEADER_NAME] = create_session_csrf_token(pair.session_id, csrf_settings).value
    elif failure == "wrong-origin":
        headers["Origin"] = "https://attacker.example"
    elif failure == "preauth":
        preauth = create_preauth_csrf_token(csrf_settings)
        headers[CSRF_HEADER_NAME] = preauth.value
        cookies[csrf_cookie_name(csrf_settings)] = preauth.value
    else:
        wrong = create_session_csrf_token(uuid4(), csrf_settings)
        headers[CSRF_HEADER_NAME] = wrong.value
        cookies[csrf_cookie_name(csrf_settings)] = wrong.value

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    assert response.headers["cache-control"] == "no-store"
    assert database_dependency_called is False


@pytest.mark.anyio
async def test_reused_refresh_token_revokes_family_and_returns_generic_401() -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    stored = _persisted_session(pair, refresh_token_id=uuid4())
    mock, session = _session()
    mock.scalar.return_value = stored
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _session_evidence(pair, csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Session is invalid or expired."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get_list("set-cookie") == []
    assert stored.revoked_at is not None
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["missing", "already-revoked"])
async def test_invalid_persisted_session_rolls_back_and_returns_same_401(state: str) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    stored = _persisted_session(
        pair,
        revoked_at=datetime.now(UTC) if state == "already-revoked" else None,
    )
    mock, session = _session()
    mock.scalar.return_value = None if state == "missing" else stored
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _session_evidence(pair, csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Session is invalid or expired."}
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_inactive_user_revokes_the_refresh_family() -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    stored = _persisted_session(pair)
    mock, session = _session()
    mock.scalar.side_effect = [stored, _user(is_active=False)]
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _session_evidence(pair, csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert stored.revoked_at is not None
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_rotation_commit_failure_rolls_back_without_setting_replacement_cookies() -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    pair = _pair()
    stored = _persisted_session(pair)
    mock, session = _session()
    mock.scalar.side_effect = [stored, _user()]
    mock.commit.side_effect = RuntimeError("database secret must never be returned")
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _session_evidence(pair, csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post("/api/auth/refresh", headers=headers)

    assert response.status_code == 500
    assert "database secret" not in response.text
    assert response.headers.get_list("set-cookie") == []
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_openapi_refresh_contract_exposes_no_request_or_jwt_response_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    document = response.json()
    operation = document["paths"]["/api/auth/refresh"]["post"]
    response_schema = document["components"]["schemas"]["RefreshResponse"]
    assert "requestBody" not in operation
    assert set(response_schema["properties"]) == {"user", "csrf_token"}
    assert "access_token" not in response_schema["properties"]
    assert "refresh_token" not in response_schema["properties"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RefreshResponse"
    }
