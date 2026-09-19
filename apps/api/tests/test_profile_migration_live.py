"""Opt-in BE-010 acceptance against an empty disposable PostgreSQL database.

Set BE010_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named be010_acceptance. The test migrates and drops its entire schema;
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _expect_integrity_error(
    engine: AsyncEngine,
    statement: str,
    parameters: dict[str, object],
) -> None:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        with pytest.raises(IntegrityError):
            await connection.execute(text(statement), parameters)
        await transaction.rollback()


async def _assert_live_constraints(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    user_id = uuid4()
    profile_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_private.users "
                    "(id, email, password_hash) "
                    "VALUES (:id, :email, :password_hash)"
                ),
                {
                    "id": user_id,
                    "email": "be010-acceptance@example.invalid",
                    "password_hash": "disposable-test-hash",
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.student_profiles (id, user_id) "
                    "VALUES (:id, :user_id)"
                ),
                {"id": profile_id, "user_id": user_id},
            )
            interest_id = (
                await connection.execute(
                    text("SELECT id FROM app_private.interests WHERE code = 'travel'")
                )
            ).scalar_one()
            seeded_interests = set(
                (
                    await connection.execute(
                        text("SELECT code FROM app_private.interests")
                    )
                ).scalars()
            )
            seeded_languages = set(
                (
                    await connection.execute(
                        text("SELECT code FROM app_private.languages")
                    )
                ).scalars()
            )
            assert {
                "art",
                "cooking",
                "gaming",
                "hiking",
                "language-exchange",
                "movies",
                "music",
                "photography",
                "reading",
                "sports",
                "technology",
                "travel",
                "volunteering",
            } <= seeded_interests
            assert {"de", "en", "es", "fr", "ja", "ko", "vi", "zh"} <= seeded_languages
            await connection.execute(
                text(
                    "INSERT INTO app_private.profile_interests "
                    "(profile_id, interest_id) VALUES (:profile_id, :interest_id)"
                ),
                {"profile_id": profile_id, "interest_id": interest_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.profile_languages "
                    "(profile_id, language_code, proficiency) "
                    "VALUES (:profile_id, 'en', 'fluent')"
                ),
                {"profile_id": profile_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.profile_photos "
                    "(profile_id, object_key, mime_type, byte_size, width, height, is_avatar) "
                    "VALUES (:profile_id, :object_key, 'image/jpeg', 128, 64, 64, true)"
                ),
                {"profile_id": profile_id, "object_key": f"{uuid4()}.jpg"},
            )

        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.student_profiles (user_id) VALUES (:user_id)",
            {"user_id": user_id},
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.profile_interests "
            "(profile_id, interest_id) VALUES (:profile_id, :interest_id)",
            {"profile_id": profile_id, "interest_id": interest_id},
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.profile_languages "
            "(profile_id, language_code, proficiency) "
            "VALUES (:profile_id, 'en', 'native')",
            {"profile_id": profile_id},
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.profile_photos "
            "(profile_id, object_key, mime_type, byte_size, width, height, is_avatar) "
            "VALUES (:profile_id, :object_key, 'image/png', 256, 64, 64, true)",
            {"profile_id": profile_id, "object_key": f"{uuid4()}.png"},
        )
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


def test_live_profile_upgrade_constraints_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("BE010_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set BE010_TEST_DATABASE_URL for disposable BE-010 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "be010_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "BE-010 requires the privileged postgres role in the isolated loopback "
            "be010_acceptance database."
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
