"""Opt-in INV-001 acceptance against an isolated loopback PostgreSQL database.

Set INV001_TEST_DATABASE_URL to the disposable ``inv001_runner`` role in a
loopback-only database named ``inv001_acceptance``. The test migrates only that
database; never point it at development or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import INVITATION_EXPIRY_INTERVAL, MatchingInvitation

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


async def _assert_upgrade_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    sender_id = uuid4()
    recipient_id = uuid4()
    validation_recipient_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_private.users (id, email, password_hash) VALUES "
                    "(:sender_id, 'inv001-sender@example.invalid', 'test-only-hash'), "
                    "(:recipient_id, 'inv001-recipient@example.invalid', 'test-only-hash'), "
                    "(:validation_recipient_id, 'inv001-validation@example.invalid', "
                    "'test-only-hash')"
                ),
                {
                    "sender_id": sender_id,
                    "recipient_id": recipient_id,
                    "validation_recipient_id": validation_recipient_id,
                },
            )
            inserted = (
                await connection.execute(
                    text(
                        "INSERT INTO app_private.matching_invitations "
                        "(sender_id, recipient_id, message) "
                        "VALUES (:sender_id, :recipient_id, 'Hello') "
                        "RETURNING id, pair_low_user_id, pair_high_user_id, "
                        "created_at, expires_at, status, version"
                    ),
                    {"sender_id": sender_id, "recipient_id": recipient_id},
                )
            ).one()
            invitation_id = inserted.id
            assert isinstance(invitation_id, UUID)
            assert {inserted.pair_low_user_id, inserted.pair_high_user_id} == {
                sender_id,
                recipient_id,
            }
            assert inserted.pair_low_user_id < inserted.pair_high_user_id
            assert inserted.expires_at - inserted.created_at == INVITATION_EXPIRY_INTERVAL
            assert inserted.status == "PENDING"
            assert inserted.version == 1

            permissions = (
                await connection.execute(
                    text(
                        "SELECT "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matching_invitations', 'SELECT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matching_invitations', 'INSERT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matching_invitations', 'UPDATE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matching_invitations', 'DELETE')"
                    )
                )
            ).one()
            assert permissions == (True, True, True, False)
            assert (
                await connection.scalar(
                    text(
                        "SELECT relrowsecurity FROM pg_class "
                        "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND relname = 'matching_invitations'"
                    )
                )
                is True
            )

        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:recipient_id, :sender_id, 'Reciprocal')",
            {"sender_id": sender_id, "recipient_id": recipient_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:sender_id, :recipient_id, 'Duplicate direction')",
            {"sender_id": sender_id, "recipient_id": recipient_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:sender_id, :sender_id, 'Self')",
            {"sender_id": sender_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:sender_id, :validation_recipient_id, ' not canonical ')",
            {"sender_id": sender_id, "validation_recipient_id": validation_recipient_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message, expires_at) "
            "VALUES (:sender_id, :validation_recipient_id, 'Wrong expiry', "
            "now() + INTERVAL '8 days')",
            {"sender_id": sender_id, "validation_recipient_id": validation_recipient_id},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:sender_id, :unknown_recipient_id, 'Orphan recipient')",
            {"sender_id": sender_id, "unknown_recipient_id": uuid4()},
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message, status) "
            "VALUES (:sender_id, :validation_recipient_id, 'Invalid status', 'UNKNOWN')",
            {"sender_id": sender_id, "validation_recipient_id": validation_recipient_id},
            DBAPIError,
        )
        await _expect_database_error(
            engine,
            "INSERT INTO app_private.matching_invitations "
            "(sender_id, recipient_id, message) "
            "VALUES (:sender_id, :validation_recipient_id, :message)",
            {
                "sender_id": sender_id,
                "validation_recipient_id": validation_recipient_id,
                "message": "x" * 10_001,
            },
        )
        await _expect_database_error(
            engine,
            "UPDATE app_private.matching_invitations "
            "SET status = 'ACCEPTED' WHERE id = :invitation_id",
            {"invitation_id": invitation_id},
        )

        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as first_session, sessions() as second_session:
            first = await first_session.scalar(
                select(MatchingInvitation).where(MatchingInvitation.id == invitation_id)
            )
            second = await second_session.scalar(
                select(MatchingInvitation).where(MatchingInvitation.id == invitation_id)
            )
            assert first is not None
            assert second is not None
            transition_at = datetime.now(UTC)
            first.decline(at=transition_at)
            second.cancel(at=transition_at)
            await first_session.commit()
            with pytest.raises(StaleDataError):
                await second_session.commit()
            await second_session.rollback()

        async with engine.begin() as connection:
            terminal = (
                await connection.execute(
                    text(
                        "SELECT status, responded_at, version "
                        "FROM app_private.matching_invitations WHERE id = :invitation_id"
                    ),
                    {"invitation_id": invitation_id},
                )
            ).one()
            assert terminal.status == "DECLINED"
            assert terminal.responded_at == transition_at
            assert terminal.version == 2
            new_pending_id = await connection.scalar(
                text(
                    "INSERT INTO app_private.matching_invitations "
                    "(sender_id, recipient_id, message) "
                    "VALUES (:recipient_id, :sender_id, 'Allowed after terminal') "
                    "RETURNING id"
                ),
                {"sender_id": sender_id, "recipient_id": recipient_id},
            )
            assert isinstance(new_pending_id, UUID)
    finally:
        await engine.dispose()


async def _assert_downgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            table_name, type_name = (
                await connection.execute(
                    text(
                        "SELECT to_regclass('app_private.matching_invitations'), "
                        "to_regtype('app_private.invitation_status')"
                    )
                )
            ).one()
            assert table_name is None
            assert type_name is None
            assert (
                await connection.scalar(
                    text("SELECT to_regclass('app_private.profile_custom_preferences')")
                )
                == "app_private.profile_custom_preferences"
            )
    finally:
        await engine.dispose()


async def _assert_reupgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT to_regclass('app_private.matching_invitations')")
                )
                == "app_private.matching_invitations"
            )
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.matching_invitations")
                )
                == 0
            )
    finally:
        await engine.dispose()


def test_live_invitation_upgrade_constraints_concurrency_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("INV001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV001_TEST_DATABASE_URL for disposable INV-001 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv001_acceptance"
        or parsed_url.username != "inv001_runner"
    ):
        pytest.fail(
            "INV-001 requires the disposable inv001_runner role in the isolated "
            "loopback inv001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "0011_preference_persistence")
        command.upgrade(config, "head")
        asyncio.run(_assert_upgrade_contract(async_database_url))
        command.downgrade(config, "0011_preference_persistence")
        asyncio.run(_assert_downgraded(async_database_url))
        command.upgrade(config, "head")
        asyncio.run(_assert_reupgraded(async_database_url))
    finally:
        # Stop at the pre-INV-001 head. Migration 0001 manages a cluster-global
        # runtime role that may be shared by another local database.
        command.downgrade(config, "0011_preference_persistence")
        get_migration_database_settings.cache_clear()
