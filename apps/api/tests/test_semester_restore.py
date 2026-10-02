"""Pure SEM-006 identity, state, and sanitized-summary contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Semester,
    SemesterBackup,
    SemesterBackupState,
    SemesterOperation,
    SemesterOperationState,
    SemesterOperationType,
    SemesterStatus,
    User,
    UserRole,
)
from app.services.semester_restore import (
    SEMESTER_RESTORE_ALEMBIC_HEAD,
    SEMESTER_RESTORE_COMPATIBLE_MANIFEST_HEADS,
    SemesterRestoreStateError,
    _apply_locked_gate,
    _integer_counts,
    _is_restore_identity_valid,
    _parse_restore_summary,
    semester_restore_confirmation_phrase,
)

ADMIN_ID = UUID("10000000-0000-4000-8000-000000000001")
SOURCE_ID = UUID("20000000-0000-4000-8000-000000000001")
BACKUP_ID = UUID("30000000-0000-4000-8000-000000000001")
RESET_ID = UUID("40000000-0000-4000-8000-000000000001")
RESTORE_ID = UUID("50000000-0000-4000-8000-000000000001")
BOUNDARY = datetime(2026, 9, 1, tzinfo=UTC)


def _context() -> tuple[SemesterOperation, SemesterBackup, Semester, SemesterOperation]:
    source = Semester(
        id=SOURCE_ID,
        status=SemesterStatus.CLOSED,
        started_at=BOUNDARY,
        closed_at=BOUNDARY + timedelta(days=1),
        reset_operation_id=RESET_ID,
        student_accounts_created=2,
        first_student_created_at=BOUNDARY + timedelta(hours=1),
    )
    reset = SemesterOperation(
        id=RESET_ID,
        operation_type=SemesterOperationType.RESET,
        state=SemesterOperationState.SUCCEEDED,
        semester_id=SOURCE_ID,
        admin_actor_id=ADMIN_ID,
        backup_id=BACKUP_ID,
    )
    restore = SemesterOperation(
        id=RESTORE_ID,
        operation_type=SemesterOperationType.RESTORE,
        state=SemesterOperationState.RUNNING,
        semester_id=SOURCE_ID,
        admin_actor_id=ADMIN_ID,
        backup_id=BACKUP_ID,
    )
    backup = SemesterBackup(
        id=BACKUP_ID,
        source_semester_id=SOURCE_ID,
        source_boundary_at=BOUNDARY,
        created_by_operation_id=RESET_ID,
        state=SemesterBackupState.READY,
        verified_at=BOUNDARY + timedelta(hours=2),
        expires_at=BOUNDARY + timedelta(days=31),
        database_manifest_location="private://database/manifest.json",
        database_manifest_checksum="a" * 64,
        database_row_counts={"users": 2},
        avatar_manifest_location="private://avatars/manifest.json",
        avatar_manifest_checksum="b" * 64,
        avatar_object_count=1,
    )
    return restore, backup, source, reset


def test_restore_confirmation_is_bound_to_the_exact_backup() -> None:
    assert semester_restore_confirmation_phrase(BACKUP_ID) == f"RESTORE {BACKUP_ID}"
    assert semester_restore_confirmation_phrase(SOURCE_ID) != semester_restore_confirmation_phrase(
        BACKUP_ID
    )


def test_restore_identity_accepts_only_exact_ready_reset_context() -> None:
    restore, backup, source, reset = _context()

    assert _is_restore_identity_valid(
        restore,
        backup,
        source,
        reset,
        admin_id=ADMIN_ID,
    )

    backup.state = SemesterBackupState.RESTORE_BLOCKED_NEW_DATA
    assert not _is_restore_identity_valid(
        restore,
        backup,
        source,
        reset,
        admin_id=ADMIN_ID,
    )
    backup.state = SemesterBackupState.READY
    restore.operation_type = SemesterOperationType.RESET
    assert not _is_restore_identity_valid(
        restore,
        backup,
        source,
        reset,
        admin_id=ADMIN_ID,
    )


def test_restore_rejects_mismatched_reset_and_existing_restore_metadata() -> None:
    restore, backup, source, reset = _context()
    reset.backup_id = SOURCE_ID
    assert not _is_restore_identity_valid(
        restore,
        backup,
        source,
        reset,
        admin_id=ADMIN_ID,
    )

    restore, backup, source, reset = _context()
    backup.restore_operation_id = RESTORE_ID
    backup.restored_by_admin_id = ADMIN_ID
    backup.restored_at = BOUNDARY + timedelta(days=2)
    assert not _is_restore_identity_valid(
        restore,
        backup,
        source,
        reset,
        admin_id=ADMIN_ID,
    )


def test_restore_summary_and_schema_compatibility_are_bounded() -> None:
    assert SEMESTER_RESTORE_COMPATIBLE_MANIFEST_HEADS == {
        "0019_semester_reset_execution",
        SEMESTER_RESTORE_ALEMBIC_HEAD,
    }
    assert _integer_counts({"users": 2, "buddy_messages": 1}) == {
        "users": 2,
        "buddy_messages": 1,
    }
    assert _parse_restore_summary(
        {
            "source_semester_id": str(SOURCE_ID),
            "restored": {"users": 2},
            "avatar_objects_restored": 1,
        }
    ) == (SOURCE_ID, {"users": 2}, 1)
    with pytest.raises(SemesterRestoreStateError, match="aggregate"):
        _integer_counts({"users": -1})
    with pytest.raises(SemesterRestoreStateError, match="result"):
        _parse_restore_summary({"object_key": "private"})


@pytest.mark.anyio
async def test_effective_expiry_fails_operation_without_touching_a_package() -> None:
    restore, backup, _source, _reset = _context()
    current = Semester(
        id=UUID("60000000-0000-4000-8000-000000000001"),
        status=SemesterStatus.CURRENT,
        started_at=BOUNDARY + timedelta(days=1),
        student_accounts_created=0,
        first_student_created_at=None,
    )
    actor = User(
        id=ADMIN_ID,
        email="admin@example.invalid",
        password_hash="unused",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )

    expires_at = backup.expires_at
    assert expires_at is not None
    result = await _apply_locked_gate(
        cast(AsyncSession, object()),
        actor,
        restore,
        backup,
        current,
        now=expires_at,
        replay=False,
    )

    assert result == "expired"
    assert backup.state is SemesterBackupState.EXPIRED
    assert restore.state is SemesterOperationState.FAILED
    assert restore.failure_code == "RESTORE_BACKUP_EXPIRED"
