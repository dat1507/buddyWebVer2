"""Pure safety-contract tests for SEM-005 reset orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.models import (
    Semester,
    SemesterBackup,
    SemesterBackupState,
    SemesterOperation,
    SemesterOperationState,
    SemesterOperationType,
    SemesterStatus,
)
from app.services.image_storage import ImageBucket, StorageObjectRef, StorageOperationError
from app.services.semester_avatar_backup import (
    AvatarBackupBinaryRef,
    AvatarBackupManifest,
    AvatarBackupObjectManifest,
)
from app.services.semester_database_backup import (
    BACKUP_TABLES,
    DatabaseBackupCompatibility,
    DatabaseBackupManifest,
    DatabaseBackupSharedReferences,
    DatabaseBackupTableManifest,
)
from app.services.semester_reset import (
    SemesterResetSnapshotError,
    SemesterResetStateError,
    SemesterResetStorageError,
    _delete_managed_avatars,
    _integer_counts,
    _is_reset_execution_eligible,
    _parse_reset_summary,
    _validate_current_snapshot,
    semester_reset_confirmation_phrase,
)

BACKUP_ID = UUID("11111111-1111-4111-8111-111111111111")
SEMESTER_ID = UUID("22222222-2222-4222-8222-222222222222")
PHOTO_ID = UUID("33333333-3333-4333-8333-333333333333")
PROFILE_ID = UUID("44444444-4444-4444-8444-444444444444")
USER_ID = UUID("55555555-5555-4555-8555-555555555555")
ADMIN_ID = UUID("77777777-7777-4777-8777-777777777777")
OPERATION_ID = UUID("88888888-8888-4888-8888-888888888888")
BOUNDARY = datetime(2026, 9, 1, tzinfo=UTC)
SOURCE_KEY = "66666666-6666-4666-8666-666666666666.jpg"


def _database_manifest() -> DatabaseBackupManifest:
    tables = tuple(
        DatabaseBackupTableManifest(
            table_name=spec.table_name,
            archive_name=spec.archive_name,
            columns=("id",),
            row_count=0,
            byte_size=1,
            sha256=f"{index + 1:064x}",
        )
        for index, spec in enumerate(BACKUP_TABLES)
    )
    return DatabaseBackupManifest(
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=BOUNDARY,
        created_at=BOUNDARY,
        artifact_location="private://database",
        artifact_size_bytes=1,
        artifact_sha256="a" * 64,
        tables=tables,
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
            required_alembic_head="0019_semester_reset_execution",
            producer_version="1.0",
        ),
    )


def _avatar_manifest() -> AvatarBackupManifest:
    item = AvatarBackupObjectManifest(
        photo_id=PHOTO_ID,
        profile_id=PROFILE_ID,
        owner_user_id=USER_ID,
        source_bucket="profile-images",
        source_object_key=SOURCE_KEY,
        backup_object_key=AvatarBackupBinaryRef(
            BACKUP_ID,
            PHOTO_ID,
            "image/jpeg",
        ).object_key,
        mime_type="image/jpeg",
        byte_size=3,
        width=1,
        height=1,
        sha256="b" * 64,
    )
    return AvatarBackupManifest(
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=BOUNDARY,
        created_at=BOUNDARY,
        database_manifest_checksum="c" * 64,
        object_count=1,
        total_bytes=3,
        objects=(item,),
    )


def _eligible_reset_context() -> tuple[SemesterOperation, SemesterBackup, Semester]:
    semester = Semester(
        id=SEMESTER_ID,
        status=SemesterStatus.CURRENT,
        started_at=BOUNDARY,
        reset_operation_id=None,
    )
    operation = SemesterOperation(
        id=OPERATION_ID,
        operation_type=SemesterOperationType.RESET,
        state=SemesterOperationState.RUNNING,
        semester_id=SEMESTER_ID,
        admin_actor_id=ADMIN_ID,
        backup_id=BACKUP_ID,
    )
    backup = SemesterBackup(
        id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=BOUNDARY,
        created_by_operation_id=OPERATION_ID,
        state=SemesterBackupState.CREATING,
        verified_at=BOUNDARY + timedelta(minutes=1),
        expires_at=None,
        failure_code=None,
        database_manifest_location="private://database/manifest.json",
        database_manifest_checksum="a" * 64,
        avatar_manifest_location="private://avatars/manifest.json",
        avatar_manifest_checksum="b" * 64,
    )
    return operation, backup, semester


class _AvatarStorage:
    def __init__(self, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        self.deleted: list[StorageObjectRef] = []

    async def delete_image(self, reference: StorageObjectRef) -> None:
        self.deleted.append(reference)
        if self.status_code is not None:
            raise StorageOperationError("private provider detail", status_code=self.status_code)


def test_confirmation_phrase_is_bound_to_exact_semester() -> None:
    assert semester_reset_confirmation_phrase(SEMESTER_ID) == f"RESET {SEMESTER_ID}"
    assert semester_reset_confirmation_phrase(BACKUP_ID) != semester_reset_confirmation_phrase(
        SEMESTER_ID
    )


def test_predelete_gate_accepts_only_verified_creating_backup_for_exact_boundary() -> None:
    operation, backup, semester = _eligible_reset_context()

    assert _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=ADMIN_ID,
    )

    for rejected_state in (
        SemesterBackupState.READY,
        SemesterBackupState.FAILED,
        SemesterBackupState.EXPIRED,
        SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
    ):
        backup.state = rejected_state
        assert not _is_reset_execution_eligible(
            operation,
            backup,
            semester,
            admin_id=ADMIN_ID,
        )


def test_predelete_gate_rejects_incomplete_mismatched_or_invalid_metadata() -> None:
    operation, backup, semester = _eligible_reset_context()
    backup.verified_at = None
    assert not _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=ADMIN_ID,
    )

    operation, backup, semester = _eligible_reset_context()
    backup.source_semester_id = BACKUP_ID
    assert not _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=ADMIN_ID,
    )

    operation, backup, semester = _eligible_reset_context()
    operation.state = SemesterOperationState.FAILED
    assert not _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=ADMIN_ID,
    )

    operation, backup, semester = _eligible_reset_context()
    backup.avatar_manifest_checksum = None
    assert not _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=ADMIN_ID,
    )


def test_current_snapshot_requires_exact_table_hashes_and_references() -> None:
    backed_up = _database_manifest()
    _validate_current_snapshot(backed_up, backed_up.model_copy())
    changed_table = backed_up.tables[0].model_copy(update={"sha256": "f" * 64})
    changed = backed_up.model_copy(update={"tables": (changed_table, *backed_up.tables[1:])})

    with pytest.raises(SemesterResetSnapshotError, match="changed"):
        _validate_current_snapshot(backed_up, changed)


def test_aggregate_and_result_metadata_are_strict_and_private() -> None:
    assert _integer_counts({"users": 2, "buddy_messages": 1}) == {
        "users": 2,
        "buddy_messages": 1,
    }
    with pytest.raises(SemesterResetStateError, match="aggregate"):
        _integer_counts({"users": -1})
    with pytest.raises(SemesterResetStateError, match="result"):
        _parse_reset_summary({"private_path": "secret"})


@pytest.mark.anyio
async def test_avatar_cleanup_uses_only_manifest_keys_and_treats_missing_as_idempotent() -> None:
    storage = _AvatarStorage(status_code=404)

    processed = await _delete_managed_avatars(storage, _avatar_manifest())  # type: ignore[arg-type]

    assert processed == 1
    assert storage.deleted == [StorageObjectRef(ImageBucket.PROFILE_IMAGES, SOURCE_KEY)]


@pytest.mark.anyio
async def test_avatar_cleanup_fails_closed_without_exposing_provider_detail() -> None:
    storage = _AvatarStorage(status_code=503)

    with pytest.raises(SemesterResetStorageError) as captured:
        await _delete_managed_avatars(storage, _avatar_manifest())  # type: ignore[arg-type]

    assert "provider" not in str(captured.value)
    assert Path(SOURCE_KEY).name not in str(captured.value)
