"""Async SQLAlchemy connection and session boundary."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Final

from pydantic import SecretStr
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import (
    APP_ENV_VARIABLE,
    DatabaseConfigurationError,
    MigrationDatabaseSettings,
    RuntimeDatabaseSettings,
    get_runtime_database_settings,
)

APPLICATION_SCHEMA: Final = "app_private"
TRANSACTION_POOLER_PORT: Final = 6543
_ALLOWED_SSL_MODES: Final = frozenset({"require", "verify-ca", "verify-full"})
_LOCAL_DATABASE_HOSTS: Final = frozenset({"127.0.0.1", "::1", "localhost"})
_LOCAL_COMPOSE_DATABASE_HOST: Final = "postgres"
_SUPPORTED_DRIVERS: Final = frozenset({"postgres", "postgresql", "postgresql+asyncpg"})


def _as_async_postgres_url(
    secret: SecretStr, *, allow_transaction_pooler: bool
) -> URL:
    try:
        url = make_url(secret.get_secret_value())
    except ArgumentError as exc:
        raise DatabaseConfigurationError("Database URL is not a valid SQLAlchemy URL.") from exc

    if url.drivername not in _SUPPORTED_DRIVERS:
        raise DatabaseConfigurationError("Database URL must use PostgreSQL with asyncpg.")
    if not url.username or url.password is None or not url.host or not url.database:
        raise DatabaseConfigurationError(
            "Database URL must include username, password, host, and database name."
        )
    if not allow_transaction_pooler and url.port == TRANSACTION_POOLER_PORT:
        raise DatabaseConfigurationError(
            "Alembic requires the direct Supabase connection, not transaction-pooler port 6543."
        )

    query = dict(url.query)
    libpq_ssl_mode = query.pop("sslmode", None)
    asyncpg_ssl_mode = query.get("ssl")
    if (
        libpq_ssl_mode is not None
        and asyncpg_ssl_mode is not None
        and libpq_ssl_mode != asyncpg_ssl_mode
    ):
        raise DatabaseConfigurationError(
            "Database URL cannot define conflicting sslmode and ssl values."
        )

    ssl_mode = libpq_ssl_mode or asyncpg_ssl_mode
    is_local = url.host in _LOCAL_DATABASE_HOSTS or (
        os.getenv(APP_ENV_VARIABLE, "production").strip().lower() == "local"
        and url.host == _LOCAL_COMPOSE_DATABASE_HOST
    )
    if ssl_mode is None and is_local:
        ssl_mode = "disable"
    elif ssl_mode is None:
        ssl_mode = "require"
    elif ssl_mode not in _ALLOWED_SSL_MODES and not (
        is_local and ssl_mode == "disable"
    ):
        raise DatabaseConfigurationError(
            "Remote database URLs must require TLS with sslmode=require, verify-ca, "
            "or verify-full."
        )

    # SQLAlchemy expands URL query values into asyncpg.connect keyword arguments.
    # asyncpg accepts ``ssl`` here, while ``sslmode`` is only valid inside its raw DSN.
    query["ssl"] = ssl_mode

    if url.port == TRANSACTION_POOLER_PORT:
        query["prepared_statement_cache_size"] = "0"

    return url.set(drivername="postgresql+asyncpg", query=query)


def runtime_database_url(settings: RuntimeDatabaseSettings) -> URL:
    """Normalize the runtime URL for direct, session, or transaction pooling."""
    return _as_async_postgres_url(settings.url, allow_transaction_pooler=True)


def migration_database_url(settings: MigrationDatabaseSettings) -> URL:
    """Normalize the privileged direct URL used by Alembic."""
    return _as_async_postgres_url(settings.url, allow_transaction_pooler=False)


def create_runtime_engine(settings: RuntimeDatabaseSettings) -> AsyncEngine:
    """Create a bounded engine appropriate for the selected Supabase endpoint."""
    url = runtime_database_url(settings)
    if url.port == TRANSACTION_POOLER_PORT:
        return create_async_engine(
            url,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},
        )

    return create_async_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=300,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_runtime_engine() -> AsyncEngine:
    """Create one engine for the FastAPI process, never one per request."""
    return create_runtime_engine(get_runtime_database_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory."""
    return async_sessionmaker(get_runtime_engine(), expire_on_commit=False, autoflush=False)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped session and always release it."""
    async with get_session_factory()() as session:
        yield session


async def dispose_database_engine() -> None:
    """Release pooled connections during application shutdown."""
    if get_runtime_engine.cache_info().currsize:
        await get_runtime_engine().dispose()
    get_session_factory.cache_clear()
    get_runtime_engine.cache_clear()
