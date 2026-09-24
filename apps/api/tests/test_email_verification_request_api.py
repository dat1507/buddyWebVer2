"""EMAIL-002 authenticated API, CSRF, generic response, and rate-limit tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.auth as auth_api
from app.api.auth import require_email_verification_delivery_settings
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    EmailConfigurationError,
    EmailVerificationDeliverySettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.core.rate_limits import get_auth_rate_limiter
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.email_verification_requests import EmailVerificationRequestResult
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ORIGIN = "https://buddy.example"
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TOKEN_SETTINGS = AuthTokenSettings(
    signing_key=SecretBytes(bytes(range(32))),
    secure_cookies=False,
)
CSRF_SETTINGS = CsrfSettings(
    signing_key=SecretBytes(bytes(reversed(range(32)))),
    secure_cookies=False,
    trusted_origins=(ORIGIN,),
)
DELIVERY_SETTINGS = EmailVerificationDeliverySettings(
    public_app_base_url=ORIGIN,
    sealing_key=SecretBytes(bytes(range(32))),
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(*, role: UserRole = UserRole.USER, verified: bool = False) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
        email_verified=verified,
        email_verified_at=datetime(2026, 9, 24, 12, 0, tzinfo=UTC) if verified else None,
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
    app.dependency_overrides[require_email_verification_delivery_settings] = (
        lambda: DELIVERY_SETTINGS
    )
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
@pytest.mark.parametrize("verified", [False, True])
async def test_request_and_already_verified_return_the_same_generic_response(
    verified: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user(verified=verified)
    mock, _session = _install(user)
    request = AsyncMock(return_value=EmailVerificationRequestResult(created=not verified))
    monkeypatch.setattr(auth_api, "request_email_verification", request)
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email-verification/request",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {"status": "verification_requested"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert PASSWORD_HASH not in response.text
    request.assert_awaited_once()
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_request_requires_session_csrf_and_current_user_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    request = AsyncMock()
    monkeypatch.setattr(auth_api, "request_email_verification", request)
    _headers, cookies = _evidence(user)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        missing_csrf = await client.post("/api/auth/email-verification/request")
    assert missing_csrf.status_code == 403
    request.assert_not_awaited()
    mock.commit.assert_not_awaited()

    admin = _user(role=UserRole.ADMIN)
    _install(admin)
    headers, cookies = _evidence(admin)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        forbidden = await client.post(
            "/api/auth/email-verification/request", headers=headers
        )
    assert forbidden.status_code == 403
    request.assert_not_awaited()


@pytest.mark.anyio
async def test_request_enforces_existing_per_user_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    _install(user)
    request = AsyncMock()
    monkeypatch.setattr(auth_api, "request_email_verification", request)
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_user(user)
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email-verification/request", headers=headers
        )

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Please try again later."}
    request.assert_not_awaited()


def test_openapi_has_cookie_auth_no_body_and_generic_response_only() -> None:
    operation = app.openapi()["paths"]["/api/auth/email-verification/request"]["post"]
    assert "requestBody" not in operation
    assert {"200", "403", "429", "503"} <= set(operation["responses"])


def test_missing_delivery_configuration_fails_closed_without_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable() -> EmailVerificationDeliverySettings:
        raise EmailConfigurationError("private key diagnostics")

    monkeypatch.setattr(auth_api, "get_email_verification_delivery_settings", unavailable)
    with pytest.raises(HTTPException) as raised:
        require_email_verification_delivery_settings()
    assert getattr(raised.value, "status_code", None) == 503
    assert str(getattr(raised.value, "detail", "")) == "Email verification is unavailable."
    assert "private key diagnostics" not in str(raised.value)
