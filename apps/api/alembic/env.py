"""Alembic migration environment for the VGU Buddy API."""

from __future__ import annotations

import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_migration_database_settings
from app.core.database import migration_database_url
from app.models import Base

config = context.config

target_metadata = Base.metadata


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
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations on a synchronous connection facade."""
    context.configure(connection=connection, target_metadata=target_metadata)

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
