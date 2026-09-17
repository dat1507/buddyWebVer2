"""Give each test fresh, enabled local counters; never disable the rate limiter."""

from collections.abc import Iterator

import pytest

from app.core.rate_limits import close_auth_rate_limiter


@pytest.fixture(autouse=True)
def isolated_rate_limit_storage(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    close_auth_rate_limiter()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    yield
    close_auth_rate_limiter()
