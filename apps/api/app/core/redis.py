"""Process-wide async Redis boundary for readiness and future coordination."""

from collections.abc import Awaitable
from functools import lru_cache
from typing import cast

from redis.asyncio import Redis

from app.core.config import get_redis_settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Create one lazy connection pool without exposing its server-only URL."""
    settings = get_redis_settings()
    return Redis.from_url(
        settings.url.get_secret_value(),
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


async def check_redis() -> bool:
    """Perform a real PING; redis-py reconnects after transient outages."""
    ping = cast(Awaitable[bool], get_redis_client().ping())
    return bool(await ping)


async def close_redis_client() -> None:
    """Close only an initialized pool and clear process-local cached configuration."""
    if get_redis_client.cache_info().currsize:
        await get_redis_client().aclose()
    get_redis_client.cache_clear()
    get_redis_settings.cache_clear()
