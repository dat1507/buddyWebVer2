"""Security and behavior tests for the public registration endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as auth_service
from app.core.config import CsrfSettings, get_csrf_settings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.schemas.auth import RegistrationRequest
from app.services.csrf import (
    CSRF_HEADER_NAME,
    create_preauth_csrf_token,
    create_session_csrf_token,
    csrf_cookie_name,
)

ALLOWED_ORIGIN = "https://app.example.com"
TEST_PASSWORD = "Correct horse battery staple"
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


class _PostgresViolation(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("test database constraint violation")
        self.sqlstate = sqlstate


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(bytes(range(32))),
        secure_cookies=False,
        trusted_origins=(ALLOWED_ORIGIN,),
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.rollback = AsyncMock()
    mock.commit = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install_dependencies(session: AsyncSession, settings: CsrfSettings) -> None:
    async def override_database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: settings


def _csrf_evidence(settings: CsrfSettings) -> tuple[dict[str, str], dict[str, str]]:
    token = create_preauth_csrf_token(settings)
    headers = {"Origin": ALLOWED_ORIGIN, CSRF_HEADER_NAME: token.value}
    cookies = {csrf_cookie_name(settings): token.value}
    return headers, cookies


def _payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "  Student@Example.COM  ",
        "password": TEST_PASSWORD,
        "consent": True,
    }
    payload.update(changes)
    return payload


@pytest.mark.anyio
async def test_registration_creates_only_a_user_and_returns_no_authentication_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    mock, session = _session()
    _install_dependencies(session, settings)
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    headers, cookies = _csrf_evidence(settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=_payload(),
            headers=headers,
        )

    assert response.status_code == 201
    assert response.json() == {"status": "registered"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert "set-cookie" not in response.headers
    assert "token" not in response.text.lower()
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()
    user = cast(User, mock.add.call_args.args[0])
    assert user.email == "student@example.com"
    assert user.role is UserRole.USER
    assert user.password_hash == TEST_PASSWORD_HASH
    assert user.email_verified is False
    assert user.email_verified_at is None


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["missing", "mismatched", "wrong-origin", "session-scope"])
async def test_registration_rejects_invalid_csrf_before_mutation(failure: str) -> None:
    settings = _settings()
    mock, session = _session()
    _install_dependencies(session, settings)
    headers, cookies = _csrf_evidence(settings)

    if failure == "missing":
        headers.pop(CSRF_HEADER_NAME)
    elif failure == "mismatched":
        headers[CSRF_HEADER_NAME] = create_preauth_csrf_token(settings).value
    elif failure == "wrong-origin":
        headers["Origin"] = "https://attacker.example"
    else:
        session_token = create_session_csrf_token(TEST_SESSION_ID, settings)
        headers[CSRF_HEADER_NAME] = session_token.value
        cookies[csrf_cookie_name(settings)] = session_token.value

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=_payload(),
            headers=headers,
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    assert response.headers["cache-control"] == "no-store"
    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_invalid_csrf_is_rejected_before_opening_a_database_session() -> None:
    settings = _settings()
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run before CSRF validation")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_csrf_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=_payload(),
            headers={"Origin": ALLOWED_ORIGIN},
        )

    assert response.status_code == 403
    assert database_dependency_called is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "changes",
    [
        {"email": "not-an-email"},
        {"password": "x" * 7},
        {"password": "x" * 73},
        {"password": ("é" * 36) + "a"},
        {"consent": False},
        {"consent": "true"},
        {"role": "ADMIN"},
    ],
)
async def test_registration_rejects_invalid_or_privilege_bearing_input_without_echoing_it(
    changes: dict[str, object],
) -> None:
    settings = _settings()
    mock, session = _session()
    _install_dependencies(session, settings)
    headers, cookies = _csrf_evidence(settings)
    payload = _payload(**changes)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=payload,
            headers=headers,
        )

    assert response.status_code == 422
    assert '"input"' not in response.text
    assert response.headers["cache-control"] == "no-store"
    for value in changes.values():
        assert str(value) not in response.text
    mock.add.assert_not_called()
    mock.commit.assert_not_awaited()


def test_registration_request_does_not_expose_password_in_repr() -> None:
    request = RegistrationRequest(
        email="student@example.com",
        password=TEST_PASSWORD,
        consent=True,
    )

    assert TEST_PASSWORD not in repr(request)


@pytest.mark.parametrize("password", ["x" * 8, "x" * 72, "é" * 36, " " * 8])
def test_registration_password_policy_accepts_length_boundary_unicode_and_whitespace(
    password: str,
) -> None:
    request = RegistrationRequest(
        email="student@example.com",
        password=password,
        consent=True,
    )

    assert request.password == password


@pytest.mark.anyio
async def test_duplicate_registration_returns_one_generic_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    mock, session = _session()
    _install_dependencies(session, settings)
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    mock.flush.side_effect = IntegrityError(
        "insert into users",
        {},
        _PostgresViolation("23505"),
    )
    headers, cookies = _csrf_evidence(settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=_payload(email="existing@example.com"),
            headers=headers,
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Account registration failed."}
    assert response.headers["cache-control"] == "no-store"
    assert "existing@example.com" not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_registration_rolls_back_and_sanitizes_an_unexpected_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    mock, session = _session()
    _install_dependencies(session, settings)
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    mock.commit.side_effect = RuntimeError("database secret must never be returned")
    headers, cookies = _csrf_evidence(settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json=_payload(),
            headers=headers,
        )

    assert response.status_code == 500
    assert "database secret" not in response.text
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_openapi_contract_requires_consent_and_has_no_role_input() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    schema = response.json()["components"]["schemas"]["RegistrationRequest"]
    assert set(schema["required"]) == {"email", "password", "consent"}
    assert "role" not in schema["properties"]
    assert response.json()["paths"]["/api/auth/register"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/RegistrationResponse"}
