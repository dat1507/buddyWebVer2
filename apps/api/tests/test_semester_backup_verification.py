"""Focused SEM-004 manifest linkage, effective expiry, and safe-report tests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.semester_backup_verification as verification_service
from app.models import SemesterBackup, SemesterBackupState
from app.services.database_backup_storage import (
    BackupStorageObjectRef,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
    DatabaseBackupStorageError,
    DatabaseBackupStorageNotFoundError,
)
from app.services.semester_avatar_backup import AvatarBackupManifest, AvatarBackupManifestRef
from app.services.semester_backup_verification import (
    SemesterBackupExpiryReport,
    SemesterBackupExpiryValidationError,
    SemesterBackupPackageError,
    SemesterBackupVerificationReport,
    effective_semester_backup_state,
    process_expired_semester_backup_batch,
    validate_semester_backup_manifests,
)
from app.services.semester_database_backup import (
    BACKUP_TABLES,
    DatabaseBackupCompatibility,
    DatabaseBackupManifest,
    DatabaseBackupSharedReferences,
    DatabaseBackupTableManifest,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
BACKUP_ID = UUID("90000000-0000-4000-8000-000000000001")
SEMESTER_ID = UUID("91000000-0000-4000-8000-000000000001")


class _LocationStore:
    def location(self, reference: BackupStorageObjectRef) -> str:
        return f"private-test://semester-database-backups/{reference.object_key}"

    async def put_file(self, reference: BackupStorageObjectRef, source: Path) -> None:
        raise AssertionError((reference, source))

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None:
        raise AssertionError((reference, target))

    async def delete(self, reference: BackupStorageObjectRef) -> None:
        raise AssertionError(reference)


class _CleanupStore(_LocationStore):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_delete_once: str | None = None

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None:
        try:
            content = self.objects[reference.object_key]
        except KeyError:
            raise DatabaseBackupStorageNotFoundError() from None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    async def delete(self, reference: BackupStorageObjectRef) -> None:
        if reference.object_key == self.fail_delete_once:
            self.fail_delete_once = None
            raise DatabaseBackupStorageError("injected private cleanup detail")
        self.objects.pop(reference.object_key, None)


def _backup(*, state: SemesterBackupState = SemesterBackupState.CREATING) -> SemesterBackup:
    store = _LocationStore()
    backup = SemesterBackup(
        id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=NOW - timedelta(days=100),
        created_by_operation_id=uuid4(),
        state=state,
        database_manifest_location=store.location(
            DatabaseBackupObjectRef(BACKUP_ID, DatabaseBackupObjectKind.MANIFEST)
        ),
        database_manifest_checksum="a" * 64,
        database_row_counts={spec.table_name: 0 for spec in BACKUP_TABLES},
        avatar_manifest_location=store.location(AvatarBackupManifestRef(BACKUP_ID)),
        avatar_manifest_checksum="b" * 64,
        avatar_object_count=0,
    )
    if state is not SemesterBackupState.CREATING:
        backup.verified_at = NOW - timedelta(days=1)
        backup.expires_at = NOW + timedelta(days=29)
    return backup


def _database_manifest() -> DatabaseBackupManifest:
    store = _LocationStore()
    return DatabaseBackupManifest(
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=NOW - timedelta(days=100),
        created_at=NOW - timedelta(days=2),
        artifact_location=store.location(
            DatabaseBackupObjectRef(BACKUP_ID, DatabaseBackupObjectKind.ARTIFACT)
        ),
        artifact_size_bytes=1,
        artifact_sha256="c" * 64,
        tables=tuple(
            DatabaseBackupTableManifest(
                table_name=spec.table_name,
                archive_name=spec.archive_name,
                columns=("id",),
                row_count=0,
                byte_size=1,
                sha256="d" * 64,
            )
            for spec in BACKUP_TABLES
        ),
        shared_references=DatabaseBackupSharedReferences(
            source_semester_ids=(SEMESTER_ID,),
            admin_user_ids=(),
            interest_ids=(),
            language_codes=(),
            activity_ids=(),
            event_ids=(),
        ),
        compatibility=DatabaseBackupCompatibility(
            source_postgresql_major=17,
            required_target_postgresql_major=17,
            required_alembic_head="0018_backup_verification",
            producer_version="test",
        ),
    )


def _avatar_manifest() -> AvatarBackupManifest:
    return AvatarBackupManifest(
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=NOW - timedelta(days=100),
        created_at=NOW - timedelta(days=1),
        database_manifest_checksum="a" * 64,
        object_count=0,
        total_bytes=0,
        objects=(),
    )


def test_complete_cross_manifest_package_is_accepted() -> None:
    validate_semester_backup_manifests(
        _backup(),
        _database_manifest(),
        _avatar_manifest(),
        storage=_LocationStore(),
    )


@pytest.mark.parametrize(
    "database_change,avatar_change",
    [
        ({"backup_id": uuid4()}, {}),
        ({}, {"backup_id": uuid4()}),
        ({"source_semester_id": uuid4()}, {}),
        ({}, {"database_manifest_checksum": "e" * 64}),
        ({}, {"source_boundary_at": NOW}),
    ],
)
def test_mixed_or_stale_cross_manifest_package_fails_closed(
    database_change: dict[str, object],
    avatar_change: dict[str, object],
) -> None:
    database_manifest = _database_manifest().model_copy(update=database_change)
    avatar_manifest = _avatar_manifest().model_copy(update=avatar_change)

    with pytest.raises(SemesterBackupPackageError, match="linkage"):
        validate_semester_backup_manifests(
            _backup(),
            database_manifest,
            avatar_manifest,
            storage=_LocationStore(),
        )


def test_effective_expiry_is_inclusive_and_does_not_mutate_persisted_state() -> None:
    backup = _backup(state=SemesterBackupState.READY)
    assert backup.expires_at is not None

    assert (
        effective_semester_backup_state(
            backup,
            now=backup.expires_at - timedelta(microseconds=1),
        )
        is SemesterBackupState.READY
    )
    assert (
        effective_semester_backup_state(
            backup,
            now=backup.expires_at,
        )
        is SemesterBackupState.EXPIRED
    )
    assert (
        effective_semester_backup_state(
            backup,
            now=backup.expires_at + timedelta(seconds=1),
        )
        is SemesterBackupState.EXPIRED
    )
    assert backup.state is SemesterBackupState.READY


def test_effective_expiry_rejects_client_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        effective_semester_backup_state(_backup(), now=datetime(2026, 10, 2, 12, 0))


def test_operational_reports_are_aggregate_only() -> None:
    assert set(SemesterBackupVerificationReport.__dataclass_fields__) == {
        "backup_id",
        "persisted_state",
        "effective_state",
        "verified_at",
        "expires_at",
        "database_rows",
        "avatar_objects",
        "newly_verified",
        "newly_ready",
    }
    assert set(SemesterBackupExpiryReport.__dataclass_fields__) == {
        "selected",
        "expired",
        "cleaned",
        "failed",
    }
    private_fields = {
        "manifest_location",
        "manifest_checksum",
        "object_key",
        "owner_user_id",
        "artifact_path",
    }
    assert private_fields.isdisjoint(SemesterBackupVerificationReport.__dataclass_fields__)
    assert private_fields.isdisjoint(SemesterBackupExpiryReport.__dataclass_fields__)


@pytest.mark.anyio
@pytest.mark.parametrize("batch_size", (0, 101))
async def test_expiry_cleanup_rejects_unbounded_batches(batch_size: int) -> None:
    with pytest.raises(SemesterBackupExpiryValidationError, match="batch size"):
        await process_expired_semester_backup_batch(
            cast(async_sessionmaker[AsyncSession], object()),
            storage=_LocationStore(),
            batch_size=batch_size,
        )


@pytest.mark.anyio
async def test_expiry_cleanup_rejects_naive_test_clock() -> None:
    with pytest.raises(SemesterBackupExpiryValidationError, match="timezone-aware"):
        await process_expired_semester_backup_batch(
            cast(async_sessionmaker[AsyncSession], object()),
            storage=_LocationStore(),
            expiry_now=datetime(2026, 11, 1, 12, 0),
        )


@pytest.mark.anyio
async def test_partial_artifact_cleanup_retries_without_touching_unrelated_object(
    tmp_path: Path,
) -> None:
    store = _CleanupStore()
    backup = _backup(state=SemesterBackupState.READY)
    database_manifest = _database_manifest()
    database_content = json.dumps(
        database_manifest.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    backup.database_manifest_checksum = hashlib.sha256(database_content).hexdigest()
    avatar_manifest = _avatar_manifest().model_copy(
        update={"database_manifest_checksum": backup.database_manifest_checksum}
    )
    avatar_content = json.dumps(
        avatar_manifest.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    backup.avatar_manifest_checksum = hashlib.sha256(avatar_content).hexdigest()
    database_artifact_ref = DatabaseBackupObjectRef(
        BACKUP_ID,
        DatabaseBackupObjectKind.ARTIFACT,
    )
    database_manifest_ref = DatabaseBackupObjectRef(
        BACKUP_ID,
        DatabaseBackupObjectKind.MANIFEST,
    )
    avatar_manifest_ref = AvatarBackupManifestRef(BACKUP_ID)
    unrelated_key = "unrelated/keep.json"
    store.objects = {
        database_artifact_ref.object_key: b"artifact",
        database_manifest_ref.object_key: database_content,
        avatar_manifest_ref.object_key: avatar_content,
        unrelated_key: b"keep",
    }
    store.fail_delete_once = database_manifest_ref.object_key

    with pytest.raises(DatabaseBackupStorageError):
        await verification_service._cleanup_expired_backup_artifacts(
            store,
            backup,
            workspace=tmp_path / "first",
        )
    assert database_artifact_ref.object_key not in store.objects
    assert database_manifest_ref.object_key in store.objects
    assert avatar_manifest_ref.object_key in store.objects

    await verification_service._cleanup_expired_backup_artifacts(
        store,
        backup,
        workspace=tmp_path / "retry",
    )
    assert store.objects == {unrelated_key: b"keep"}
