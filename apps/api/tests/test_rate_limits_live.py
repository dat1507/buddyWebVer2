"""Opt-in live checks: run only against an operator-approved disposable Redis/database.

Set AUTH020_TEST_REDIS_URI and AUTH020_TEST_DATABASE_URL. Never target development/production
data: database acceptance commits test accounts and refresh sessions in the disposable database.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    RuntimeDatabaseSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import create_runtime_engine, get_database_session
from app.core.rate_limits import AuthRateLimiter, RateLimitExceeded, login_identifier
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def redis_pair() -> tuple[AuthRateLimiter, AuthRateLimiter]:
    uri = os.getenv("AUTH020_TEST_REDIS_URI")
    if not uri:
        pytest.skip("Set AUTH020_TEST_REDIS_URI for disposable live Redis acceptance.")
    prefix = f"vgu-buddy:auth020:test:{uuid4()}"
    return AuthRateLimiter(uri, prefix), AuthRateLimiter(uri, prefix)


@pytest.mark.anyio
@pytest.mark.parametrize(("role", "allowed"), [(UserRole.USER, 120), (UserRole.ADMIN, 60)])
async def test_live_redis_shared_role_quota_and_worker_restart(
    redis_pair: tuple[AuthRateLimiter, AuthRateLimiter],
    role: UserRole,
    allowed: int,
) -> None:
    first, second = redis_pair
    try:
        user = User(id=uuid4(), role=role)
        for _ in range(allowed // 2):
            await first.check_user(user)
            await second.check_user(user)
        with pytest.raises(RateLimitExceeded):
            await second.check_user(user)
        # A separate OS process cannot inherit either limiter's in-memory counters.
        child = subprocess.run(
            [
                sys.executable,
                "-c",
                "\n".join(
                    [
                        "import asyncio, os",
                        "from uuid import UUID",
                        "from app.core.rate_limits import AuthRateLimiter, RateLimitExceeded",
                        "from app.models import User, UserRole",
                        "async def main():",
                        "    limiter = AuthRateLimiter(os.environ['AUTH020_TEST_REDIS_URI'], "
                        "os.environ['AUTH020_TEST_CHILD_PREFIX'])",
                        "    user = User(id=UUID(os.environ['AUTH020_TEST_CHILD_ID']), "
                        "role=UserRole(os.environ['AUTH020_TEST_CHILD_ROLE']))",
                        "    try:",
                        "        await limiter.check_user(user)",
                        "        print('unexpected admission')",
                        "    except RateLimitExceeded:",
                        "        print('429')",
                        "    finally:",
                        "        limiter.close()",
                        "asyncio.run(main())",
                    ]
                ),
            ],
            env={
                **os.environ,
                "AUTH020_TEST_CHILD_PREFIX": first.prefix,
                "AUTH020_TEST_CHILD_ID": str(user.id),
                "AUTH020_TEST_CHILD_ROLE": role.value,
            },
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        assert child.stdout.strip() == "429"
        first.close()
        uri = os.environ["AUTH020_TEST_REDIS_URI"]
        restarted = AuthRateLimiter(uri, first.prefix)
        try:
            with pytest.raises(RateLimitExceeded):
                await restarted.check_user(user)
            user.id = uuid4()
            await restarted.check_user(user)
        finally:
            restarted.close()
    finally:
        first.close()
        second.close()


@pytest.mark.anyio
async def test_live_redis_concurrent_atomic_admission(
    redis_pair: tuple[AuthRateLimiter, AuthRateLimiter],
) -> None:
    first, second = redis_pair

    async def attempt(limiter: AuthRateLimiter) -> bool:
        try:
            await limiter.check_ip("192.0.2.1")
            return True
        except RateLimitExceeded:
            return False

    try:
        assert (
            sum(await asyncio.gather(*(attempt(first if i % 2 else second) for i in range(140))))
            == 120
        )
    finally:
        first.close()
        second.close()


@pytest.mark.anyio
async def test_live_redis_failed_logins_are_shared_without_ip_or_instance_bypass(
    redis_pair: tuple[AuthRateLimiter, AuthRateLimiter],
) -> None:
    first, second = redis_pair
    try:
        account = login_identifier("admin@example.com")
        for _ in range(2):
            await first.login_failed(account)
        for _ in range(3):
            await second.login_failed(account)
        with pytest.raises(RateLimitExceeded) as error:
            await first.check_login(account)
        assert error.value.headers is not None
        assert 898 <= int(error.value.headers["Retry-After"]) <= 900
        await second.login_succeeded(account)
        with pytest.raises(RateLimitExceeded):
            await second.check_login(account)
        await first.check_login(login_identifier("other@example.com"))
    finally:
        first.close()
        second.close()


@pytest.mark.anyio
async def test_live_database_cookie_login_current_session_refresh_health_and_lockout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("AUTH020_TEST_DATABASE_URL")
    redis_uri = os.getenv("AUTH020_TEST_REDIS_URI")
    if not database_url or not redis_uri:
        pytest.skip("Set disposable AUTH020_TEST_DATABASE_URL and AUTH020_TEST_REDIS_URI.")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", redis_uri)
    monkeypatch.setenv("RATE_LIMIT_KEY_PREFIX", f"vgu-buddy:auth020:test:{uuid4()}")
    engine = create_runtime_engine(RuntimeDatabaseSettings(url=SecretStr(database_url)))
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def database_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    token_settings = AuthTokenSettings(
        signing_key=SecretBytes(bytes(range(32))), secure_cookies=False
    )
    csrf_settings = CsrfSettings(
        signing_key=SecretBytes(bytes(reversed(range(32)))),
        secure_cookies=False,
        trusted_origins=("http://localhost:5173",),
    )
    app.dependency_overrides.clear()
    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: token_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    # Non-secret test credential for a database that must be destroyed after acceptance.
    password = "AUTH020 disposable test password"
    email = f"auth020-{uuid4()}@example.com"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            origin = {"Origin": "http://localhost:5173"}
            csrf = (await client.get("/api/auth/csrf")).json()["csrf_token"]
            headers = {**origin, CSRF_HEADER_NAME: csrf}
            registered = await client.post(
                "/api/auth/register",
                json={"email": email, "password": password, "consent": True},
                headers=headers,
            )
            assert registered.status_code == 201
            logged_in = await client.post(
                "/api/auth/login", json={"email": email, "password": password}, headers=headers
            )
            assert logged_in.status_code == 200
            assert logged_in.json()["user"]["role"] == "USER"
            assert (await client.get("/api/auth/me")).status_code == 200
            assert (await client.get("/api/health/database")).json() == {"status": "ok"}
            refreshed = await client.post(
                "/api/auth/refresh",
                headers={**origin, CSRF_HEADER_NAME: logged_in.json()["csrf_token"]},
            )
            assert refreshed.status_code == 200
            csrf = (await client.get("/api/auth/csrf")).json()["csrf_token"]
            headers = {**origin, CSRF_HEADER_NAME: csrf}
            for _ in range(5):
                wrong = await client.post(
                    "/api/auth/login", json={"email": email, "password": "wrong"}, headers=headers
                )
                assert wrong.status_code == 401
            locked = await client.post(
                "/api/auth/login", json={"email": email, "password": password}, headers=headers
            )
            assert locked.status_code == 429
            assert locked.headers.get_list("set-cookie") == []
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
