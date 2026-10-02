"""Opt-in PostgreSQL 17 and private-storage acceptance for SEM-006.

Set ``SEM006_TEST_DATABASE_URL`` to the isolated loopback ``sem006_acceptance``
database owned by ``sem006_runner``. The test rebuilds only that disposable database.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from test_semester_reset_live import (
    ADMIN_PASSWORD,
    _avatar_bytes,
    _ControlledAvatarTransport,
    _counts,
    _seed,
)

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    BackupDatabaseSettings,
    get_migration_database_settings,
)
from app.models import SemesterBackupState
from app.services.database_backup_storage import PrivateFileDatabaseBackupStore
from app.services.image_storage import ImageBucket, ImageStorageService, StorageObjectRef
from app.services.passwords import verify_password
from app.services.semester_avatar_backup import AvatarBackupAdapter, create_semester_avatar_backup
from app.services.semester_backup_verification import verify_semester_backup
from app.services.semester_database_backup import (
    DatabaseBackupError,
    PostgresBinaryCopyBackupAdapter,
    create_semester_database_backup,
)
from app.services.semester_reset import execute_semester_reset, semester_reset_confirmation_phrase
from app.services.semester_restore import (
    SemesterRestoreBlockedError,
    SemesterRestoreBusyError,
    SemesterRestorePackageError,
    execute_semester_restore,
    semester_restore_confirmation_phrase,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _validated_url() -> URL:
    raw = os.getenv("SEM006_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set SEM006_TEST_DATABASE_URL for disposable SEM-006 acceptance.")
    parsed = make_url(raw)
    if (
        parsed.host != "127.0.0.1"
        or parsed.database != "sem006_acceptance"
        or parsed.username != "sem006_runner"
    ):
        pytest.fail(
            "SEM-006 requires sem006_runner in the isolated loopback sem006_acceptance database."
        )
    return parsed


def _async_url(url: URL) -> str:
    return url.set(drivername="postgresql+asyncpg", query={"ssl": "disable"}).render_as_string(
        hide_password=False
    )


async def _clear_disposable_database(parsed: URL) -> None:
    engine = create_async_engine(_async_url(parsed), poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA IF EXISTS app_private CASCADE"))
            await connection.execute(text("DROP TABLE IF EXISTS public.alembic_version"))
    finally:
        await engine.dispose()


class _RestoreAvatarTransport(_ControlledAvatarTransport):
    def __init__(self) -> None:
        super().__init__()
        self.pause_upload = False
        self.upload_started = asyncio.Event()
        self.release_upload = asyncio.Event()

    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None:
        if self.pause_upload:
            self.upload_started.set()
            await self.release_upload.wait()
            self.pause_upload = False
        await super().upload(reference, content, content_type)


class _FailOnceRestoreAdapter(PostgresBinaryCopyBackupAdapter):
    def __init__(self, settings: BackupDatabaseSettings) -> None:
        super().__init__(settings)
        self.fail_once = True

    async def restore_into_transaction(self, connection: Any, **kwargs: Any) -> Any:
        if self.fail_once:
            self.fail_once = False
            raise DatabaseBackupError("Injected sanitized database restore failure.")
        return await super().restore_into_transaction(connection, **kwargs)


async def _prepare_reset(
    engine: AsyncEngine,
    backup_root: Path,
    parsed: URL,
) -> tuple[
    dict[str, UUID],
    async_sessionmaker[Any],
    PostgresBinaryCopyBackupAdapter,
    PrivateFileDatabaseBackupStore,
    _RestoreAvatarTransport,
    ImageStorageService,
    StorageObjectRef,
    StorageObjectRef,
    dict[str, int],
]:
    avatar = _avatar_bytes()
    ids = await _seed(engine, avatar)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    settings = BackupDatabaseSettings(url=SecretStr(parsed.render_as_string(False)))
    adapter = PostgresBinaryCopyBackupAdapter(settings)
    store = PrivateFileDatabaseBackupStore(backup_root)
    transport = _RestoreAvatarTransport()
    storage = ImageStorageService(transport)
    source_ref = StorageObjectRef(ImageBucket.PROFILE_IMAGES, f"{ids['photo']}.jpg")
    unrelated_ref = StorageObjectRef(ImageBucket.PROFILE_IMAGES, f"{uuid4()}.jpg")
    transport.objects[source_ref] = avatar
    transport.objects[unrelated_ref] = b"unrelated"
    baseline = await _counts(engine, ids["semester"])

    await create_semester_database_backup(
        factory,
        backup_id=ids["backup"],
        adapter=adapter,
        storage=store,
    )
    await create_semester_avatar_backup(
        factory,
        backup_id=ids["backup"],
        adapter=AvatarBackupAdapter(storage),
        storage=store,
    )
    verification = await verify_semester_backup(
        factory,
        backup_id=ids["backup"],
        storage=store,
    )
    assert verification.newly_verified is True
    await execute_semester_reset(
        factory,
        operation_id=ids["operation"],
        backup_id=ids["backup"],
        admin_id=ids["admin"],
        current_password=ADMIN_PASSWORD,
        confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
        snapshot_adapter=adapter,
        backup_storage=store,
        avatar_storage=storage,
    )
    assert await _counts(engine, ids["semester"]) == {key: 0 for key in baseline}
    assert source_ref not in transport.objects
    return (
        ids,
        factory,
        adapter,
        store,
        transport,
        storage,
        source_ref,
        unrelated_ref,
        baseline,
    )


async def _create_restore_operation(engine: AsyncEngine, ids: dict[str, UUID]) -> UUID:
    restore_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_operations "
                "(id, operation_type, state, semester_id, admin_actor_id, backup_id, "
                "requested_at, started_at) VALUES "
                "(:id, 'RESTORE', 'RUNNING', :semester, :admin, :backup, "
                "statement_timestamp(), statement_timestamp())"
            ),
            {**ids, "id": restore_id},
        )
    return restore_id


async def _successful_restore_acceptance(
    engine: AsyncEngine,
    backup_root: Path,
    parsed: URL,
) -> None:
    (
        ids,
        factory,
        adapter,
        store,
        transport,
        storage,
        source_ref,
        unrelated_ref,
        baseline,
    ) = await _prepare_reset(engine, backup_root, parsed)
    restore_id = await _create_restore_operation(engine, ids)
    settings = BackupDatabaseSettings(url=SecretStr(parsed.render_as_string(False)))

    failing_adapter = _FailOnceRestoreAdapter(settings)
    with pytest.raises(SemesterRestorePackageError):
        await execute_semester_restore(
            factory,
            operation_id=restore_id,
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_restore_confirmation_phrase(ids["backup"]),
            restore_adapter=failing_adapter,
            backup_storage=store,
            avatar_storage=storage,
        )
    assert source_ref not in transport.objects
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT state FROM app_private.semester_operations WHERE id = :id"),
                {"id": restore_id},
            )
            == "RUNNING"
        )

    transport.pause_upload = True
    first = asyncio.create_task(
        execute_semester_restore(
            factory,
            operation_id=restore_id,
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_restore_confirmation_phrase(ids["backup"]),
            restore_adapter=adapter,
            backup_storage=store,
            avatar_storage=storage,
        )
    )
    await asyncio.wait_for(transport.upload_started.wait(), timeout=10)

    with pytest.raises(SemesterRestoreBusyError):
        await execute_semester_restore(
            factory,
            operation_id=restore_id,
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_restore_confirmation_phrase(ids["backup"]),
            restore_adapter=adapter,
            backup_storage=store,
            avatar_storage=storage,
        )

    async def concurrent_registration() -> None:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_private.users "
                    "(id, email, password_hash, role, email_verified) VALUES "
                    "(:id, 'restore-race@example.invalid', 'student-hash', 'USER', true)"
                ),
                {"id": uuid4()},
            )

    with pytest.raises(DBAPIError):
        await concurrent_registration()
    transport.release_upload.set()
    report = await first

    assert report.operation_state.value == "SUCCEEDED"
    assert report.backup_state is SemesterBackupState.READY
    assert report.restored_counts["users"] == 2
    assert report.restored_counts["matching_invitations"] == 1
    assert report.restored_counts["matches"] == 1
    assert report.restored_counts["buddy_messages"] == 1
    assert report.avatar_objects_restored == 1
    assert await _counts(engine, ids["semester"]) == baseline
    assert transport.objects[source_ref] == _avatar_bytes()
    assert transport.objects[unrelated_ref] == b"unrelated"

    replay = await execute_semester_restore(
        factory,
        operation_id=restore_id,
        backup_id=ids["backup"],
        admin_id=ids["admin"],
        current_password=ADMIN_PASSWORD,
        confirmation_phrase=semester_restore_confirmation_phrase(ids["backup"]),
        restore_adapter=adapter,
        backup_storage=store,
        avatar_storage=storage,
    )
    assert replay.idempotent_replay is True
    assert await _counts(engine, ids["semester"]) == baseline

    async with engine.connect() as connection:
        admin = (
            await connection.execute(
                text("SELECT role, password_hash FROM app_private.users WHERE id = :id"),
                {"id": ids["admin"]},
            )
        ).one()
        assert admin.role == "ADMIN"
        assert verify_password(ADMIN_PASSWORD, admin.password_hash)
        assert await connection.scalar(text("SELECT count(*) FROM app_private.interests")) > 0
        assert await connection.scalar(text("SELECT count(*) FROM app_private.languages")) > 0
        assert await connection.scalar(text("SELECT count(*) FROM app_private.activities")) > 0
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM app_private.events WHERE id = :id"),
                {"id": ids["event"]},
            )
            == 1
        )
        metadata = (
            await connection.execute(
                text(
                    "SELECT backup.state, backup.restored_at, backup.restored_by_admin_id, "
                    "backup.restore_operation_id, operation.state AS operation_state "
                    "FROM app_private.semester_backups AS backup "
                    "JOIN app_private.semester_operations AS operation "
                    "ON operation.id = backup.restore_operation_id WHERE backup.id = :id"
                ),
                {"id": ids["backup"]},
            )
        ).one()
        assert metadata.state == "READY"
        assert metadata.restored_at is not None
        assert metadata.restored_by_admin_id == ids["admin"]
        assert metadata.restore_operation_id == restore_id
        assert metadata.operation_state == "SUCCEEDED"
        await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


async def _new_cohort_block_acceptance(
    engine: AsyncEngine,
    backup_root: Path,
    parsed: URL,
) -> None:
    (
        ids,
        factory,
        adapter,
        store,
        transport,
        storage,
        source_ref,
        _unrelated_ref,
        baseline,
    ) = await _prepare_reset(engine, backup_root, parsed)
    restore_id = await _create_restore_operation(engine, ids)
    new_user_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, role, email_verified) VALUES "
                "(:id, 'new-cohort@example.invalid', 'student-hash', 'USER', true)"
            ),
            {"id": new_user_id},
        )

    with pytest.raises(SemesterRestoreBlockedError):
        await execute_semester_restore(
            factory,
            operation_id=restore_id,
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_restore_confirmation_phrase(ids["backup"]),
            restore_adapter=adapter,
            backup_storage=store,
            avatar_storage=storage,
        )

    assert await _counts(engine, ids["semester"]) == {key: 0 for key in baseline}
    assert source_ref not in transport.objects
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM app_private.users WHERE id = :id"),
                {"id": new_user_id},
            )
            == 1
        )
        state = (
            await connection.execute(
                text(
                    "SELECT backup.state, backup.restored_at, operation.state AS operation_state, "
                    "operation.failure_code FROM app_private.semester_backups AS backup "
                    "JOIN app_private.semester_operations AS operation ON operation.id = :operation "
                    "WHERE backup.id = :backup"
                ),
                {"operation": restore_id, "backup": ids["backup"]},
            )
        ).one()
        assert state.state == "RESTORE_BLOCKED_NEW_DATA"
        assert state.restored_at is None
        assert state.operation_state == "FAILED"
        assert state.failure_code == "RESTORE_BLOCKED_NEW_DATA"


def test_live_semester_restore_is_exact_blocking_atomic_and_retry_safe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parsed = _validated_url()
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, parsed.render_as_string(False))
    get_migration_database_settings.cache_clear()
    config = _config()
    engine: AsyncEngine | None = None
    try:
        asyncio.run(_clear_disposable_database(parsed))
        command.upgrade(config, "head")
        engine = create_async_engine(_async_url(parsed), poolclass=NullPool)
        asyncio.run(
            _successful_restore_acceptance(
                engine,
                tmp_path / "success-private-backups",
                parsed,
            )
        )
        asyncio.run(engine.dispose())
        engine = None

        asyncio.run(_clear_disposable_database(parsed))
        command.upgrade(config, "head")
        engine = create_async_engine(_async_url(parsed), poolclass=NullPool)
        asyncio.run(
            _new_cohort_block_acceptance(
                engine,
                tmp_path / "blocked-private-backups",
                parsed,
            )
        )
        asyncio.run(engine.dispose())
        engine = None

        command.downgrade(config, "0019_semester_reset_execution")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        if engine is not None:
            asyncio.run(engine.dispose())
        get_migration_database_settings.cache_clear()
