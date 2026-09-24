"""AUTH-020: explicit ASGI/dependency adapter over SlowAPI's public limits backend.

Do not use SlowAPI's route discovery here: included FastAPI routers can otherwise be exempt.
Redis I/O runs in the thread pool, never synchronously on the ASGI event loop.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import time
from collections.abc import Callable
from functools import lru_cache
from math import ceil
from typing import TypeVar, cast
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from limits import RateLimitItem, RateLimitItemPerMinute
from limits.storage import RedisStorage
from limits.strategies import RateLimiter
from redis import Redis
from slowapi import Limiter
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Receive, Scope, Send

from app.models import User, UserRole
from app.services.auth import EmailValidationError, canonicalize_email

USER_REQUESTS_PER_MINUTE = 120
ADMIN_REQUESTS_PER_MINUTE = 60
FAILED_LOGIN_THRESHOLD = 5
LOGIN_LOCKOUT_SECONDS = 900
AUTH_ENDPOINTS = frozenset(
    {
        ("GET", "/api/auth/csrf"),
        ("GET", "/api/auth/csrf/session"),
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/refresh"),
        ("POST", "/api/auth/logout"),
        ("POST", "/api/auth/email/change"),
        ("POST", "/api/auth/email-verification/request"),
        ("POST", "/api/auth/email-verification/confirm"),
    }
)
_NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
_T = TypeVar("_T")


class RateLimitUnavailable(HTTPException):
    """Fail closed without exposing URLs, credentials or storage diagnostics."""

    def __init__(self) -> None:
        super().__init__(503, "Rate limiting is unavailable.", headers=_NO_STORE)


class RateLimitExceeded(HTTPException):
    """Same response for IP, identity and login-lockout exhaustion."""

    def __init__(self, reset_at: float) -> None:
        super().__init__(
            429,
            "Too many requests. Please try again later.",
            headers={**_NO_STORE, "Retry-After": str(max(1, ceil(reset_at - time.time())))},
        )


def client_identifier(request: Request) -> str:
    """Only use the transport peer (or Uvicorn's trusted-proxy-resolved peer).

    Never read Forwarded/X-Forwarded-For/X-Real-IP here. Unknown peers share a bucket.
    Equivalent IPv6 forms and IPv4-mapped IPv6 cannot create independent buckets.
    """
    try:
        address = ipaddress.ip_address(request.client.host if request.client else "")
    except ValueError:
        return "unknown"
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return address.compressed.split("%", maxsplit=1)[0]
    return str(address)


def login_identifier(email: str) -> str:
    """Do not store raw email/password/token material in limiter keys."""
    try:
        canonical = canonicalize_email(email)
    except EmailValidationError:
        canonical = email.strip().casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuthRateLimiter:
    """Request counters and account lockout share the same private, expiring storage."""

    def __init__(self, storage_uri: str, prefix: str) -> None:
        options: dict[str, object] = {"wrap_exceptions": True}
        if storage_uri != "memory://":
            options.update(socket_connect_timeout=2, socket_timeout=2, max_connections=50)
        self.extension = Limiter(
            key_func=client_identifier,
            storage_uri=storage_uri,
            # SlowAPI annotates all values as str, although limits accepts bool/int options.
            storage_options=cast(dict[str, str], options),
            strategy="fixed-window",
            auto_check=False,
            swallow_errors=False,
            in_memory_fallback_enabled=False,
        )
        self.backend: RateLimiter = self.extension.limiter
        self.prefix = prefix

    def _hit(self, limit: RateLimitItem, identifier: str) -> None:
        if not self.backend.hit(limit, self.prefix, identifier):
            stats = self.backend.get_window_stats(limit, self.prefix, identifier)
            raise RateLimitExceeded(stats.reset_time)

    async def _call(self, operation: Callable[[], _T]) -> _T:
        try:
            return await run_in_threadpool(operation)
        except RateLimitExceeded:
            raise
        except Exception:
            # Never fall back to a process-local counter or log the storage URI.
            raise RateLimitUnavailable() from None

    async def check_ip(self, identifier: str) -> None:
        await self._call(
            lambda: self._hit(RateLimitItemPerMinute(USER_REQUESTS_PER_MINUTE), f"ip:{identifier}")
        )

    async def check_user(self, user: User) -> None:
        amount = (
            ADMIN_REQUESTS_PER_MINUTE if user.role is UserRole.ADMIN else USER_REQUESTS_PER_MINUTE
        )
        await self._call(lambda: self._hit(RateLimitItemPerMinute(amount), f"user:{user.id}"))

    def _login_keys(self, identifier: str) -> tuple[str, str]:
        return f"{self.prefix}:failed:{identifier}", f"{self.prefix}:locked:{identifier}"

    def _ensure_login_unlocked(self, identifier: str) -> None:
        failed_key, locked_key = self._login_keys(identifier)
        storage = self.backend.storage
        if storage.get(locked_key):
            raise RateLimitExceeded(storage.get_expiry(locked_key))
        if storage.get(failed_key) >= FAILED_LOGIN_THRESHOLD:
            # Close the gap between the fifth atomic failure increment and lock creation.
            storage.incr(locked_key, LOGIN_LOCKOUT_SECONDS)
            raise RateLimitExceeded(storage.get_expiry(locked_key))

    async def check_login(self, identifier: str) -> None:
        await self._call(lambda: self._ensure_login_unlocked(identifier))

    async def login_failed(self, identifier: str) -> None:
        def record() -> None:
            failed_key, locked_key = self._login_keys(identifier)
            storage = self.backend.storage
            count = storage.incr(failed_key, LOGIN_LOCKOUT_SECONDS)
            if count >= FAILED_LOGIN_THRESHOLD:
                # INCR + initial expiry is atomic in Redis. Subsequent failures do not extend TTL.
                storage.incr(locked_key, LOGIN_LOCKOUT_SECONDS)
                storage.clear(failed_key)

        await self._call(record)

    async def login_succeeded(self, identifier: str) -> None:
        # An in-flight success may reset failures, but must never clear an already active lock.
        failed_key, _locked_key = self._login_keys(identifier)
        await self._call(lambda: self.backend.storage.clear(failed_key))

    def close(self) -> None:
        if isinstance(self.backend.storage, RedisStorage):
            cast(Redis, self.backend.storage.get_connection()).close()


@lru_cache(maxsize=1)
def get_auth_rate_limiter() -> AuthRateLimiter:
    """Production is the default; only explicit local/test mode permits memory."""
    environment = os.getenv("APP_ENV", "production")
    uri = os.getenv("RATE_LIMIT_STORAGE_URI", "")
    try:
        if environment not in {"local", "test", "production"}:
            raise ValueError
        prefix = os.getenv("RATE_LIMIT_KEY_PREFIX", f"vgu-buddy:{environment}:auth:v1")
        if not re.fullmatch(r"[A-Za-z0-9:_-]{1,100}", prefix):
            raise ValueError
        if f":{environment}:" not in prefix:
            raise ValueError
        if uri == "memory://":
            if environment == "production" or os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
                raise ValueError
        else:
            parsed = urlsplit(uri)
            if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
                raise ValueError
            _port = parsed.port
            if environment == "production" and parsed.scheme != "rediss":
                raise ValueError
        return AuthRateLimiter(uri, prefix)
    except Exception:
        raise RateLimitUnavailable() from None


def close_auth_rate_limiter() -> None:
    """Close only an already initialized limiter; never reset shared Redis counters."""
    if get_auth_rate_limiter.cache_info().currsize:
        get_auth_rate_limiter().close()
    get_auth_rate_limiter.cache_clear()


async def check_user_rate_limit(request: Request, user: User) -> None:
    """Use the current persisted role; do not authenticate again just to choose a quota."""
    limiter = getattr(request.state, "auth_rate_limiter", None)
    if not isinstance(limiter, AuthRateLimiter):
        raise RateLimitUnavailable()
    await limiter.check_user(user)


class AuthRateLimitMiddleware:
    """Limit scoped auth traffic before body validation, CSRF, bcrypt or database work."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        root_path = scope.get("root_path", "")
        if root_path and path.startswith(f"{root_path}/"):
            path = path[len(root_path) :]
        if (scope["method"], path.rstrip("/")) not in AUTH_ENDPOINTS:
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        try:
            limiter = get_auth_rate_limiter()
            await limiter.check_ip(client_identifier(request))
        except (RateLimitExceeded, RateLimitUnavailable) as error:
            response = JSONResponse(
                status_code=error.status_code,
                content={"detail": error.detail},
                headers=error.headers,
            )
            await response(scope, receive, send)
            return
        request.state.auth_rate_limiter = limiter
        await self.app(scope, receive, send)
