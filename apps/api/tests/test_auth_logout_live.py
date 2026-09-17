"""Opt-in AUTH-024 acceptance against disposable PostgreSQL and Redis only.

Set AUTH024_TEST_DATABASE_URL (least-privilege runtime role) and AUTH024_TEST_REDIS_URI.
These checks commit test accounts/session rows; never point them at development/production data.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes, SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    RuntimeDatabaseSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import create_runtime_engine, get_database_session
from app.main import app
from app.models import RefreshSession, User, UserRole
from app.services.csrf import CSRF_HEADER_NAME
from app.services.refresh_sessions import (
    RefreshSessionError,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)
from app.services.tokens import (
    TokenPair,
    access_cookie_name,
    create_token_pair,
    refresh_cookie_name,
    verify_refresh_token,
)

ORIGIN = {"Origin": "http://localhost:5173"}
TOKEN_SETTINGS = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)
CSRF_SETTINGS = CsrfSettings(
    signing_key=SecretBytes(bytes(reversed(range(32)))),
    secure_cookies=False,
    trusted_origins=(ORIGIN["Origin"],),
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def live_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    database_url = os.getenv("AUTH024_TEST_DATABASE_URL")
    redis_uri = os.getenv("AUTH024_TEST_REDIS_URI")
    if not database_url or not redis_uri:
        pytest.skip("Set disposable AUTH024_TEST_DATABASE_URL and AUTH024_TEST_REDIS_URI.")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", redis_uri)
    monkeypatch.setenv("RATE_LIMIT_KEY_PREFIX", f"vgu-buddy:auth024:test:{uuid4()}")
    engine = create_runtime_engine(RuntimeDatabaseSettings(url=SecretStr(database_url)))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def database_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: TOKEN_SETTINGS
    app.dependency_overrides[get_csrf_settings] = lambda: CSRF_SETTINGS
    try:
        yield factory
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_live_logout_cookie_cleanup_replay_and_other_family_isolation(
    live_factory: async_sessionmaker[AsyncSession], role: UserRole
) -> None:
    # Public test credential for disposable acceptance only, not a production secret.
    email = f"auth024-{uuid4()}@example.com"
    password = "AUTH024 disposable test password"
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as first,
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as second,
    ):
        preauth = (await first.get("/api/auth/csrf")).json()["csrf_token"]
        headers = {**ORIGIN, CSRF_HEADER_NAME: preauth}
        assert (
            await first.post(
                "/api/auth/register",
                json={"email": email, "password": password, "consent": True},
                headers=headers,
            )
        ).status_code == 201
        async with live_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            user.role = role
            user.email_verified = False
            await session.commit()
        logged_in = await first.post(
            "/api/auth/login", json={"email": email, "password": password}, headers=headers
        )
        assert logged_in.status_code == 200
        assert logged_in.json()["user"]["role"] == role.value
        original_refresh = first.cookies[refresh_cookie_name(TOKEN_SETTINGS)]
        claims = verify_refresh_token(original_refresh, TOKEN_SETTINGS)
        other_preauth = (await second.get("/api/auth/csrf")).json()["csrf_token"]
        other_login = await second.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            headers={**ORIGIN, CSRF_HEADER_NAME: other_preauth},
        )
        assert other_login.status_code == 200
        other_claims = verify_refresh_token(
            second.cookies[refresh_cookie_name(TOKEN_SETTINGS)], TOKEN_SETTINGS
        )
        assert claims.session_id != other_claims.session_id
        bad_logout = await first.post("/api/auth/logout", headers=ORIGIN)
        assert bad_logout.status_code == 403
        assert bad_logout.headers.get_list("set-cookie") == []
        refreshed = await first.post(
            "/api/auth/refresh",
            headers={**ORIGIN, CSRF_HEADER_NAME: logged_in.json()["csrf_token"]},
        )
        assert refreshed.status_code == 200
        rotated_refresh = first.cookies[refresh_cookie_name(TOKEN_SETTINGS)]
        copied_access = first.cookies[access_cookie_name(TOKEN_SETTINGS)]
        latest_cookies = dict(first.cookies)
        # Logout of a signed stale JTI must revoke the latest member of the same family.
        first.cookies.set(
            refresh_cookie_name(TOKEN_SETTINGS),
            original_refresh,
            domain="testserver.local",
            path="/",
        )
        logout_headers = {**ORIGIN, CSRF_HEADER_NAME: refreshed.json()["csrf_token"]}
        logged_out = await first.post("/api/auth/logout", headers=logout_headers)
        assert logged_out.status_code == 204 and logged_out.content == b""
        assert len(logged_out.headers.get_list("set-cookie")) == 3
        assert not first.cookies
        assert (await first.get("/api/auth/me")).status_code == 401
        assert (await first.get("/api/health/database")).json() == {"status": "ok"}
        async with live_factory() as session:
            stored = await session.get(RefreshSession, claims.session_id)
            other = await session.get(RefreshSession, other_claims.session_id)
            assert stored is not None and stored.revoked_at is not None
            assert (
                stored.refresh_token_id
                == verify_refresh_token(rotated_refresh, TOKEN_SETTINGS).token_id
            )
            assert other is not None and other.revoked_at is None
        for replay in (original_refresh, rotated_refresh):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
                cookies={**latest_cookies, refresh_cookie_name(TOKEN_SETTINGS): replay},
            ) as attacker:
                rejected = await attacker.post("/api/auth/refresh", headers=logout_headers)
                assert rejected.status_code == 401
                assert rejected.headers.get_list("set-cookie") == []
                repeat = await attacker.post("/api/auth/logout", headers=logout_headers)
                assert repeat.status_code == 204
        other_refreshed = await second.post(
            "/api/auth/refresh",
            headers={**ORIGIN, CSRF_HEADER_NAME: other_login.json()["csrf_token"]},
        )
        assert other_refreshed.status_code == 200
        # Existing AUTH-017 verifies short-lived access JWT + User, not refresh-family state.
        # Explicitly pin this residual TTL; do not falsely claim immediate access-token revocation.
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies={access_cookie_name(TOKEN_SETTINGS): copied_access},
        ) as copied:
            assert (await copied.get("/api/auth/me")).status_code == 200
        # Inactive accounts must also be able to revoke their own session (no User lookup gate).
        async with live_factory() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            user.is_active = False
            await session.commit()
        assert (
            await second.post(
                "/api/auth/logout",
                headers={**ORIGIN, CSRF_HEADER_NAME: other_refreshed.json()["csrf_token"]},
            )
        ).status_code == 204
        preauth = (await first.get("/api/auth/csrf")).json()["csrf_token"]
        assert (
            await first.post("/api/auth/logout", headers={**ORIGIN, CSRF_HEADER_NAME: preauth})
        ).status_code == 204


async def _new_family(factory: async_sessionmaker[AsyncSession]) -> tuple[User, TokenPair]:
    async with factory() as session:
        user = User(
            email=f"auth024-race-{uuid4()}@example.com",
            password_hash="$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6",
            role=UserRole.USER,
            is_active=True,
            email_verified=False,
        )
        session.add(user)
        await session.flush()
        pair = create_token_pair(user.id, user.role, TOKEN_SETTINGS)
        await create_refresh_session(session, user, pair)
        await session.commit()
        return user, pair


async def _wait_for_real_row_lock(factory: async_sessionmaker[AsyncSession], pid: int) -> None:
    async with asyncio.timeout(5), factory() as observer:
        while True:
            wait_type = await observer.scalar(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid}
            )
            if wait_type == "Lock":
                return
            # End the stats snapshot transaction before observing another backend again.
            await observer.rollback()
            await asyncio.sleep(0.02)


@pytest.mark.anyio
async def test_live_revocation_cannot_mutate_a_different_owners_family(
    live_factory: async_sessionmaker[AsyncSession],
) -> None:
    user, pair = await _new_family(live_factory)
    async with live_factory() as session:
        await revoke_refresh_session(session, pair.session_id, uuid4())
        await session.commit()
    async with live_factory() as session:
        row = await session.get(RefreshSession, pair.session_id)
        assert row is not None and row.revoked_at is None
        await revoke_refresh_session(session, pair.session_id, user.id)
        await session.commit()
    async with live_factory() as session:
        row = await session.get(RefreshSession, pair.session_id)
        assert row is not None and row.revoked_at is not None


@pytest.mark.anyio
@pytest.mark.parametrize("order", ["refresh-first", "logout-first"])
async def test_live_refresh_logout_race_uses_real_postgresql_row_lock(
    live_factory: async_sessionmaker[AsyncSession], order: str
) -> None:
    user, pair = await _new_family(live_factory)
    claims = verify_refresh_token(pair.refresh_token, TOKEN_SETTINGS)
    started: asyncio.Future[int] = asyncio.get_running_loop().create_future()

    async def competitor() -> None:
        async with live_factory() as session:
            pid = await session.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            started.set_result(pid)
            if order == "refresh-first":
                await revoke_refresh_session(session, pair.session_id, user.id)
                await session.commit()
            else:
                with pytest.raises(RefreshSessionError, match="invalid or expired"):
                    await rotate_refresh_session(
                        session, pair.refresh_token, claims, TOKEN_SETTINGS
                    )
                await session.rollback()

    async with live_factory() as holder:
        if order == "refresh-first":
            rotated = await rotate_refresh_session(
                holder, pair.refresh_token, claims, TOKEN_SETTINGS
            )
            candidate = rotated.token_pair
        else:
            await revoke_refresh_session(holder, pair.session_id, user.id)
            candidate = pair
        task = asyncio.create_task(competitor())
        try:
            pid = await asyncio.wait_for(started, timeout=5)
            await _wait_for_real_row_lock(live_factory, pid)
            assert not task.done()
            await holder.commit()
            await asyncio.wait_for(task, timeout=5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    async with live_factory() as session:
        stored = await session.get(RefreshSession, pair.session_id)
        assert stored is not None and stored.revoked_at is not None
        with pytest.raises(RefreshSessionError, match="invalid or expired"):
            await rotate_refresh_session(
                session,
                candidate.refresh_token,
                verify_refresh_token(candidate.refresh_token, TOKEN_SETTINGS),
                TOKEN_SETTINGS,
            )
        await session.rollback()
