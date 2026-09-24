"""Tests for the server-only SQLAlchemy database boundary."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy.pool import NullPool

from app.core.config import (
    MIGRATION_URL_VARIABLE,
    RUNTIME_URL_VARIABLE,
    DatabaseConfigurationError,
    MigrationDatabaseSettings,
    RuntimeDatabaseSettings,
    get_migration_database_settings,
    get_runtime_database_settings,
)
from app.core.database import (
    create_runtime_engine,
    migration_database_url,
    runtime_database_url,
)


def _database_test_url(
    role: str, *, host: str = "db.example.test", port: int = 5432
) -> str:
    parts = (
        "postgresql://",
        role,
        ":",
        "test-only-credential",
        "@",
        host,
        f":{port}/postgres",
    )
    return "".join(parts)


def test_runtime_and_migration_credentials_are_loaded_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_URL_VARIABLE, _database_test_url("runtime-user"))
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _database_test_url("migration-user"))
    get_runtime_database_settings.cache_clear()
    get_migration_database_settings.cache_clear()

    try:
        runtime_settings = get_runtime_database_settings()
        migration_settings = get_migration_database_settings()
    finally:
        get_runtime_database_settings.cache_clear()
        get_migration_database_settings.cache_clear()

    assert runtime_settings.url != migration_settings.url
    assert "test-only-credential" not in repr(runtime_settings)
    assert "test-only-credential" not in repr(migration_settings)


def test_missing_runtime_credential_fails_without_a_secret_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(RUNTIME_URL_VARIABLE, raising=False)
    get_runtime_database_settings.cache_clear()

    with pytest.raises(DatabaseConfigurationError, match=RUNTIME_URL_VARIABLE):
        get_runtime_database_settings()

    get_runtime_database_settings.cache_clear()


def test_remote_runtime_url_is_async_and_requires_tls() -> None:
    settings = RuntimeDatabaseSettings(
        url=SecretStr(_database_test_url("runtime-user"))
    )

    url = runtime_database_url(settings)

    assert url.drivername == "postgresql+asyncpg"
    assert url.query["ssl"] == "require"
    assert "sslmode" not in url.query


def test_remote_runtime_url_rejects_disabled_tls() -> None:
    raw_url = _database_test_url("runtime-user") + "?sslmode=disable"
    settings = RuntimeDatabaseSettings(url=SecretStr(raw_url))

    with pytest.raises(DatabaseConfigurationError, match="must require TLS"):
        runtime_database_url(settings)


def test_local_url_allows_explicitly_disabled_tls() -> None:
    raw_url = (
        _database_test_url("runtime-user", host="localhost") + "?sslmode=disable"
    )
    settings = RuntimeDatabaseSettings(url=SecretStr(raw_url))

    url = runtime_database_url(settings)

    assert url.query["ssl"] == "disable"
    assert "sslmode" not in url.query


def test_local_compose_url_allows_disabled_tls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    raw_url = _database_test_url("runtime-user", host="postgres") + "?sslmode=disable"
    settings = RuntimeDatabaseSettings(url=SecretStr(raw_url))

    assert runtime_database_url(settings).query["ssl"] == "disable"


def test_compose_hostname_is_not_trusted_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    raw_url = _database_test_url("runtime-user", host="postgres") + "?sslmode=disable"
    settings = RuntimeDatabaseSettings(url=SecretStr(raw_url))

    with pytest.raises(DatabaseConfigurationError, match="must require TLS"):
        runtime_database_url(settings)


def test_conflicting_ssl_parameters_are_rejected() -> None:
    raw_url = _database_test_url("runtime-user") + "?sslmode=require&ssl=verify-full"
    settings = RuntimeDatabaseSettings(url=SecretStr(raw_url))

    with pytest.raises(DatabaseConfigurationError, match="conflicting sslmode and ssl"):
        runtime_database_url(settings)


@pytest.mark.anyio
async def test_transaction_pooler_disables_caches_and_local_pool() -> None:
    settings = RuntimeDatabaseSettings(
        url=SecretStr(_database_test_url("runtime-user", port=6543))
    )

    engine = create_runtime_engine(settings)
    try:
        assert isinstance(engine.pool, NullPool)
        assert engine.url.query["ssl"] == "require"
        assert "sslmode" not in engine.url.query
        assert engine.url.query["prepared_statement_cache_size"] == "0"
    finally:
        await engine.dispose()


def test_migration_url_rejects_transaction_pooler() -> None:
    settings = MigrationDatabaseSettings(
        url=SecretStr(_database_test_url("migration-user", port=6543))
    )

    with pytest.raises(DatabaseConfigurationError, match="direct Supabase connection"):
        migration_database_url(settings)
