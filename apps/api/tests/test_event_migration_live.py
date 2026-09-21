"""Opt-in EVT-003 acceptance against an empty disposable PostgreSQL database.

Set EVT003_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named evt003_acceptance. The test migrates and drops its entire schema;
never point it at development or production data.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _expect_database_error(
    engine: AsyncEngine,
    statement: str,
    parameters: dict[str, object],
    error_type: type[DBAPIError] = IntegrityError,
) -> None:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        with pytest.raises(error_type):
            await connection.execute(text(statement), parameters)
        await transaction.rollback()


async def _assert_live_constraints(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    admin_id = uuid4()
    attendee_id = uuid4()
    first_event_id = uuid4()
    second_event_id = uuid4()
    first_media_id = uuid4()
    second_media_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_private.users (id, email, password_hash, role) "
                    "VALUES "
                    "(:admin_id, 'evt003-admin@example.invalid', 'test-only-hash', 'ADMIN'), "
                    "(:attendee_id, 'evt003-user@example.invalid', 'test-only-hash', 'USER')"
                ),
                {"admin_id": admin_id, "attendee_id": attendee_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.events "
                    "(id, start_date, end_date, created_by, updated_by) "
                    "VALUES "
                    "(:first_id, '2026-10-01T08:00:00Z', '2026-10-01T10:00:00Z', "
                    ":admin_id, :admin_id), "
                    "(:second_id, '2026-10-02T08:00:00Z', '2026-10-02T10:00:00Z', "
                    ":admin_id, :admin_id)"
                ),
                {
                    "first_id": first_event_id,
                    "second_id": second_event_id,
                    "admin_id": admin_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.event_media "
                    "(id, event_id, object_key, usage, alt_en, alt_de, mime_type, "
                    "byte_size, width, height, created_by) "
                    "VALUES "
                    "(:first_media_id, :first_event_id, :first_key, 'EVENT_COVER', "
                    "'First cover', 'Erstes Titelbild', 'image/webp', 128, 64, 64, "
                    ":admin_id), "
                    "(:second_media_id, :second_event_id, :second_key, 'EVENT_COVER', "
                    "'Second cover', 'Zweites Titelbild', 'image/webp', 128, 64, 64, "
                    ":admin_id)"
                ),
                {
                    "first_media_id": first_media_id,
                    "first_event_id": first_event_id,
                    "first_key": f"{first_media_id}.webp",
                    "second_media_id": second_media_id,
                    "second_event_id": second_event_id,
                    "second_key": f"{second_media_id}.webp",
                    "admin_id": admin_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE app_private.events SET cover_media_id = :media_id WHERE id = :event_id"
                ),
                {"media_id": first_media_id, "event_id": first_event_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.event_registrations (event_id, user_id) "
                    "VALUES (:event_id, :user_id)"
                ),
                {"event_id": first_event_id, "user_id": attendee_id},
            )

        await _expect_database_error(
            engine,
            "UPDATE app_private.events SET cover_media_id = :media_id WHERE id = :event_id",
            {"media_id": second_media_id, "event_id": first_event_id},
        )
        await _expect_database_error(
            engine,
            "DELETE FROM app_private.event_media WHERE id = :media_id",
            {"media_id": first_media_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.events "
            "(start_date, end_date, created_by, updated_by) "
            "VALUES ('2026-10-01T10:00:00Z', '2026-10-01T08:00:00Z', "
            ":admin_id, :admin_id)",
            {"admin_id": admin_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.events (status, created_by, updated_by) "
            "VALUES ('INVALID', :admin_id, :admin_id)",
            {"admin_id": admin_id},
            DBAPIError,
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.events (visibility, created_by, updated_by) "
            "VALUES ('INVALID', :admin_id, :admin_id)",
            {"admin_id": admin_id},
            DBAPIError,
        )

        async with engine.begin() as connection:
            await connection.execute(
                text("UPDATE app_private.events SET cover_media_id = NULL WHERE id = :event_id"),
                {"event_id": first_event_id},
            )
            await connection.execute(
                text("DELETE FROM app_private.events WHERE id = :event_id"),
                {"event_id": first_event_id},
            )
            media_count = (
                await connection.execute(
                    text("SELECT count(*) FROM app_private.event_media WHERE event_id = :event_id"),
                    {"event_id": first_event_id},
                )
            ).scalar_one()
            registration_count = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM app_private.event_registrations "
                        "WHERE event_id = :event_id"
                    ),
                    {"event_id": first_event_id},
                )
            ).scalar_one()
            assert media_count == 0
            assert registration_count == 0
    finally:
        await engine.dispose()


async def _assert_clean_downgrade(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT to_regnamespace('app_private'), to_regrole('vgu_buddy_runtime')")
            )
            schema, role = result.one()
            assert schema is None
            assert role is None
    finally:
        await engine.dispose()


def test_live_event_upgrade_constraints_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("EVT003_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set EVT003_TEST_DATABASE_URL for disposable EVT-003 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "evt003_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "EVT-003 requires the privileged postgres role in the isolated loopback "
            "evt003_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )
    try:
        command.upgrade(config, "head")
        asyncio.run(_assert_live_constraints(async_database_url))
        command.downgrade(config, "base")
        asyncio.run(_assert_clean_downgrade(async_database_url))
        command.upgrade(config, "head")
    finally:
        command.downgrade(config, "base")
        get_migration_database_settings.cache_clear()
