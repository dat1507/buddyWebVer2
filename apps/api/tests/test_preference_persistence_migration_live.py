"""Opt-in PREF-001 acceptance against an isolated loopback PostgreSQL database.

Set PREF001_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named pref001_acceptance. The test migrates and drops its entire schema;
never point it at development or production data.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

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


async def _seed_legacy_profiles(database_url: str) -> tuple[UUID, UUID, UUID]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    first_user_id = uuid4()
    second_user_id = uuid4()
    first_profile_id = uuid4()
    second_profile_id = uuid4()
    try:
        async with engine.begin() as connection:
            travel_id = cast_uuid(
                await connection.scalar(
                    text("SELECT id FROM app_private.interests WHERE code = 'travel'")
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.users (id, email, password_hash) VALUES "
                    "(:first_user_id, 'pref001-first@example.invalid', 'test-only-hash'), "
                    "(:second_user_id, 'pref001-second@example.invalid', 'test-only-hash')"
                ),
                {
                    "first_user_id": first_user_id,
                    "second_user_id": second_user_id,
                },
            )
            preferences = json.dumps({"preferred_activity_ids": [str(travel_id)]})
            await connection.execute(
                text(
                    "INSERT INTO app_private.student_profiles "
                    "(id, user_id, full_name, preferences) VALUES "
                    "(:first_profile_id, :first_user_id, 'First Profile', "
                    "CAST(:preferences AS jsonb)), "
                    "(:second_profile_id, :second_user_id, 'Second Profile', "
                    "CAST(:preferences AS jsonb))"
                ),
                {
                    "first_profile_id": first_profile_id,
                    "first_user_id": first_user_id,
                    "second_profile_id": second_profile_id,
                    "second_user_id": second_user_id,
                    "preferences": preferences,
                },
            )
        return first_profile_id, second_profile_id, travel_id
    finally:
        await engine.dispose()


def cast_uuid(value: object) -> UUID:
    assert isinstance(value, UUID)
    return value


async def _assert_upgrade_contract(
    database_url: str,
    first_profile_id: UUID,
    second_profile_id: UUID,
    legacy_travel_id: UUID,
) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            migrated = (
                await connection.execute(
                    text(
                        "SELECT profile.id, profile.full_name, activity.id, activity.code, "
                        "profile.preferences "
                        "FROM app_private.student_profiles AS profile "
                        "JOIN app_private.profile_activities AS selected "
                        "ON selected.profile_id = profile.id "
                        "JOIN app_private.activities AS activity "
                        "ON activity.id = selected.activity_id "
                        "ORDER BY profile.full_name"
                    )
                )
            ).all()
            assert [(row.full_name, row.code) for row in migrated] == [
                ("First Profile", "travel"),
                ("Second Profile", "travel"),
            ]
            assert all(row[0] in {first_profile_id, second_profile_id} for row in migrated)
            assert all(row[2] == legacy_travel_id for row in migrated)
            assert all(
                row.preferences == {"preferred_activity_ids": [str(legacy_travel_id)]}
                for row in migrated
            )

            interest_label = await connection.scalar(
                text("SELECT label_en FROM app_private.interests WHERE code = 'travel'")
            )
            await connection.execute(
                text(
                    "UPDATE app_private.activities SET label_en = 'Independent activity label' "
                    "WHERE code = 'travel'"
                )
            )
            assert (
                await connection.scalar(
                    text("SELECT label_en FROM app_private.interests WHERE code = 'travel'")
                )
                == interest_label
            )

            await connection.execute(
                text(
                    "INSERT INTO app_private.profile_custom_preferences "
                    "(profile_id, kind, display_label, normalized_key, proficiency) "
                    "VALUES "
                    "(:first_id, 'INTEREST', 'Formula 1', 'formula 1', NULL), "
                    "(:first_id, 'ACTIVITY', 'Formula 1', 'formula 1', NULL), "
                    "(:first_id, 'LANGUAGE', 'Esperanto', 'esperanto', 'beginner'), "
                    "(:second_id, 'INTEREST', 'Formula 1', 'formula 1', NULL)"
                ),
                {"first_id": first_profile_id, "second_id": second_profile_id},
            )

            permissions = (
                await connection.execute(
                    text(
                        "SELECT "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.activities', 'SELECT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.activities', 'INSERT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_activities', 'SELECT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_activities', 'INSERT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_activities', 'DELETE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_activities', 'UPDATE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_custom_preferences', "
                        "'SELECT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_custom_preferences', "
                        "'INSERT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_custom_preferences', "
                        "'UPDATE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.profile_custom_preferences', "
                        "'DELETE')"
                    )
                )
            ).one()
            assert permissions == (
                True,
                False,
                True,
                True,
                True,
                False,
                True,
                True,
                True,
                True,
            )
            rls_rows = (
                await connection.execute(
                    text(
                        "SELECT relname, relrowsecurity FROM pg_class "
                        "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND relname IN ('activities', 'profile_activities', "
                        "'profile_custom_preferences')"
                    )
                )
            ).all()
            rls: dict[str, bool] = {
                str(table_name): bool(enabled) for table_name, enabled in rls_rows
            }
            assert rls == {
                "activities": True,
                "profile_activities": True,
                "profile_custom_preferences": True,
            }

        await _expect_database_error(
            engine,
            "INSERT INTO app_private.activities (code, label_en, label_de) "
            "VALUES ('travel', 'Duplicate', 'Duplikat')",
            {},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_activities (profile_id, activity_id) "
            "VALUES (:profile_id, :activity_id)",
            {"profile_id": first_profile_id, "activity_id": legacy_travel_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_activities (profile_id, activity_id) "
            "VALUES (:profile_id, :activity_id)",
            {"profile_id": first_profile_id, "activity_id": uuid4()},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'INTEREST', 'Formula One', 'formula 1')",
            {"profile_id": first_profile_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'INVALID', 'Invalid', 'invalid')",
            {"profile_id": first_profile_id},
            DBAPIError,
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'LANGUAGE', 'No proficiency', 'no proficiency')",
            {"profile_id": first_profile_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key, proficiency) "
            "VALUES (:profile_id, 'ACTIVITY', 'Wrong proficiency', "
            "'wrong proficiency', 'fluent')",
            {"profile_id": first_profile_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'ACTIVITY', :label, 'oversized label')",
            {"profile_id": first_profile_id, "label": "x" * 121},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'ACTIVITY', 'Oversized key', :normalized_key)",
            {"profile_id": first_profile_id, "normalized_key": "x" * 256},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.profile_custom_preferences "
            "(profile_id, kind, display_label, normalized_key) "
            "VALUES (:profile_id, 'ACTIVITY', 'Missing key', NULL)",
            {"profile_id": first_profile_id},
        )

        async with engine.begin() as connection:
            activity_count_before = await connection.scalar(
                text("SELECT count(*) FROM app_private.activities")
            )
            await connection.execute(
                text("DELETE FROM app_private.student_profiles WHERE id = :profile_id"),
                {"profile_id": first_profile_id},
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.profile_activities "
                        "WHERE profile_id = :profile_id"
                    ),
                    {"profile_id": first_profile_id},
                )
                == 0
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.profile_custom_preferences "
                        "WHERE profile_id = :profile_id"
                    ),
                    {"profile_id": first_profile_id},
                )
                == 0
            )
            assert await connection.scalar(
                text("SELECT count(*) FROM app_private.activities")
            ) == activity_count_before
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.profile_custom_preferences "
                        "WHERE profile_id = :profile_id"
                    ),
                    {"profile_id": second_profile_id},
                )
                == 1
            )
    finally:
        await engine.dispose()


async def _assert_reupgrade_is_idempotent(
    database_url: str,
    second_profile_id: UUID,
) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            catalog_counts = (
                await connection.execute(
                    text(
                        "SELECT count(*), count(DISTINCT code) "
                        "FROM app_private.activities"
                    )
                )
            ).one()
            assert catalog_counts[0] == catalog_counts[1]
            assert catalog_counts[0] == await connection.scalar(
                text("SELECT count(*) FROM app_private.interests")
            )
            selected_codes = set(
                (
                    await connection.execute(
                        text(
                            "SELECT activity.code "
                            "FROM app_private.profile_activities AS selected "
                            "JOIN app_private.activities AS activity "
                            "ON activity.id = selected.activity_id "
                            "WHERE selected.profile_id = :profile_id"
                        ),
                        {"profile_id": second_profile_id},
                    )
                ).scalars()
            )
            assert selected_codes == {"travel"}
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


def test_live_preference_upgrade_constraints_cascades_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("PREF001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set PREF001_TEST_DATABASE_URL for disposable PREF-001 PostgreSQL acceptance."
        )
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "pref001_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "PREF-001 requires the privileged postgres role in the isolated loopback "
            "pref001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )
    try:
        command.upgrade(config, "0010_edge_email_outbox_functions")
        first_profile_id, second_profile_id, legacy_travel_id = asyncio.run(
            _seed_legacy_profiles(async_database_url)
        )
        command.upgrade(config, "head")
        asyncio.run(
            _assert_upgrade_contract(
                async_database_url,
                first_profile_id,
                second_profile_id,
                legacy_travel_id,
            )
        )
        command.downgrade(config, "0010_edge_email_outbox_functions")
        command.upgrade(config, "head")
        asyncio.run(_assert_reupgrade_is_idempotent(async_database_url, second_profile_id))
        command.downgrade(config, "base")
        asyncio.run(_assert_clean_downgrade(async_database_url))
    finally:
        command.downgrade(config, "base")
        get_migration_database_settings.cache_clear()
