"""Exact quota, runtime-router, isolation, proxy, lockout and fail-closed acceptance."""

from __future__ import annotations

import asyncio
import socket
import time
from collections.abc import AsyncIterator, Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp
from uvicorn._types import ASGI3Application
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import app.services.auth as auth_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.core.rate_limits import (
    AUTH_ENDPOINTS,
    RateLimitExceeded,
    RateLimitUnavailable,
    check_user_rate_limit,
    client_identifier,
    get_auth_rate_limiter,
    login_identifier,
)
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_preauth_csrf_token, csrf_cookie_name
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ORIGIN = "http://localhost:5173"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_app_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-only-placeholder",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _dependencies(user: User | None) -> tuple[MagicMock, AuthTokenSettings, CsrfSettings]:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=user)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    settings = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)
    csrf = CsrfSettings(
        signing_key=SecretBytes(bytes(reversed(range(32)))),
        secure_cookies=False,
        trusted_origins=(ORIGIN,),
    )
    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf
    return session, settings, csrf


@pytest.mark.anyio
@pytest.mark.parametrize(("role", "allowed"), [(UserRole.USER, 120), (UserRole.ADMIN, 60)])
async def test_current_database_role_exact_http_quota(role: UserRole, allowed: int) -> None:
    user = _user(role)
    _session, settings, _csrf = _dependencies(user)
    opposite_claim = UserRole.ADMIN if role is UserRole.USER else UserRole.USER
    pair = create_token_pair(user.id, opposite_claim, settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        for _ in range(allowed):
            response = await client.get("/api/auth/me")
            assert response.status_code == 200
            assert response.json()["role"] == role.value
        response = await client.get("/api/auth/me")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Please try again later."}
    assert 1 <= int(response.headers["retry-after"]) <= 60
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.anyio
@pytest.mark.parametrize(("method", "path"), sorted(AUTH_ENDPOINTS))
async def test_every_included_auth_route_is_guarded_before_dependencies(
    method: str, path: str
) -> None:
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_ip("127.0.0.1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.request(method, path, json={})
    assert response.status_code == 429


@pytest.mark.anyio
async def test_mount_root_path_and_trailing_slash_do_not_bypass_ip_gate() -> None:
    outer = FastAPI()
    outer.mount("/backend", app)
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_ip("127.0.0.1")
    async with AsyncClient(
        transport=ASGITransport(app=outer), base_url="http://testserver"
    ) as client:
        assert (await client.get("/backend/api/auth/csrf")).status_code == 429
        assert (await client.get("/backend/api/auth/csrf/")).status_code == 429


@pytest.mark.anyio
async def test_invalid_requests_count_and_forwarded_header_spoofing_cannot_bypass() -> None:
    _dependencies(None)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        for attempt in range(120):
            response = await client.post(
                "/api/auth/login",
                json={"email": "student@example.com", "password": "wrong"},
                headers={"X-Forwarded-For": f"192.0.2.{attempt + 1}"},
            )
            assert response.status_code == 403
        response = await client.get("/api/auth/csrf", headers={"X-Real-IP": "203.0.113.1"})
    assert response.status_code == 429


@pytest.mark.anyio
async def test_different_transport_ip_is_isolated_and_cors_survives_429() -> None:
    _dependencies(None)
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_ip("192.0.2.1")
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.1", 1234)),
        base_url="http://testserver",
    ) as blocked:
        response = await blocked.get("/api/auth/csrf", headers={"Origin": ORIGIN})
        assert response.status_code == 429
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert "Retry-After" in response.headers["access-control-expose-headers"]
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.2", 1234)),
        base_url="http://testserver",
    ) as other:
        assert (await other.get("/api/auth/csrf")).status_code == 200


@pytest.mark.anyio
async def test_per_user_quota_survives_ip_and_session_rotation_and_isolates_other_users() -> None:
    limiter = get_auth_rate_limiter()
    user = _user(UserRole.ADMIN)
    for _ in range(60):
        await limiter.check_user(user)
    with pytest.raises(RateLimitExceeded):
        await limiter.check_user(user)
    user.id = uuid4()
    await limiter.check_user(user)
    await limiter.check_ip("192.0.2.30")


@pytest.mark.anyio
@pytest.mark.parametrize(("role", "allowed"), [(UserRole.USER, 120), (UserRole.ADMIN, 60)])
async def test_login_and_me_share_identity_quota_across_transport_and_session_changes(
    role: UserRole, allowed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _user(role)
    _mock, _settings, csrf = _dependencies(user)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    limiter = get_auth_rate_limiter()
    for _ in range(allowed - 1):
        await limiter.check_user(user)
    token = create_preauth_csrf_token(csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.1", 1234)),
        base_url="http://testserver",
        cookies={csrf_cookie_name(csrf): token.value},
    ) as client:
        logged_in = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "test-only-password"},
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: token.value},
        )
        assert logged_in.status_code == 200
        cookie = logged_in.cookies[DEVELOPMENT_ACCESS_COOKIE_NAME]
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("192.0.2.2", 1234)),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: cookie},
    ) as other_ip:
        assert (await other_ip.get("/api/auth/me")).status_code == 429


@pytest.mark.anyio
async def test_role_throttled_login_rolls_back_without_committing_or_setting_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user(UserRole.ADMIN)
    mock, _settings, csrf = _dependencies(user)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    limiter = get_auth_rate_limiter()
    for _ in range(60):
        await limiter.check_user(user)
    token = create_preauth_csrf_token(csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={csrf_cookie_name(csrf): token.value},
    ) as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "test-only-password"},
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: token.value},
        )
    assert response.status_code == 429
    assert response.headers.get_list("set-cookie") == []
    mock.commit.assert_not_awaited()
    mock.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_failed_database_commit_does_not_reset_prior_login_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, _settings, csrf = _dependencies(user)
    mock.commit.side_effect = RuntimeError("commit failed")
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: True)
    limiter = get_auth_rate_limiter()
    identifier = login_identifier(user.email)
    for _ in range(4):
        await limiter.login_failed(identifier)
    token = create_preauth_csrf_token(csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies={csrf_cookie_name(csrf): token.value},
    ) as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "test-only-password"},
            headers={"Origin": ORIGIN, CSRF_HEADER_NAME: token.value},
        )
    assert response.status_code == 500
    assert response.headers.get_list("set-cookie") == []
    await limiter.login_failed(identifier)
    with pytest.raises(RateLimitExceeded):
        await limiter.check_login(identifier)


@pytest.mark.anyio
async def test_request_and_account_windows_reset_without_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_ip("192.0.2.1")
    with pytest.raises(RateLimitExceeded):
        await limiter.check_ip("192.0.2.1")
    now[0] += 61
    await limiter.check_ip("192.0.2.1")
    account = login_identifier("admin@example.com")
    for _ in range(5):
        await limiter.login_failed(account)
    with pytest.raises(RateLimitExceeded) as error:
        await limiter.check_login(account)
    assert error.value.headers is not None
    assert int(error.value.headers["Retry-After"]) == 900
    now[0] += 901
    await limiter.check_login(account)


@pytest.mark.anyio
@pytest.mark.parametrize("stored_user", [_user(UserRole.ADMIN), _user(), None])
async def test_five_wrong_logins_then_lockout_is_uniform_and_blocks_before_database(
    stored_user: User | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock, _settings, csrf = _dependencies(stored_user)
    monkeypatch.setattr(auth_service, "verify_password", lambda _password, _hash: False)
    token = create_preauth_csrf_token(csrf)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={csrf_cookie_name(csrf): token.value},
    ) as client:
        headers = {"Origin": ORIGIN, CSRF_HEADER_NAME: token.value}
        for attempt in range(5):
            response = await client.post(
                "/api/auth/login",
                json={"email": " Student@Example.COM ", "password": "wrong"},
                headers=headers,
            )
            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid email or password."}
            assert mock.scalar.await_count == attempt + 1
        response = await client.post(
            "/api/auth/login",
            json={"email": "student@example.com", "password": "correct-but-locked"},
            headers=headers,
        )
    assert response.status_code == 429
    assert 899 <= int(response.headers["retry-after"]) <= 900
    assert mock.scalar.await_count == 5
    mock.commit.assert_not_awaited()
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.anyio
async def test_success_resets_failures_but_cannot_clear_existing_lock() -> None:
    limiter = get_auth_rate_limiter()
    account = login_identifier("student@example.com")
    for _ in range(4):
        await limiter.login_failed(account)
    await limiter.login_succeeded(account)
    await limiter.login_failed(account)
    await limiter.check_login(account)
    for _ in range(4):
        await limiter.login_failed(account)
    await limiter.login_succeeded(account)
    with pytest.raises(RateLimitExceeded):
        await limiter.check_login(account)
    await limiter.check_login(login_identifier("other@example.com"))


@pytest.mark.anyio
async def test_concurrent_ip_requests_do_not_over_admit() -> None:
    limiter = get_auth_rate_limiter()

    async def attempt() -> bool:
        try:
            await limiter.check_ip("192.0.2.1")
            return True
        except RateLimitExceeded:
            return False

    assert sum(await asyncio.gather(*(attempt() for _ in range(140)))) == 120


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("2001:db8:0:0:0:0:0:1", "2001:db8::1"),
        ("::ffff:192.0.2.1", "192.0.2.1"),
        ("192.0.2.1", "192.0.2.1"),
        ("unparseable-client", "unknown"),
    ],
)
def test_ip_canonicalization(host: str, expected: str) -> None:
    request = Request({"type": "http", "client": (host, 1234), "headers": []})
    assert client_identifier(request) == expected


def test_email_normalization_and_no_raw_pii_in_account_key() -> None:
    assert login_identifier(" Student@Example.COM ") == login_identifier("student@example.com")
    assert "student" not in login_identifier("student@example.com")
    assert len(login_identifier("student@example.com")) == 64


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("peer", "expected"), [("192.0.2.1", "192.0.2.1"), ("127.0.0.1", "203.0.113.9")]
)
async def test_uvicorn_only_resolves_forwarded_ip_from_trusted_peer(
    peer: str, expected: str
) -> None:
    probe = FastAPI()

    @probe.get("/peer")
    async def read_peer(request: Request) -> dict[str, str]:
        return {"peer": client_identifier(request)}

    wrapped = ProxyHeadersMiddleware(cast(ASGI3Application, probe), trusted_hosts=["127.0.0.1"])
    async with AsyncClient(
        transport=ASGITransport(app=cast(ASGIApp, wrapped), client=(peer, 1234)),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/peer", headers={"X-Forwarded-For": "203.0.113.9"})
    assert response.json() == {"peer": expected}


@pytest.mark.parametrize(
    ("environment", "uri"),
    [
        ("production", "memory://"),
        ("production", "redis://localhost:6379/0"),
        ("production", ""),
        ("invalid", "memory://"),
        ("test", "http://localhost:6379"),
    ],
)
def test_invalid_or_unsafe_storage_configuration_fails_closed(
    environment: str, uri: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", uri)
    with pytest.raises(RateLimitUnavailable) as error:
        get_auth_rate_limiter()
    assert error.value.detail == "Rate limiting is unavailable."


def test_vercel_cannot_opt_into_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(RateLimitUnavailable):
        get_auth_rate_limiter()


@pytest.mark.anyio
async def test_storage_outage_is_sanitized_503_never_memory_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter = get_auth_rate_limiter()

    def unavailable(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("private Redis connection diagnostics")

    monkeypatch.setattr(limiter.backend, "hit", unavailable)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/auth/csrf")
        assert response.status_code == 503
        assert response.json() == {"detail": "Rate limiting is unavailable."}
        assert "diagnostics" not in response.text
        assert (await client.get("/openapi.json")).status_code == 200
        assert (await client.options("/api/auth/login")).status_code != 503


@pytest.mark.anyio
async def test_real_redis_connection_failure_is_sanitized_and_unrelated_routes_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reserve a local port without listening: no other service can accidentally accept it.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", f"redis://127.0.0.1:{port}/0")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/api/auth/csrf")
            assert response.status_code == 503
            assert response.json() == {"detail": "Rate limiting is unavailable."}
            assert response.headers.get_list("set-cookie") == []
            assert str(port) not in response.text
            assert (await client.get("/openapi.json")).status_code == 200


@pytest.mark.anyio
async def test_identity_check_cannot_silently_bypass_missing_middleware_context() -> None:
    request = Request({"type": "http", "headers": []})
    with pytest.raises(RateLimitUnavailable):
        await check_user_rate_limit(request, _user())


@pytest.mark.anyio
async def test_actual_http_window_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    _dependencies(None)
    now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    limiter = get_auth_rate_limiter()
    for _ in range(120):
        await limiter.check_ip("127.0.0.1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/auth/csrf")).status_code == 429
        now[0] += 61
        assert (await client.get("/api/auth/csrf")).status_code == 200
