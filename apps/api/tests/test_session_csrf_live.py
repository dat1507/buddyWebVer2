"""Opt-in AUTH-021 acceptance with a disposable, loopback PostgreSQL database.

Set AUTH021_TEST_DATABASE_URL to the least-privilege vgu_buddy_runtime role in
auth021_acceptance. Never use a populated development/production database.
The enabled memory limiter is explicitly test-only; shared Redis has separate live tests.
"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes, SecretStr
from sqlalchemy import select
from sqlalchemy.engine import make_url
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
from app.services.csrf import CSRF_HEADER_NAME, csrf_cookie_name
from app.services.tokens import (
    access_cookie_name,
    create_token_pair,
    refresh_cookie_name,
    verify_refresh_token,
)

ORIGIN = {"Origin": "http://localhost:5173"}
TOKEN = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)
CSRF = CsrfSettings(
    signing_key=SecretBytes(bytes(reversed(range(32)))),
    secure_cookies=False,
    trusted_origins=(ORIGIN["Origin"],),
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def live_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    raw_url = os.getenv("AUTH021_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set AUTH021_TEST_DATABASE_URL for disposable local PostgreSQL acceptance.")
    url = make_url(raw_url)
    if (
        url.host != "127.0.0.1"
        or url.database != "auth021_acceptance"
        or url.username != "vgu_buddy_runtime"
    ):
        pytest.fail("AUTH021 requires the isolated loopback auth021_acceptance runtime database.")
    engine = create_runtime_engine(RuntimeDatabaseSettings(url=SecretStr(raw_url)))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def database() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: TOKEN
    app.dependency_overrides[get_csrf_settings] = lambda: CSRF
    try:
        yield factory
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_live_registration_login_reload_expired_access_refresh_logout(
    live_factory: async_sessionmaker[AsyncSession], role: UserRole
) -> None:
    email = f"auth021-{uuid4()}@example.com"
    # Public test fixture, only used by this isolated acceptance database.
    password = "AUTH021 disposable test password"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        preauth = (await client.get("/api/auth/csrf")).json()["csrf_token"]
        registration = {"email": email, "password": password, "consent": True}
        assert (
            await client.post(
                "/api/auth/register",
                json=registration,
                headers={**ORIGIN, CSRF_HEADER_NAME: preauth},
            )
        ).status_code == 201
        async with live_factory() as database:
            account = await database.scalar(select(User).where(User.email == email))
            assert account is not None and account.role is UserRole.USER
            assert account.password_hash != password and account.email_verified is False
            account.role = role
            await database.commit()
            user_id = account.id
        assert (
            await client.post(
                "/api/auth/register",
                json=registration,
                headers={**ORIGIN, CSRF_HEADER_NAME: preauth},
            )
        ).status_code == 409
        login = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            headers={**ORIGIN, CSRF_HEADER_NAME: preauth},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == role.value
        original_refresh = client.cookies[refresh_cookie_name(TOKEN)]
        claims = verify_refresh_token(original_refresh, TOKEN)
        # Reload loses readable JSON; cookies alone recover the same valid session CSRF.
        recovery = await client.get("/api/auth/csrf/session", headers=ORIGIN)
        assert recovery.status_code == 200 and "set-cookie" not in recovery.headers
        assert recovery.headers["cache-control"] == "no-store"
        assert (await client.get("/api/auth/me")).json()["role"] == role.value
        old_access = create_token_pair(
            user_id,
            role,
            TOKEN,
            session_id=claims.session_id,
            now=datetime.now(UTC) - timedelta(minutes=20),
        )
        client.cookies.set(
            access_cookie_name(TOKEN), old_access.access_token, domain="testserver.local", path="/"
        )
        assert (await client.get("/api/auth/me")).status_code == 401
        recovered = await client.get("/api/auth/csrf/session", headers=ORIGIN)
        assert recovered.status_code == 200
        refresh = await client.post(
            "/api/auth/refresh",
            headers={**ORIGIN, CSRF_HEADER_NAME: recovered.json()["csrf_token"]},
        )
        assert refresh.status_code == 200
        current_refresh = client.cookies[refresh_cookie_name(TOKEN)]
        current_claims = verify_refresh_token(current_refresh, TOKEN)
        assert (
            current_claims.session_id == claims.session_id
            and current_claims.token_id != claims.token_id
        )
        cookies_before_logout = dict(client.cookies)
        logout = await client.post(
            "/api/auth/logout", headers={**ORIGIN, CSRF_HEADER_NAME: refresh.json()["csrf_token"]}
        )
        assert logout.status_code == 204 and len(client.cookies) == 0
        async with live_factory() as database:
            family = await database.get(RefreshSession, claims.session_id)
            assert family is not None and family.revoked_at is not None
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies=cookies_before_logout,
        ) as replay:
            assert (await replay.get("/api/auth/csrf/session", headers=ORIGIN)).status_code == 401
            assert (
                await replay.post(
                    "/api/auth/refresh",
                    headers={**ORIGIN, CSRF_HEADER_NAME: refresh.json()["csrf_token"]},
                )
            ).status_code == 401
        # Anonymous repeat cleanup obtains its own pre-auth context.
        cleanup = (await client.get("/api/auth/csrf")).json()["csrf_token"]
        assert (
            await client.post("/api/auth/logout", headers={**ORIGIN, CSRF_HEADER_NAME: cleanup})
        ).status_code == 204


@pytest.mark.anyio
async def test_live_recovery_does_not_cross_families_or_bypass_origin(
    live_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = f"auth021-security-{uuid4()}@example.com"
    password = "AUTH021 disposable test password"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as first:
        token = (await first.get("/api/auth/csrf")).json()["csrf_token"]
        assert (
            await first.post(
                "/api/auth/register",
                json={"email": email, "password": password, "consent": True},
                headers={**ORIGIN, CSRF_HEADER_NAME: token},
            )
        ).status_code == 201
        assert (
            await first.post(
                "/api/auth/login",
                json={"email": email, "password": password},
                headers={**ORIGIN, CSRF_HEADER_NAME: token},
            )
        ).status_code == 200
        recovered = (await first.get("/api/auth/csrf/session", headers=ORIGIN)).json()["csrf_token"]
        assert (
            await first.get(
                "/api/auth/csrf/session", headers={"Origin": "https://attacker.example"}
            )
        ).status_code == 403
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as second:
            preauth = (await second.get("/api/auth/csrf")).json()["csrf_token"]
            assert (
                await second.post(
                    "/api/auth/login",
                    json={"email": email, "password": password},
                    headers={**ORIGIN, CSRF_HEADER_NAME: preauth},
                )
            ).status_code == 200
            # Matching header/cookie from A still cannot act on B's verified refresh family.
            second.cookies.set(
                csrf_cookie_name(CSRF), recovered, domain="testserver.local", path="/"
            )
            assert (
                await second.post(
                    "/api/auth/logout", headers={**ORIGIN, CSRF_HEADER_NAME: recovered}
                )
            ).status_code == 403
