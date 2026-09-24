"""EMAIL-004 API authorization, CSRF, session projection, and redaction tests."""

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
from app.api.auth import require_email_verification_delivery_settings
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    EmailVerificationDeliverySettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.email_changes import (
    EmailChangeAuthenticationError,
    EmailChangeConflictError,
    EmailChangePasswordError,
    EmailChangeResult,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ORIGIN = "https://buddy.example"
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
CURRENT_CREDENTIAL = "correct current password"
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


def _user(
    *,
    email: str = "student@example.com",
    role: UserRole = UserRole.USER,
    verified_at: datetime | None = VERIFIED_AT,
) -> User:
    return User(
        id=USER_ID,
        email=email,
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=True,
        email_verified=False,
        email_verified_at=verified_at,
    )


def _install(*users: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    for name in ("flush", "commit", "rollback"):
        setattr(mock, name, AsyncMock())
    mock.scalar = AsyncMock(side_effect=users)

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
async def test_change_commits_relocked_projection_and_keeps_existing_session_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _user()
    updated = _user(email="new.student@example.com", verified_at=None)
    mock, session = _install(original, updated)
    change = AsyncMock(return_value=EmailChangeResult(user=updated))
    monkeypatch.setattr(auth_api, "change_current_user_email", change)
    headers, cookies = _evidence(original)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email/change",
            json={
                "new_email": "  New.Student@Example.COM  ",
                "current_password": CURRENT_CREDENTIAL,
            },
            headers=headers,
        )
        reloaded = await client.get("/api/auth/me")

    expected_user = {
        "id": str(USER_ID),
        "email": "new.student@example.com",
        "role": "USER",
        "email_verified": False,
        "email_verified_at": None,
    }
    assert response.status_code == 200
    assert response.json() == {"status": "email_changed", "user": expected_user}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert "set-cookie" not in response.headers
    assert CURRENT_CREDENTIAL not in response.text
    assert reloaded.status_code == 200
    assert reloaded.json() == expected_user
    change.assert_awaited_once_with(
        session,
        USER_ID,
        "new.student@example.com",
        CURRENT_CREDENTIAL,
        DELIVERY_SETTINGS,
    )
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("failure", "status_code", "detail"),
    [
        (
            EmailChangePasswordError("private password diagnostics"),
            400,
            "Email change could not be authorized.",
        ),
        (
            EmailChangeAuthenticationError("private account diagnostics"),
            401,
            "Email change could not be authorized.",
        ),
        (
            EmailChangeConflictError("private account owner diagnostics"),
            409,
            "Email address could not be changed.",
        ),
    ],
)
async def test_change_returns_generic_authorization_and_conflict_failures(
    failure: Exception,
    status_code: int,
    detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    monkeypatch.setattr(
        auth_api,
        "change_current_user_email",
        AsyncMock(side_effect=failure),
    )
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email/change",
            json={"new_email": "shared@example.com", "current_password": CURRENT_CREDENTIAL},
            headers=headers,
        )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "private" not in response.text
    assert CURRENT_CREDENTIAL not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_change_requires_session_csrf_and_current_user_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    change = AsyncMock()
    monkeypatch.setattr(auth_api, "change_current_user_email", change)
    _headers, cookies = _evidence(user)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        missing_csrf = await client.post(
            "/api/auth/email/change",
            json={"new_email": "new@example.com", "current_password": CURRENT_CREDENTIAL},
        )
    assert missing_csrf.status_code == 403
    change.assert_not_awaited()
    mock.commit.assert_not_awaited()

    admin = _user(role=UserRole.ADMIN)
    _install(admin)
    headers, cookies = _evidence(admin)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        forbidden = await client.post(
            "/api/auth/email/change",
            json={"new_email": "new@example.com", "current_password": CURRENT_CREDENTIAL},
            headers=headers,
        )
    assert forbidden.status_code == 403
    change.assert_not_awaited()


@pytest.mark.anyio
async def test_change_sanitizes_database_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _session = _install(user)
    monkeypatch.setattr(
        auth_api,
        "change_current_user_email",
        AsyncMock(side_effect=SQLAlchemyError("private database diagnostics")),
    )
    headers, cookies = _evidence(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            "/api/auth/email/change",
            json={"new_email": "new@example.com", "current_password": CURRENT_CREDENTIAL},
            headers=headers,
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Email change is unavailable."}
    assert "private" not in response.text
    mock.rollback.assert_awaited_once_with()


def test_change_openapi_has_only_reviewed_inputs_and_redacts_password() -> None:
    document = app.openapi()
    operation = document["paths"]["/api/auth/email/change"]["post"]
    request_schema = document["components"]["schemas"]["EmailChangeRequest"]
    response_schema = document["components"]["schemas"]["EmailChangeResponse"]
    assert set(request_schema["properties"]) == {"new_email", "current_password"}
    assert request_schema["properties"]["current_password"]["writeOnly"] is True
    assert set(response_schema["properties"]) == {"status", "user"}
    assert {"200", "400", "401", "403", "409", "422", "429", "503"} <= set(
        operation["responses"]
    )
