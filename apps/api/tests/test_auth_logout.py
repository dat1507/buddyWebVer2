"""Logout service, cookie/CSRF boundaries, and transaction failure regression checks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient, Cookies
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.core.rate_limits import get_auth_rate_limiter
from app.main import app
from app.models import RefreshSession, User, UserRole
from app.services.csrf import (
    CSRF_HEADER_NAME,
    create_preauth_csrf_token,
    create_session_csrf_token,
    csrf_cookie_name,
)
from app.services.refresh_sessions import revoke_refresh_session
from app.services.tokens import (
    TokenPair,
    access_cookie_name,
    create_token_pair,
    refresh_cookie_name,
    verify_refresh_token,
)

ORIGIN = "http://localhost:5173"


def _cookies(values: dict[str, str]) -> Cookies:
    jar = Cookies()
    for name, value in values.items():
        jar.set(name, value, domain="testserver.local", path="/")
    return jar


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings(secure: bool = False) -> tuple[AuthTokenSettings, CsrfSettings]:
    return (
        AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=secure),
        CsrfSettings(
            signing_key=SecretBytes(bytes(reversed(range(32)))),
            secure_cookies=secure,
            trusted_origins=(ORIGIN,),
        ),
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    for name in ("scalar", "flush", "commit", "rollback"):
        setattr(mock, name, AsyncMock())
    return mock, cast(AsyncSession, mock)


def _install(session: AsyncSession, token: AuthTokenSettings, csrf: CsrfSettings) -> MagicMock:
    opened = MagicMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        opened()
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: token
    app.dependency_overrides[get_csrf_settings] = lambda: csrf
    return opened


def _stored(pair: TokenPair) -> RefreshSession:
    return RefreshSession(
        id=pair.session_id,
        user_id=verify_refresh_token(pair.refresh_token, _settings()[0]).user_id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )


def _evidence(
    pair: TokenPair, token: AuthTokenSettings, csrf: CsrfSettings
) -> tuple[dict[str, str], dict[str, str]]:
    csrf_token = create_session_csrf_token(pair.session_id, csrf).value
    return (
        {"Origin": ORIGIN, CSRF_HEADER_NAME: csrf_token},
        {
            access_cookie_name(token): pair.access_token,
            refresh_cookie_name(token): pair.refresh_token,
            csrf_cookie_name(csrf): csrf_token,
        },
    )


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["active", "expired", "revoked", "deleted", "missing"])
async def test_revocation_locks_owner_bound_family_and_stages_only_once(state: str) -> None:
    token, _ = _settings()
    user_id = uuid4()
    pair = create_token_pair(user_id, UserRole.USER, token)
    row = _stored(pair)
    row.user_id = user_id
    now = datetime.now(UTC).replace(microsecond=0)
    if state == "expired":
        row.expires_at = now - timedelta(seconds=1)
    if state == "revoked":
        row.revoked_at = now - timedelta(minutes=1)
    if state == "deleted":
        row.deleted_at = now - timedelta(minutes=1)
    previous_revocation = row.revoked_at
    mock, session = _session()
    mock.scalar.return_value = None if state == "missing" else row

    await revoke_refresh_session(session, pair.session_id, user_id, now=now)

    statement = mock.scalar.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    assert "FOR UPDATE" in str(statement.compile(dialect=dialect))
    assert "refresh_sessions.id =" in str(statement.whereclause)
    assert "refresh_sessions.user_id =" in str(statement.whereclause)
    assert "refresh_token_id" not in str(statement.whereclause)
    assert set(statement.compile().params.values()) == {pair.session_id, user_id}
    mock.commit.assert_not_awaited()
    if state in {"active", "expired"}:
        assert row.revoked_at == now
        mock.flush.assert_awaited_once_with()
    else:
        assert row.revoked_at == previous_revocation
        mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_revocation_rejects_naive_time_before_database_work() -> None:
    mock, session = _session()
    with pytest.raises(ValueError, match="timezone-aware"):
        await revoke_refresh_session(session, uuid4(), uuid4(), now=datetime(2026, 1, 1))
    mock.scalar.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("secure", [False, True])
@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_logout_commits_then_clears_cookie_scopes_without_role_gate(
    secure: bool, role: UserRole
) -> None:
    token, csrf = _settings(secure)
    user_id = uuid4()
    pair = create_token_pair(user_id, role, token)
    row = _stored(pair)
    row.user_id = user_id
    # The same family may already have rotated: logout must not require the old JTI.
    row.refresh_token_id = uuid4()
    mock, session = _session()
    mock.scalar.return_value = row
    _install(session, token, csrf)
    headers, cookies = _evidence(pair, token, csrf)
    limiter = get_auth_rate_limiter()
    user = User(id=user_id, role=role)
    for _ in range(120 if role is UserRole.USER else 60):
        await limiter.check_user(user)

    async def committed() -> None:
        assert row.revoked_at is not None

    mock.commit.side_effect = committed
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", cookies=_cookies(cookies)
    ) as client:
        response = await client.post("/api/auth/logout", headers=headers)
        assert not client.cookies

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    deleted = response.headers.get_list("set-cookie")
    assert len(deleted) == 3
    for name in (access_cookie_name(token), refresh_cookie_name(token), csrf_cookie_name(csrf)):
        cookie = next(value for value in deleted if value.startswith(f"{name}="))
        assert "Max-Age=0" in cookie and "Path=/" in cookie
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert "Domain=" not in cookie
        assert ("Secure" in cookie) is secure
    mock.scalar.assert_awaited_once()
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("credential", ["expired-access", "access-only", "invalid-refresh"])
async def test_logout_uses_verified_family_even_without_a_valid_access_or_refresh_cookie(
    credential: str,
) -> None:
    token, csrf = _settings()
    user_id = uuid4()
    pair = create_token_pair(
        user_id,
        UserRole.USER,
        token,
        now=datetime.now(UTC) - timedelta(hours=1) if credential == "expired-access" else None,
    )
    row = _stored(pair)
    row.user_id = user_id
    mock, session = _session()
    mock.scalar.return_value = row
    _install(session, token, csrf)
    headers, cookies = _evidence(pair, token, csrf)
    if credential == "access-only":
        cookies.pop(refresh_cookie_name(token))
    if credential == "invalid-refresh":
        cookies[refresh_cookie_name(token)] = "untrusted.invalid.jwt"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", cookies=_cookies(cookies)
    ) as client:
        response = await client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 204
    assert row.revoked_at is not None
    mock.commit.assert_awaited_once_with()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid",
    [
        "missing-header",
        "missing-cookie",
        "missing-origin",
        "wrong-origin",
        "wrong-session",
        "preauth",
        "tampered",
        "duplicate-header",
        "untrusted-credentials",
    ],
)
async def test_logout_csrf_failures_do_not_open_database_or_clear_cookies(invalid: str) -> None:
    token, csrf = _settings()
    pair = create_token_pair(uuid4(), UserRole.USER, token)
    headers, cookies = _evidence(pair, token, csrf)
    if invalid == "missing-header":
        headers.pop(CSRF_HEADER_NAME)
    elif invalid == "missing-cookie":
        cookies.pop(csrf_cookie_name(csrf))
    elif invalid == "missing-origin":
        headers.pop("Origin")
    elif invalid == "wrong-origin":
        headers["Origin"] = "https://attacker.example"
    elif invalid == "untrusted-credentials":
        cookies[access_cookie_name(token)] = cookies[refresh_cookie_name(token)] = "invalid.jwt"
    elif invalid in {"wrong-session", "preauth", "tampered"}:
        value = (
            create_session_csrf_token(uuid4(), csrf).value
            if invalid == "wrong-session"
            else create_preauth_csrf_token(csrf).value
        )
        if invalid == "tampered":
            value = "invalid.signed.token"
        headers[CSRF_HEADER_NAME] = cookies[csrf_cookie_name(csrf)] = value
    mock, session = _session()
    opened = _install(session, token, csrf)
    request_headers = list(headers.items())
    if invalid == "duplicate-header":
        request_headers.append((CSRF_HEADER_NAME, headers[CSRF_HEADER_NAME]))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", cookies=_cookies(cookies)
    ) as client:
        response = await client.post("/api/auth/logout", headers=request_headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers.get_list("set-cookie") == []
    opened.assert_not_called()
    mock.scalar.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("credentials", ["none", "malformed", "expired", "wrong-key"])
async def test_anonymous_cleanup_requires_fresh_preauth_and_never_uses_unverified_claims(
    credentials: str,
) -> None:
    token, csrf = _settings()
    value = create_preauth_csrf_token(csrf).value
    cookies = {csrf_cookie_name(csrf): value}
    if credentials != "none":
        other_settings = AuthTokenSettings(signing_key=SecretBytes(b"X" * 32), secure_cookies=False)
        pair = create_token_pair(
            uuid4(),
            UserRole.ADMIN,
            other_settings if credentials == "wrong-key" else token,
            now=datetime.now(UTC) - timedelta(days=8) if credentials == "expired" else None,
        )
        cookies[refresh_cookie_name(token)] = (
            "invalid.jwt" if credentials == "malformed" else pair.refresh_token
        )
        cookies[access_cookie_name(token)] = (
            "invalid.jwt" if credentials == "malformed" else pair.access_token
        )
    mock, session = _session()
    _install(session, token, csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", cookies=_cookies(cookies)
    ) as client:
        response = await client.post(
            "/api/auth/logout", headers={"Origin": ORIGIN, CSRF_HEADER_NAME: value}
        )
        assert not client.cookies
        # Cookie clearing does not authorize an unprotected repeat request.
        assert (
            await client.post("/api/auth/logout", headers={"Origin": ORIGIN})
        ).status_code == 403
        value = (await client.get("/api/auth/csrf")).json()["csrf_token"]
        repeat = await client.post(
            "/api/auth/logout", headers={"Origin": ORIGIN, CSRF_HEADER_NAME: value}
        )
    assert response.status_code == repeat.status_code == 204
    mock.scalar.assert_not_awaited()
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["missing", "deleted", "revoked"])
async def test_signed_repeat_logout_is_indistinguishable_and_safe(state: str) -> None:
    token, csrf = _settings()
    pair = create_token_pair(uuid4(), UserRole.USER, token)
    row = _stored(pair)
    original_time = datetime.now(UTC) - timedelta(minutes=1)
    if state == "deleted":
        row.deleted_at = original_time
    if state == "revoked":
        row.revoked_at = original_time
    mock, session = _session()
    mock.scalar.return_value = None if state == "missing" else row
    _install(session, token, csrf)
    headers, cookies = _evidence(pair, token, csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://testserver", cookies=_cookies(cookies)
    ) as client:
        response = await client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 204
    assert len(response.headers.get_list("set-cookie")) == 3
    mock.flush.assert_not_awaited()
    mock.commit.assert_awaited_once_with()
    if state == "revoked":
        assert row.revoked_at == original_time


@pytest.mark.anyio
@pytest.mark.parametrize("stage", ["flush", "commit"])
@pytest.mark.parametrize("database_error", [False, True])
async def test_database_failure_rolls_back_and_never_claims_success_or_clears_cookies(
    stage: str,
    database_error: bool,
) -> None:
    token, csrf = _settings()
    pair = create_token_pair(uuid4(), UserRole.USER, token)
    mock, session = _session()
    mock.scalar.return_value = _stored(pair)
    error_type = SQLAlchemyError if database_error else RuntimeError
    getattr(mock, stage).side_effect = error_type("private database diagnostics")
    _install(session, token, csrf)
    headers, cookies = _evidence(pair, token, csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="https://testserver",
        cookies=_cookies(cookies),
    ) as client:
        response = await client.post("/api/auth/logout", headers=headers)
    assert response.status_code == (503 if database_error else 500)
    if database_error:
        assert response.json() == {"detail": "Session logout is unavailable."}
        assert response.headers["Cache-Control"] == "no-store"
    assert "private database diagnostics" not in response.text
    assert response.headers.get_list("set-cookie") == []
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_body_and_authorization_header_cannot_select_a_family_for_logout() -> None:
    token, csrf = _settings()
    pair = create_token_pair(uuid4(), UserRole.USER, token)
    value = create_preauth_csrf_token(csrf).value
    mock, session = _session()
    _install(session, token, csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies=_cookies({csrf_cookie_name(csrf): value}),
    ) as client:
        response = await client.post(
            "/api/auth/logout",
            json={"refresh_token": pair.refresh_token, "session_id": str(pair.session_id)},
            headers={
                "Origin": ORIGIN,
                CSRF_HEADER_NAME: value,
                "Authorization": f"Bearer {pair.access_token}",
            },
        )
    assert response.status_code == 204
    mock.scalar.assert_not_awaited()
    mock.commit.assert_not_awaited()


def test_logout_openapi_is_cookie_only_and_has_no_response_token_or_body() -> None:
    operation = app.openapi()["paths"]["/api/auth/logout"]["post"]
    assert "requestBody" not in operation
    assert "content" not in operation["responses"]["204"]
    assert {"429", "503"} <= set(operation["responses"])
