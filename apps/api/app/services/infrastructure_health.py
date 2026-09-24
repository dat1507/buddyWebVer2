"""Sanitized liveness/readiness checks for required infrastructure dependencies."""

from dataclasses import dataclass
from typing import Literal

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    DatabaseConfigurationError,
    EmailConfigurationError,
    RedisConfigurationError,
    StorageConfigurationError,
    get_email_provider_settings,
    get_email_verification_delivery_settings,
    get_storage_settings,
)
from app.core.database import get_session_factory
from app.core.redis import check_redis
from app.services.database_health import check_database

DependencyStatus = Literal["ok", "configured", "unconfigured", "unavailable"]


@dataclass(frozen=True)
class InfrastructureReadiness:
    """Fixed, non-sensitive dependency states for one readiness response."""

    database: DependencyStatus
    redis: DependencyStatus
    email: DependencyStatus
    storage: DependencyStatus

    @property
    def ready(self) -> bool:
        return (
            self.database == "ok"
            and self.redis == "ok"
            and self.email == "configured"
            and self.storage == "configured"
        )


async def _database_status() -> DependencyStatus:
    try:
        async with get_session_factory()() as session:
            return "ok" if await check_database(session) else "unavailable"
    except DatabaseConfigurationError:
        return "unconfigured"
    except (OSError, SQLAlchemyError):
        return "unavailable"


async def _redis_status() -> DependencyStatus:
    try:
        return "ok" if await check_redis() else "unavailable"
    except RedisConfigurationError:
        return "unconfigured"
    except (OSError, RedisError):
        return "unavailable"


def _email_status() -> DependencyStatus:
    try:
        get_email_provider_settings()
        get_email_verification_delivery_settings()
        return "configured"
    except EmailConfigurationError:
        return "unconfigured"


def _storage_status() -> DependencyStatus:
    try:
        get_storage_settings()
        return "configured"
    except StorageConfigurationError:
        return "unconfigured"


async def check_infrastructure_readiness() -> InfrastructureReadiness:
    """Check every dependency even when another is unavailable."""
    return InfrastructureReadiness(
        database=await _database_status(),
        redis=await _redis_status(),
        email=_email_status(),
        storage=_storage_status(),
    )
