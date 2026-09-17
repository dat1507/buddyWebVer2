"""Security and behavior tests for the public login endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as auth_service
from app.core.config import (
    AuthConfigurationError,
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import RefreshSession, User, UserRole
from app.schemas.auth import LoginRequest
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
    verify_access_token,
    verify_refresh_token,
)

ALLOWED_ORIGIN = "https://app.example.com"
TEST_PASSWORD = "Correct horse battery staple"
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
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


def _csrf_evidence(settings: CsrfSettings) -> tuple[dict[str, str], dict[str, str]]:
    token = create_preauth_csrf_token(settings)
    headers = {"Origin": ALLOWED_ORIGIN, CSRF_HEADER_NAME: token.value}
    cookies = {csrf_cookie_name(settings): token.value}
    return headers, cookies


def _payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "  Student@Example.COM  ",
        "password": TEST_PASSWORD,
    }
    payload.update(changes)
    return payload


@pytest.mark.anyio
async def test_login_sets_cookie_only_tokens_and_returns_a_sanitized_real_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    mock, session = _session()
    user = _user(role=UserRole.ADMIN)
    mock.scalar.return_value = user
    _install_dependencies(session, csrf_settings, token_settings)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/login", json=_payload(), headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"] == {
        "id": str(TEST_USER_ID),
        "email": "student@example.com",
        "role": "ADMIN",
        "email_verified": True,
    }
    assert set(payload) == {"user", "csrf_token"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"

    access_token = response.cookies[DEVELOPMENT_ACCESS_COOKIE_NAME]
    refresh_token = response.cookies[DEVELOPMENT_REFRESH_COOKIE_NAME]
    session_csrf = response.cookies[DEVELOPMENT_CSRF_COOKIE_NAME]
    access_claims = verify_access_token(access_token, token_settings)
    refresh_claims = verify_refresh_token(refresh_token, token_settings)
    verify_csrf_token(
        session_csrf,
        csrf_settings,
        expected_scope="session",
        session_id=access_claims.session_id,
    )

    assert access_claims.user_id == refresh_claims.user_id == TEST_USER_ID
    assert access_claims.role is UserRole.ADMIN
    assert access_claims.session_id == refresh_claims.session_id
    assert payload["csrf_token"] == session_csrf
    assert access_token not in response.text
    assert refresh_token not in response.text
    assert TEST_PASSWORD not in response.text
    assert TEST_PASSWORD_HASH not in response.text
    assert user.last_login is not None
    assert user.last_login.tzinfo is not None
    assert mock.flush.await_count == 2
    persisted_session = cast(RefreshSession, mock.add.call_args.args[0])
    assert persisted_session.id == access_claims.session_id
    assert persisted_session.user_id == TEST_USER_ID
    assert persisted_session.refresh_token_id == refresh_claims.token_id
    assert persisted_session.expires_at == refresh_claims.expires_at
    assert persisted_session.revoked_at is None
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("stored_user", "password_matches"),
    [
        (_user(), False),
        (None, False),
        (_user(is_active=False), True),
        (_user(deleted_at=datetime(2026, 9, 1, tzinfo=UTC)), True),
    ],
    ids=["wrong-password", "nonexistent-user", "inactive-user", "deleted-user"],
)
async def test_all_credential_and_account_failures_return_the_same_401_without_cookies(
    monkeypatch: pytest.MonkeyPatch,
    stored_user: User | None,
    password_matches: bool,
) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    mock, session = _session()
    mock.scalar.return_value = stored_user
    _install_dependencies(session, csrf_settings, token_settings)
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda _password, _hash: password_matches,
    )
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/login", json=_payload(), headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers.get_list("set-cookie") == []
    assert "student@example.com" not in response.text
    mock.commit.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": TEST_PASSWORD},
        {"email": "student@example.com", "password": ""},
        {"email": "student@example.com", "password": "x" * 73},
    ],
    ids=["malformed-email", "empty-password", "overlong-password"],
)
async def test_malformed_credentials_still_use_the_generic_401(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    mock, session = _session()
    mock.scalar.return_value = None
    _install_dependencies(session, csrf_settings, token_settings)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: False)
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/login", json=payload, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    for value in payload.values():
        if value:
            assert str(value) not in response.text
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["missing", "mismatched", "wrong-origin", "session-scope"])
async def test_login_rejects_invalid_csrf_before_opening_the_database(failure: str) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run before CSRF validation")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_auth_token_settings] = lambda: token_settings
    headers, cookies = _csrf_evidence(csrf_settings)

    if failure == "missing":
        headers.pop(CSRF_HEADER_NAME)
    elif failure == "mismatched":
        headers[CSRF_HEADER_NAME] = create_preauth_csrf_token(csrf_settings).value
    elif failure == "wrong-origin":
        headers["Origin"] = "https://attacker.example"
    else:
        session_token = create_session_csrf_token(TEST_SESSION_ID, csrf_settings)
        headers[CSRF_HEADER_NAME] = session_token.value
        cookies[csrf_cookie_name(csrf_settings)] = session_token.value

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/auth/login", json=_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    assert response.headers["cache-control"] == "no-store"
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "changes",
    [
        {"email": 123},
        {"password": 123},
        {"role": "ADMIN"},
    ],
)
async def test_login_rejects_invalid_or_privilege_bearing_shapes_without_echoing_input(
    changes: dict[str, object],
) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    mock, session = _session()
    _install_dependencies(session, csrf_settings, token_settings)
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/login",
            json=_payload(**changes),
            headers=headers,
        )

    assert response.status_code == 422
    assert '"input"' not in response.text
    assert response.headers["cache-control"] == "no-store"
    mock.scalar.assert_not_awaited()
    mock.commit.assert_not_awaited()


def test_login_request_does_not_expose_password_in_repr() -> None:
    request = LoginRequest(email="student@example.com", password=TEST_PASSWORD)

    assert TEST_PASSWORD not in repr(request)


@pytest.mark.anyio
async def test_login_rolls_back_and_sets_no_cookies_when_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf_settings = _csrf_settings()
    token_settings = _token_settings()
    mock, session = _session()
    mock.scalar.return_value = _user()
    mock.commit.side_effect = RuntimeError("database secret must never be returned")
    _install_dependencies(session, csrf_settings, token_settings)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post("/api/auth/login", json=_payload(), headers=headers)

    assert response.status_code == 500
    assert "database secret" not in response.text
    assert response.headers.get_list("set-cookie") == []
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_login_fails_closed_when_token_configuration_is_unavailable() -> None:
    csrf_settings = _csrf_settings()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database must not open with invalid token configuration")

    def missing_token_settings() -> AuthTokenSettings:
        raise AuthConfigurationError("AUTH_JWT_SECRET contains sensitive diagnostics")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_auth_token_settings] = missing_token_settings
    headers, cookies = _csrf_evidence(csrf_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post("/api/auth/login", json=_payload(), headers=headers)

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured."}
    assert response.headers["cache-control"] == "no-store"
    assert "sensitive diagnostics" not in response.text
    assert database_dependency_called is False


@pytest.mark.anyio
async def test_openapi_login_contract_has_no_role_input_or_token_response_fields() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    document = response.json()
    request_schema = document["components"]["schemas"]["LoginRequest"]
    response_schema = document["components"]["schemas"]["LoginResponse"]
    assert set(request_schema["required"]) == {"email", "password"}
    assert set(request_schema["properties"]) == {"email", "password"}
    assert "role" not in request_schema["properties"]
    assert set(response_schema["properties"]) == {"user", "csrf_token"}
    assert "access_token" not in response_schema["properties"]
    assert "refresh_token" not in response_schema["properties"]
    assert document["paths"]["/api/auth/login"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/LoginResponse"}
