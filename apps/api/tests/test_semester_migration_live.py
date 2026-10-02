"""Opt-in SEM-001 migration, invariant, and registration race acceptance.

Set SEM001_TEST_DATABASE_URL to the disposable ``sem001_runner`` role in the
loopback-only ``sem001_acceptance`` database. The test returns that database to
revision 0016 and must never target development or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import Semester, SemesterStatus
from app.services.auth import register_user

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)


def _config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_legacy_accounts(engine: AsyncEngine) -> tuple[UUID, UUID]:
    admin_id = uuid4()
    student_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, role, created_at) VALUES "
                "(:admin_id, :admin_email, 'test-hash', 'ADMIN', :now), "
                "(:student_id, :student_email, 'test-hash', 'USER', :now)"
            ),
            {
                "admin_id": admin_id,
                "admin_email": f"sem-admin-{admin_id}@example.invalid",
                "student_id": student_id,
                "student_email": f"legacy-student-{student_id}@example.invalid",
                "now": NOW,
            },
        )
    return admin_id, student_id


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


async def _register(
    factory: async_sessionmaker[AsyncSession],
    email: str,
) -> UUID:
    async with factory() as session:
        user = await register_user(session, email, "Correct horse battery staple 2026!")
        await session.commit()
        return user.id


async def _assert_upgrade_invariants(
    engine: AsyncEngine,
    admin_id: UUID,
    legacy_student_id: UUID,
) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        semester = await session.scalar(
            select(Semester).where(Semester.status == SemesterStatus.CURRENT)
        )
        assert semester is not None
        semester_id = semester.id
        assert semester.student_accounts_created == 1
        assert semester.first_student_created_at == NOW
        stamp_rows = (
            await session.execute(text("SELECT id, semester_id FROM app_private.users ORDER BY id"))
        ).all()
        stamps: dict[UUID, UUID | None] = {row.id: row.semester_id for row in stamp_rows}
        assert stamps[admin_id] is None
        assert stamps[legacy_student_id] == semester_id

    await _expect_integrity_error(
        engine,
        "INSERT INTO app_private.semesters (status) VALUES ('CURRENT')",
        {},
    )
    await _expect_integrity_error(
        engine,
        "UPDATE app_private.semesters SET student_accounts_created = 0 WHERE id = :id",
        {"id": semester_id},
    )
    await _expect_integrity_error(
        engine,
        "INSERT INTO app_private.semester_operations "
        "(operation_type, semester_id, admin_actor_id) "
        "VALUES ('RESET', :semester_id, :student_id)",
        {"semester_id": semester_id, "student_id": legacy_student_id},
    )

    operation_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_operations "
                "(id, operation_type, state, semester_id, admin_actor_id, requested_at, "
                "started_at) VALUES "
                "(:id, 'RESET', 'RUNNING', :semester_id, :admin_id, :now, :now)"
            ),
            {
                "id": operation_id,
                "semester_id": semester_id,
                "admin_id": admin_id,
                "now": NOW,
            },
        )
    await _expect_integrity_error(
        engine,
        "INSERT INTO app_private.semester_operations "
        "(operation_type, state, semester_id, admin_actor_id, requested_at, started_at) "
        "VALUES ('RESTORE', 'RUNNING', :semester_id, :admin_id, :now, :now)",
        {"semester_id": semester_id, "admin_id": admin_id, "now": NOW},
    )

    await _expect_integrity_error(
        engine,
        "INSERT INTO app_private.semester_backups "
        "(source_semester_id, source_boundary_at, created_by_operation_id, state, "
        "verified_at, expires_at) VALUES "
        "(:semester_id, :boundary, :operation_id, 'READY', :verified, :expires)",
        {
            "semester_id": semester_id,
            "boundary": NOW,
            "operation_id": operation_id,
            "verified": NOW + timedelta(minutes=1),
            "expires": NOW + timedelta(days=30),
        },
    )

    backup_id = uuid4()
    completed_at = NOW + timedelta(minutes=5)
    expires_at = completed_at + timedelta(days=30)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_backups "
                "(id, source_semester_id, source_boundary_at, created_by_operation_id) "
                "VALUES (:id, :semester_id, :boundary, :operation_id)"
            ),
            {
                "id": backup_id,
                "semester_id": semester_id,
                "boundary": NOW,
                "operation_id": operation_id,
            },
        )
        await connection.execute(
            text("UPDATE app_private.semester_backups SET verified_at = :verified WHERE id = :id"),
            {"verified": completed_at, "id": backup_id},
        )
    await _expect_integrity_error(
        engine,
        "UPDATE app_private.semester_backups SET verified_at = :changed WHERE id = :id",
        {"changed": completed_at + timedelta(seconds=1), "id": backup_id},
    )
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE app_private.semester_backups SET "
                "state = 'READY', database_manifest_location = 'private/db/manifest.json', "
                "database_manifest_checksum = 'db-checksum', "
                "database_row_counts = '{\"users\": 1}'::jsonb, "
                "avatar_manifest_location = 'private/avatars/manifest.json', "
                "avatar_manifest_checksum = 'avatar-checksum', avatar_object_count = 0, "
                "verified_at = :verified, expires_at = :expires WHERE id = :id"
            ),
            {
                "verified": completed_at,
                "expires": expires_at,
                "id": backup_id,
            },
        )
        await connection.execute(
            text(
                "UPDATE app_private.semester_operations SET backup_id = :backup_id, "
                "state = 'SUCCEEDED', completed_at = :completed_at WHERE id = :operation_id"
            ),
            {
                "backup_id": backup_id,
                "completed_at": completed_at,
                "operation_id": operation_id,
            },
        )
    async with engine.connect() as connection:
        persisted = (
            await connection.execute(
                text(
                    "SELECT state, verified_at, expires_at, database_row_counts, "
                    "avatar_object_count FROM app_private.semester_backups WHERE id = :id"
                ),
                {"id": backup_id},
            )
        ).one()
        assert persisted.state == "READY"
        assert persisted.verified_at == completed_at
        assert persisted.expires_at == expires_at
        assert persisted.expires_at - completed_at == timedelta(days=30)
        assert persisted.database_row_counts == {"users": 1}
        assert persisted.avatar_object_count == 0
    await _expect_integrity_error(
        engine,
        "UPDATE app_private.semester_backups SET expires_at = :changed WHERE id = :id",
        {"changed": expires_at + timedelta(seconds=1), "id": backup_id},
    )

    new_user_ids = await asyncio.gather(
        _register(factory, "semester-race-a@example.invalid"),
        _register(factory, "semester-race-b@example.invalid"),
    )
    async with engine.begin() as connection:
        marker = (
            await connection.execute(
                text(
                    "SELECT student_accounts_created, first_student_created_at "
                    "FROM app_private.semesters WHERE id = :id"
                ),
                {"id": semester_id},
            )
        ).one()
        assert marker.student_accounts_created == 3
        assert marker.first_student_created_at == NOW
        registered_semesters = (
            (
                await connection.execute(
                    text("SELECT DISTINCT semester_id FROM app_private.users WHERE id = ANY(:ids)"),
                    {"ids": list(new_user_ids)},
                )
            )
            .scalars()
            .all()
        )
        assert registered_semesters == [semester_id]
        await connection.execute(
            text("DELETE FROM app_private.users WHERE id = ANY(:ids)"),
            {"ids": [legacy_student_id, *new_user_ids]},
        )

    async with engine.connect() as connection:
        marker_after_delete = (
            await connection.execute(
                text(
                    "SELECT student_accounts_created, first_student_created_at "
                    "FROM app_private.semesters WHERE id = :id"
                ),
                {"id": semester_id},
            )
        ).one()
        assert marker_after_delete == (3, NOW)
        assert (
            await connection.scalar(text("SELECT count(*) FROM app_private.semester_operations"))
            == 1
        )
        privileges = (
            await connection.execute(
                text(
                    "SELECT "
                    "has_table_privilege('vgu_buddy_runtime', 'app_private.semesters', 'SELECT'), "
                    "has_table_privilege('vgu_buddy_runtime', 'app_private.semesters', 'DELETE'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.semester_operations', 'DELETE'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.semester_backups', 'DELETE')"
                )
            )
        ).one()
        assert privileges == (True, False, False, False)

    await _expect_integrity_error(
        engine,
        "DELETE FROM app_private.users WHERE id = :admin_id",
        {"admin_id": admin_id},
    )
    await _expect_integrity_error(
        engine,
        "UPDATE app_private.semester_backups SET state = 'CREATING' WHERE id = :id",
        {"id": backup_id},
    )


async def _assert_downgraded(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        values = (
            await connection.execute(
                text(
                    "SELECT to_regclass('app_private.semesters'), "
                    "to_regclass('app_private.semester_operations'), "
                    "to_regclass('app_private.semester_backups'), "
                    "to_regtype('app_private.semester_status')"
                )
            )
        ).one()
        assert values == (None, None, None, None)
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'app_private' AND table_name = 'users' "
                    "AND column_name = 'semester_id'"
                )
            )
            == 0
        )
        assert await connection.scalar(text("SELECT count(*) FROM app_private.users")) == 1


async def _assert_reupgraded(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT to_regclass('app_private.semesters')"))
            == "app_private.semesters"
        )
        row = (
            await connection.execute(
                text(
                    "SELECT status, student_accounts_created, first_student_created_at "
                    "FROM app_private.semesters"
                )
            )
        ).one()
        assert row == ("CURRENT", 0, None)


def test_live_semester_upgrade_invariants_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("SEM001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set SEM001_TEST_DATABASE_URL for disposable SEM-001 acceptance.")
    parsed = make_url(database_url)
    if (
        parsed.host != "127.0.0.1"
        or parsed.database != "sem001_acceptance"
        or parsed.username != "sem001_runner"
    ):
        pytest.fail(
            "SEM-001 requires sem001_runner in the isolated loopback sem001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _config()
    async_url = parsed.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    engine = create_async_engine(async_url, poolclass=NullPool)
    try:
        command.upgrade(config, "0016_chat_message_cleanup")
        admin_id, student_id = asyncio.run(_seed_legacy_accounts(engine))
        command.upgrade(config, "head")
        asyncio.run(_assert_upgrade_invariants(engine, admin_id, student_id))
        command.check(config)
        command.downgrade(config, "0016_chat_message_cleanup")
        asyncio.run(_assert_downgraded(engine))
        command.upgrade(config, "head")
        asyncio.run(_assert_reupgraded(engine))
    finally:
        command.downgrade(config, "0016_chat_message_cleanup")
        asyncio.run(engine.dispose())
        get_migration_database_settings.cache_clear()
