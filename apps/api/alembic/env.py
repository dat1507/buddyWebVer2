"""Alembic migration environment for the VGU Buddy API."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from typing import Any, Literal

from alembic.ddl.postgresql import PostgresqlImpl
from sqlalchemy import String, Table, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_migration_database_settings
from app.core.database import migration_database_url
from app.models import Base

config = context.config

target_metadata = Base.metadata


class BuddyPostgresqlImpl(PostgresqlImpl):
    """Preserve published revision IDs beyond Alembic's default 32 characters."""

    __dialect__ = "postgresql"

    def version_table_impl(self, **kw: Any) -> Table:
        version_table = super().version_table_impl(**kw)
        version_table.c.version_num.type = String(128)
        return version_table


_VERSION_CAPACITY_SQL = (
    "ALTER TABLE IF EXISTS public.alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
)

type ObjectType = Literal[
    "schema",
    "table",
    "column",
    "index",
    "unique_constraint",
    "foreign_key_constraint",
    "check_constraint",
]
type ParentNameKey = Literal[
    "schema_name",
    "table_name",
    "schema_qualified_table_name",
]


def _include_name(
    name: str | None,
    type_: ObjectType,
    parent_names: MutableMapping[ParentNameKey, str | None],
) -> bool:
    """Limit autogenerate reflection to the owned application schema."""
    if type_ == "schema":
        return name in {None, target_metadata.schema}
    if type_ == "table":
        qualified_name = parent_names.get("schema_qualified_table_name")
        return name == "alembic_version" or qualified_name in target_metadata.tables
    return True


def _database_url() -> str:
    """Return the separately scoped migration URL without logging it."""
    configured_url = config.get_alembic_option("sqlalchemy.url")
    if configured_url:
        return configured_url

    url = migration_database_url(get_migration_database_settings())
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=_include_name,
    )

    with context.begin_transaction():
        context.execute(_VERSION_CAPACITY_SQL)
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations on a synchronous connection facade."""
    with connection.begin():
        connection.exec_driver_sql(_VERSION_CAPACITY_SQL)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=_include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create the async migration engine and run pending revisions."""
    connectable = async_engine_from_config(
        {"sqlalchemy.url": _database_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations through SQLAlchemy's async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
