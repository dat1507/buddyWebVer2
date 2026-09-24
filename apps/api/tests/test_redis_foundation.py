"""OPS-001 shared async Redis configuration and reconnect behavior."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr, ValidationError
from redis.exceptions import RedisError

import app.core.redis as redis_boundary
from app.core.config import (
    RedisConfigurationError,
    RedisSettings,
    get_redis_settings,
)


@pytest.fixture(autouse=True)
def clear_redis_caches() -> Iterator[None]:
    redis_boundary.get_redis_client.cache_clear()
    get_redis_settings.cache_clear()
    yield
    redis_boundary.get_redis_client.cache_clear()
    get_redis_settings.cache_clear()


def test_local_redis_configuration_is_namespaced_and_secret_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_url = "redis://worker:private-password@127.0.0.1:6379/0"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", private_url)
    monkeypatch.setenv("REDIS_KEY_PREFIX", "vgu-buddy:local:ops:v1")

    settings = get_redis_settings()

    assert settings.environment == "local"
    assert settings.key_prefix == "vgu-buddy:local:ops:v1"
    assert private_url not in repr(settings)
    assert "private-password" not in repr(settings)


@pytest.mark.parametrize(
    ("environment", "url", "prefix"),
    [
        ("production", "redis://cache.example.test:6379/0", "vgu-buddy:production:ops:v1"),
        ("production", "rediss://cache.example.test:6379/0", "vgu-buddy:local:ops:v1"),
        ("local", "http://127.0.0.1:6379/0", "vgu-buddy:local:ops:v1"),
    ],
)
def test_unsafe_redis_settings_fail_closed(environment: str, url: str, prefix: str) -> None:
    with pytest.raises(ValidationError):
        RedisSettings(environment=environment, url=SecretStr(url), key_prefix=prefix)  # type: ignore[arg-type]


def test_production_requires_configured_tls_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(RedisConfigurationError):
        get_redis_settings()

    monkeypatch.setenv("REDIS_URL", "rediss://cache.example.test:6380/0")
    monkeypatch.setenv("REDIS_KEY_PREFIX", "vgu-buddy:production:ops:v1")
    get_redis_settings.cache_clear()
    assert get_redis_settings().environment == "production"


@pytest.mark.anyio
async def test_async_client_recovers_with_the_same_pool_after_transient_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("REDIS_KEY_PREFIX", "vgu-buddy:test:ops:v1")
    client = Mock()
    client.ping = AsyncMock(side_effect=[RedisError("private endpoint details"), True])
    client.aclose = AsyncMock()
    from_url = Mock(return_value=client)
    monkeypatch.setattr("app.core.redis.Redis.from_url", from_url)

    with pytest.raises(RedisError) as error:
        await redis_boundary.check_redis()
    assert "private endpoint details" in str(error.value)
    assert await redis_boundary.check_redis() is True
    assert from_url.call_count == 1

    await redis_boundary.close_redis_client()
    client.aclose.assert_awaited_once()
