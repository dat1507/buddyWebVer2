"""Reload recovery: verified cookies + trusted source + live owner-bound family."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient, Cookies
from pydantic import SecretBytes
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

import app.services.auth as auth_service
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
    CsrfValidationError,
    create_preauth_csrf_token,
    create_session_csrf_token,
    csrf_cookie_name,
    verify_csrf_token,
)
from app.services.tokens import (
    access_cookie_name,
    create_token_pair,
    refresh_cookie_name,
    verify_refresh_token,
)

ORIGIN = "http://localhost:5173"
TOKEN = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)
CSRF = CsrfSettings(
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


def _install(mock: MagicMock) -> MagicMock:
    opened = MagicMock()

    async def database() -> AsyncIterator[AsyncSession]:
        opened()
        yield cast(AsyncSession, mock)

    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: TOKEN
    app.dependency_overrides[get_csrf_settings] = lambda: CSRF
    return opened


def _mock() -> MagicMock:
    mock = MagicMock(spec=AsyncSession)
    for name in ("scalar", "flush", "commit", "rollback"):
        setattr(mock, name, AsyncMock())
    return mock


@pytest.mark.anyio
@pytest.mark.parametrize("expired_access", [False, True])
async def test_reload_recovers_csrf_then_me_refresh_logout(expired_access: bool) -> None:
    user = User(
        id=uuid4(),
        email="student@example.com",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=False,
    )
    pair = create_token_pair(
        user.id,
        user.role,
        TOKEN,
        now=datetime.now(UTC) - timedelta(minutes=20 if expired_access else 1),
    )
    stored = RefreshSession(
        id=pair.session_id,
        user_id=user.id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )
    original_jti = stored.refresh_token_id
    mock = _mock()
    mock.scalar.return_value = stored
    _install(mock)
    cookie_csrf = create_session_csrf_token(pair.session_id, CSRF).value
    jar = Cookies()
    for name, value in {
        access_cookie_name(TOKEN): pair.access_token,
        refresh_cookie_name(TOKEN): pair.refresh_token,
        csrf_cookie_name(CSRF): cookie_csrf,
    }.items():
        jar.set(name, value, domain="testserver.local", path="/")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=jar,
    ) as client:
        # Frontend JSON token has been lost; only browser cookies survive.
        recovered = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
        assert recovered.status_code == 200
        token = recovered.json()["csrf_token"]
        assert set(recovered.json()) == {"csrf_token"}
        assert token == cookie_csrf
        assert recovered.headers["cache-control"] == "no-store"
        assert recovered.headers["pragma"] == "no-cache"
        assert "set-cookie" not in recovered.headers
        verify_csrf_token(token, CSRF, expected_scope="session", session_id=pair.session_id)
        assert stored.refresh_token_id == original_jti
        mock.commit.assert_not_awaited()
        mock.flush.assert_not_awaited()
        mock.add.assert_not_called()
        query = str(mock.scalar.call_args.args[0])
        assert "user_id =" in query and "FOR UPDATE" not in query
        if expired_access:
            assert (await client.get("/api/auth/me")).status_code == 401
        mock.scalar.side_effect = [stored, user]
        refreshed = await client.post(
            "/api/auth/refresh", headers={"Origin": ORIGIN, CSRF_HEADER_NAME: token}
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["user"]["role"] == "ADMIN"
        assert stored.refresh_token_id != original_jti
        mock.scalar.side_effect = None
        mock.scalar.return_value = user
        assert (await client.get("/api/auth/me")).status_code == 200
        mock.scalar.return_value = stored
        logged_out = await client.post(
            "/api/auth/logout",
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: refreshed.json()["csrf_token"]},
        )
        assert logged_out.status_code == 204 and stored.revoked_at is not None
        assert len(client.cookies) == 0
        assert (
            await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
        ).status_code == 401


@pytest.mark.anyio
@pytest.mark.parametrize("cookie_state", ["missing", "preauth", "wrong-session", "expired"])
async def test_recovery_replaces_only_invalid_csrf_cookie(cookie_state: str) -> None:
    pair = create_token_pair(uuid4(), UserRole.USER, TOKEN)
    mock = _mock()
    mock.scalar.return_value = RefreshSession(
        id=pair.session_id,
        user_id=verify_refresh_token(pair.refresh_token, TOKEN).user_id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )
    _install(mock)
    cookies = {refresh_cookie_name(TOKEN): pair.refresh_token}
    if cookie_state == "preauth":
        cookies[csrf_cookie_name(CSRF)] = create_preauth_csrf_token(CSRF).value
    elif cookie_state == "wrong-session":
        cookies[csrf_cookie_name(CSRF)] = create_session_csrf_token(uuid4(), CSRF).value
    elif cookie_state == "expired":
        cookies[csrf_cookie_name(CSRF)] = create_session_csrf_token(
            pair.session_id, CSRF, now=datetime.now(UTC) - timedelta(days=8)
        ).value
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(
            "/api/auth/csrf/session", headers={"Referer": f"{ORIGIN}/login"}
        )
    assert response.status_code == 200
    value = response.json()["csrf_token"]
    verify_csrf_token(value, CSRF, expected_scope="session", session_id=pair.session_id)
    assert response.cookies[csrf_cookie_name(CSRF)] == value
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    with pytest.raises(CsrfValidationError):
        verify_csrf_token(value, CSRF, expected_scope="session", session_id=uuid4())
    with pytest.raises(CsrfValidationError):
        verify_csrf_token(value, CSRF, expected_scope="preauth")


@pytest.mark.anyio
@pytest.mark.parametrize("invalid", ["none", "tampered", "expired", "wrong-type"])
async def test_invalid_auth_fails_before_database(invalid: str) -> None:
    pair = create_token_pair(
        uuid4(), UserRole.USER, TOKEN, now=datetime.now(UTC) - timedelta(days=8)
    )
    values = {
        "tampered": "invalid.jwt",
        "expired": pair.refresh_token,
        "wrong-type": pair.access_token,
    }
    cookies = {} if invalid == "none" else {refresh_cookie_name(TOKEN): values[invalid]}
    mock = _mock()
    opened = _install(mock)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.json() == {"detail": "Session is invalid or expired."}
    assert response.headers["cache-control"] == "no-store"
    opened.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "null"},
        {"Origin": "https://attacker.example"},
        {"Origin": "https://attacker.example", "Referer": ORIGIN},
    ],
)
async def test_untrusted_source_fails_before_database(headers: dict[str, str]) -> None:
    pair = create_token_pair(uuid4(), UserRole.USER, TOKEN)
    opened = _install(_mock())
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={refresh_cookie_name(TOKEN): pair.refresh_token},
    ) as client:
        response = await client.get("/api/auth/csrf/session", headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    opened.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state",
    [
        "missing",
        "revoked",
        "deleted",
        "expired",
        "wrong-owner",
        "wrong-family",
        "stale-jti",
        "database-error",
    ],
)
async def test_invalid_family_never_recovers_or_mutates(state: str) -> None:
    pair = create_token_pair(uuid4(), UserRole.USER, TOKEN)
    stored = RefreshSession(
        id=pair.session_id,
        user_id=verify_refresh_token(pair.refresh_token, TOKEN).user_id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )
    now = datetime.now(UTC)
    if state == "revoked":
        stored.revoked_at = now
    elif state == "deleted":
        stored.deleted_at = now
    elif state == "expired":
        stored.expires_at = now - timedelta(seconds=1)
    elif state == "wrong-owner":
        stored.user_id = uuid4()
    elif state == "wrong-family":
        stored.id = uuid4()
    elif state == "stale-jti":
        stored.refresh_token_id = uuid4()
    mock = _mock()
    mock.scalar.return_value = None if state == "missing" else stored
    if state == "database-error":
        mock.scalar.side_effect = SQLAlchemyError("sensitive internal detail")
    _install(mock)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={refresh_cookie_name(TOKEN): pair.refresh_token},
    ) as client:
        response = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
    assert response.status_code == (503 if state == "database-error" else 401)
    assert "sensitive" not in response.text
    assert "set-cookie" not in response.headers
    mock.commit.assert_not_awaited()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_access_fallback_recovers_for_logout_without_refresh() -> None:
    pair = create_token_pair(uuid4(), UserRole.USER, TOKEN)
    mock = _mock()
    mock.scalar.return_value = RefreshSession(
        id=pair.session_id,
        user_id=verify_refresh_token(pair.refresh_token, TOKEN).user_id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )
    _install(mock)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={access_cookie_name(TOKEN): pair.access_token},
    ) as client:
        recovered = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
        assert recovered.status_code == 200
        response = await client.post(
            "/api/auth/logout",
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: recovered.json()["csrf_token"]},
        )
        assert response.status_code == 204


@pytest.mark.anyio
async def test_login_then_lost_json_csrf_can_recover_and_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        id=uuid4(),
        email="student@example.com",
        role=UserRole.USER,
        password_hash="test-only-hash",
        is_active=True,
        email_verified=False,
    )
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    mock = _mock()
    families: list[RefreshSession] = []
    mock.add.side_effect = families.append

    async def lookup(
        statement: Select[tuple[User]] | Select[tuple[RefreshSession]],
    ) -> User | RefreshSession | None:
        return (
            user
            if statement.column_descriptions[0]["entity"] is User
            else families[0]
            if families
            else None
        )

    mock.scalar.side_effect = lookup
    _install(mock)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        preauth = (await client.get("/api/auth/csrf")).json()["csrf_token"]
        logged_in = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "test-only password"},
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: preauth},
        )
        assert logged_in.status_code == 200 and len(families) == 1
        original_jti = families[0].refresh_token_id
        # Ignore login JSON entirely, as a reloaded frontend does.
        recovered = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
        assert recovered.status_code == 200
        assert families[0].refresh_token_id == original_jti
        refreshed = await client.post(
            "/api/auth/refresh",
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: recovered.json()["csrf_token"]},
        )
        assert refreshed.status_code == 200
        assert families[0].refresh_token_id != original_jti


@pytest.mark.anyio
async def test_recovery_preserves_production_cookie_flags_and_cross_session_rejection() -> None:
    secure_token = AuthTokenSettings(signing_key=TOKEN.signing_key, secure_cookies=True)
    secure_csrf = CsrfSettings(
        signing_key=CSRF.signing_key, secure_cookies=True, trusted_origins=(ORIGIN,)
    )
    pair = create_token_pair(uuid4(), UserRole.USER, secure_token)
    mock = _mock()
    mock.scalar.return_value = RefreshSession(
        id=pair.session_id,
        user_id=verify_refresh_token(pair.refresh_token, secure_token).user_id,
        refresh_token_id=pair.refresh_token_id,
        expires_at=pair.refresh_expires_at,
    )
    _install(mock)
    app.dependency_overrides[get_auth_token_settings] = lambda: secure_token
    app.dependency_overrides[get_csrf_settings] = lambda: secure_csrf
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://testserver",
        cookies={refresh_cookie_name(secure_token): pair.refresh_token},
    ) as client:
        recovery = await client.get("/api/auth/csrf/session", headers={"Origin": ORIGIN})
        assert recovery.status_code == 200
        cookie = recovery.headers["set-cookie"]
        assert cookie.startswith("__Host-vgu_buddy_csrf=")
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert "Domain=" not in cookie and "Path=/" in cookie
        # Swap the auth cookie to another valid family but retain recovered session A CSRF.
        other = create_token_pair(uuid4(), UserRole.USER, secure_token)
        client.cookies.clear()
        client.cookies.set(refresh_cookie_name(secure_token), other.refresh_token)
        client.cookies.set(csrf_cookie_name(secure_csrf), recovery.json()["csrf_token"])
        refresh = await client.post(
            "/api/auth/refresh",
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: recovery.json()["csrf_token"]},
        )
        assert refresh.status_code == 403
