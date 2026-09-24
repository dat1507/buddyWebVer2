"""EMAIL-003 confirmation API authentication, CSRF, response, and redaction tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.auth as auth_api
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.email_verification import (
    ConfirmedEmailVerification,
    EmailVerificationTokenError,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ORIGIN = "https://buddy.example"
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TOKEN = "A" * 43
VERIFIED_AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
TOKEN_SETTINGS = AuthTokenSettings(
    signing_key=SecretBytes(bytes(range(32))),
    secure_cookies=False,
)
CSRF_SETTINGS = CsrfSettings(
    signing_key=SecretBytes(bytes(reversed(range(32)))),
    secure_cookies=False,
    trusted_origins=(ORIGIN,),
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
        email_verified=False,
        email_verified_at=None,
    )


def _install(user: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    for name in ("scalar", "flush", "commit", "rollback"):
        setattr(mock, name, AsyncMock())
    mock.scalar.return_value = user

    async def database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, mock)

    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: TOKEN_SETTINGS
    app.dependency_overrides[get_csrf_settings] = lambda: CSRF_SETTINGS
    return mock, cast(AsyncSession, mock)


def _evidence(user: User) -> tuple[dict[str, str], dict[str, str]]:
    pair = create_token_pair(user.id, user.role, TOKEN_SETTINGS)
    csrf = create_session_csrf_token(pair.session_id, CSRF_SETTINGS)
    return (
        {"Origin": ORIGIN, CSRF_HEADER_NAME: csrf.value},
        {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(CSRF_SETTINGS): csrf.value,
        },
    )


@pytest.mark.anyio
async def test_confirm_commits_once_and_returns_only_a_fixed_internal_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, session = _install(user)
    confirm = AsyncMock(
        return_value=ConfirmedEmailVerification(
            user_id=user.id,
            email_verified_at=VERIFIED_AT,
        )
    )
    monkeypatch.setattr(auth_api, "confirm_email_verification_token", confirm)
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {"status": "email_verified", "redirect_to": "/user"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert TOKEN not in response.text
    confirm.assert_awaited_once_with(session, TOKEN, user.id)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["invalid", "expired", "replayed", "wrong-owner"])
async def test_all_token_failures_are_generic_and_rolled_back(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    confirm = AsyncMock(
        side_effect=EmailVerificationTokenError(
            f"private {failure} diagnostics containing {TOKEN}"
        )
    )
    monkeypatch.setattr(auth_api, "confirm_email_verification_token", confirm)
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN},
            headers=headers,
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Verification token is invalid or expired."}
    assert TOKEN not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_confirm_requires_session_csrf_and_current_user_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    confirm = AsyncMock()
    monkeypatch.setattr(auth_api, "confirm_email_verification_token", confirm)
    _headers, cookies = _evidence(user)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        missing_csrf = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN},
        )
    assert missing_csrf.status_code == 403
    confirm.assert_not_awaited()
    mock.commit.assert_not_awaited()

    admin = _user(role=UserRole.ADMIN)
    _install(admin)
    headers, cookies = _evidence(admin)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        forbidden = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN},
            headers=headers,
        )
    assert forbidden.status_code == 403
    confirm.assert_not_awaited()


@pytest.mark.anyio
async def test_confirm_rejects_client_redirects_and_sanitizes_database_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    confirm = AsyncMock()
    monkeypatch.setattr(auth_api, "confirm_email_verification_token", confirm)
    headers, cookies = _evidence(user)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        redirect = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN, "redirect_to": "https://attacker.example"},
            headers=headers,
        )
    assert redirect.status_code == 422
    confirm.assert_not_awaited()

    confirm.side_effect = SQLAlchemyError(f"private database diagnostics {TOKEN}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        unavailable = await client.post(
            "/api/auth/email-verification/confirm",
            json={"token": TOKEN},
            headers=headers,
        )
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "Email verification is unavailable."}
    assert TOKEN not in unavailable.text
    mock.rollback.assert_awaited_once_with()


def test_confirm_openapi_marks_token_write_only_and_has_no_redirect_input() -> None:
    document = app.openapi()
    operation = document["paths"]["/api/auth/email-verification/confirm"]["post"]
    request_schema = document["components"]["schemas"]["EmailVerificationConfirmRequest"]
    assert set(request_schema["properties"]) == {"token"}
    assert request_schema["properties"]["token"]["writeOnly"] is True
    assert {"200", "400", "403", "429", "503"} <= set(operation["responses"])
