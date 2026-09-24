"""Opt-in EMAIL-001 acceptance against an empty disposable PostgreSQL database.

Set EMAIL001_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named email001_acceptance. Never point it at development or production data.
Because the runtime role is shared cluster-wide, cleanup stops at the migration's
0007 boundary; discard the database after the test.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    MigrationDatabaseSettings,
    get_migration_database_settings,
)
from app.core.database import migration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_USERS = {
    "user-false@example.invalid": ("USER", False),
    "user-true@example.invalid": ("USER", True),
    "admin-false@example.invalid": ("ADMIN", False),
    "admin-true@example.invalid": ("ADMIN", True),
}


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_legacy_rows(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            for email, (role, email_verified) in LEGACY_USERS.items():
                await connection.execute(
                    text(
                        "INSERT INTO app_private.users "
                        "(id, email, password_hash, role, email_verified, created_at, last_login) "
                        "VALUES (:id, :email, 'test-only-hash', :role, :verified, "
                        "'2025-01-02T03:04:05Z', '2026-08-09T10:11:12Z')"
                    ),
                    {
                        "id": uuid4(),
                        "email": email,
                        "role": role,
                        "verified": email_verified,
                    },
                )
    finally:
        await engine.dispose()


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


async def _assert_upgrade_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    token_user_id = uuid4()
    blank_email_user_id = uuid4()
    empty_digest_user_id = uuid4()
    expired_token_user_id = uuid4()
    verified_at = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
    try:
        async with engine.begin() as connection:
            rows = (
                await connection.execute(
                    text(
                        "SELECT email, role::text, email_verified, email_verified_at "
                        "FROM app_private.users ORDER BY email"
                    )
                )
            ).all()
            assert len(rows) == len(LEGACY_USERS)
            for email, role, legacy_boolean, timestamp in rows:
                expected_role, expected_boolean = LEGACY_USERS[email]
                assert role == expected_role
                assert legacy_boolean is expected_boolean
                assert timestamp is None

            columns = {
                row[0]
                for row in (
                    await connection.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'app_private' "
                            "AND table_name = 'email_verification_tokens'"
                        )
                    )
                ).all()
            }
            assert "token_digest" in columns
            assert "token" not in columns

            await connection.execute(
                text(
                    "UPDATE app_private.users SET email_verified_at = :verified_at "
                    "WHERE email = 'user-false@example.invalid'"
                ),
                {"verified_at": verified_at},
            )
            stored_timestamp = await connection.scalar(
                text(
                    "SELECT email_verified_at FROM app_private.users "
                    "WHERE email = 'user-false@example.invalid'"
                )
            )
            assert stored_timestamp == verified_at

            await connection.execute(
                text(
                    "INSERT INTO app_private.users "
                    "(id, email, password_hash, role) "
                    "VALUES "
                    "(:token_id, 'token-owner@example.invalid', 'test-only-hash', 'USER'), "
                    "(:blank_id, 'blank-owner@example.invalid', 'test-only-hash', 'USER'), "
                    "(:empty_id, 'empty-owner@example.invalid', 'test-only-hash', 'USER'), "
                    "(:expired_id, 'expired-owner@example.invalid', 'test-only-hash', 'USER')"
                ),
                {
                    "token_id": token_user_id,
                    "blank_id": blank_email_user_id,
                    "empty_id": empty_digest_user_id,
                    "expired_id": expired_token_user_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.email_verification_tokens "
                    "(user_id, token_digest, email_snapshot, expires_at) "
                    "VALUES (:user_id, :digest, 'token-owner@example.invalid', :expires_at)"
                ),
                {
                    "user_id": token_user_id,
                    "digest": bytes(range(32)),
                    "expires_at": datetime.now(UTC) + timedelta(minutes=15),
                },
            )

        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.email_verification_tokens "
            "(user_id, token_digest, email_snapshot, expires_at) "
            "VALUES (:user_id, :digest, 'token-owner@example.invalid', :expires_at)",
            {
                "user_id": token_user_id,
                "digest": bytes(reversed(range(32))),
                "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            },
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.email_verification_tokens "
            "(user_id, token_digest, email_snapshot, expires_at) "
            "VALUES (:user_id, :digest, '   ', :expires_at)",
            {
                "user_id": blank_email_user_id,
                "digest": b"different-digest-with-enough-entropy",
                "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            },
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.email_verification_tokens "
            "(user_id, token_digest, email_snapshot, expires_at) "
            "VALUES (:user_id, :digest, 'token-owner@example.invalid', :expires_at)",
            {
                "user_id": empty_digest_user_id,
                "digest": b"",
                "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            },
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.email_verification_tokens "
            "(user_id, token_digest, email_snapshot, expires_at) "
            "VALUES (:user_id, :digest, 'expired-owner@example.invalid', :expires_at)",
            {
                "user_id": expired_token_user_id,
                "digest": b"expired-digest-with-enough-entropy",
                "expires_at": datetime.now(UTC) - timedelta(minutes=1),
            },
        )

        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE app_private.email_verification_tokens "
                    "SET superseded_at = now() WHERE user_id = :user_id"
                ),
                {"user_id": token_user_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO app_private.email_verification_tokens "
                    "(user_id, token_digest, email_snapshot, expires_at) "
                    "VALUES (:user_id, :digest, 'token-owner@example.invalid', :expires_at)"
                ),
                {
                    "user_id": token_user_id,
                    "digest": b"replacement-digest-with-enough-entropy",
                    "expires_at": datetime.now(UTC) + timedelta(minutes=15),
                },
            )
            await connection.execute(
                text(
                    "DELETE FROM app_private.users "
                    "WHERE id IN (:token_id, :blank_id, :empty_id, :expired_id)"
                ),
                {
                    "token_id": token_user_id,
                    "blank_id": blank_email_user_id,
                    "empty_id": empty_digest_user_id,
                    "expired_id": expired_token_user_id,
                },
            )
            remaining = await connection.scalar(
                text(
                    "SELECT count(*) FROM app_private.email_verification_tokens "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": token_user_id},
            )
            assert remaining == 0
    finally:
        await engine.dispose()


async def _assert_downgrade_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            token_table = await connection.scalar(
                text("SELECT to_regclass('app_private.email_verification_tokens')")
            )
            timestamp_column_count = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'app_private' AND table_name = 'users' "
                    "AND column_name = 'email_verified_at'"
                )
            )
            rows = (
                await connection.execute(
                    text(
                        "SELECT email, role::text, email_verified "
                        "FROM app_private.users WHERE email LIKE '%@example.invalid'"
                    )
                )
            ).all()
            assert token_table is None
            assert timestamp_column_count == 0
            assert len(rows) == len(LEGACY_USERS)
            for email, role, legacy_boolean in rows:
                expected_role, expected_boolean = LEGACY_USERS[email]
                assert role == expected_role
                assert legacy_boolean is expected_boolean
    finally:
        await engine.dispose()


def test_live_email_verification_upgrade_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("EMAIL001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set EMAIL001_TEST_DATABASE_URL for disposable EMAIL-001 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "email001_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "EMAIL-001 requires the privileged postgres role in the isolated loopback "
            "email001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = migration_database_url(
        MigrationDatabaseSettings(url=SecretStr(database_url))
    ).render_as_string(hide_password=False)
    failed_stage: str | None = None
    stage = "upgrade to the legacy boundary"
    try:
        command.upgrade(config, "0007_event_tables")
        stage = "seed legacy rows"
        asyncio.run(_seed_legacy_rows(async_database_url))
        stage = "upgrade and verify EMAIL-001"
        command.upgrade(config, "head")
        asyncio.run(_assert_upgrade_contract(async_database_url))
        stage = "downgrade and verify EMAIL-001"
        command.downgrade(config, "0007_event_tables")
        asyncio.run(_assert_downgrade_contract(async_database_url))
        stage = "re-upgrade EMAIL-001"
        command.upgrade(config, "head")
    except Exception:
        failed_stage = stage
    finally:
        try:
            command.downgrade(config, "0007_event_tables")
        except Exception:
            failed_stage = failed_stage or "final EMAIL-001 cleanup"
        get_migration_database_settings.cache_clear()
    if failed_stage is not None:
        pytest.fail(
            f"EMAIL-001 disposable migration failed during {failed_stage}; "
            "database details were suppressed.",
            pytrace=False,
        )
