"""Pure SEM-006 identity, state, and sanitized-summary contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock
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
    get_semester_restore_preflight,
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
        "0020_semester_restore_execution",
        SEMESTER_RESTORE_ALEMBIC_HEAD,
    }
    assert SEMESTER_RESTORE_ALEMBIC_HEAD == "0021_restore_runtime_permissions"
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


def _actor() -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.invalid",
        password_hash="unused",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )


def _current(*, marker: int) -> Semester:
    return Semester(
        id=UUID("60000000-0000-4000-8000-000000000001"),
        status=SemesterStatus.CURRENT,
        started_at=BOUNDARY + timedelta(days=1),
        student_accounts_created=marker,
        first_student_created_at=BOUNDARY + timedelta(days=2) if marker else None,
    )


@pytest.mark.anyio
async def test_preflight_exposes_only_exact_running_new_cohort_finalization() -> None:
    restore, backup, source, reset = _context()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [
        restore,
        backup,
        source,
        reset,
        _current(marker=1),
        BOUNDARY + timedelta(days=3),
    ]

    result = await get_semester_restore_preflight(
        session,
        _actor(),
        operation_id=RESTORE_ID,
    )

    assert result.backup_state is SemesterBackupState.RESTORE_BLOCKED_NEW_DATA
    assert result.can_execute is False
    assert result.can_finalize_new_cohort_block is True


@pytest.mark.anyio
@pytest.mark.parametrize("blocker", ["expired", "wrong_operation_state", "missing_checksum"])
async def test_preflight_does_not_finalize_other_restore_blockers(blocker: str) -> None:
    restore, backup, source, reset = _context()
    now = BOUNDARY + timedelta(days=3)
    if blocker == "expired":
        backup.expires_at = now
    elif blocker == "wrong_operation_state":
        restore.state = SemesterOperationState.SUCCEEDED
        restore.completed_at = now
    else:
        backup.database_manifest_checksum = None
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [restore, backup, source, reset, _current(marker=1), now]

    result = await get_semester_restore_preflight(
        session,
        _actor(),
        operation_id=RESTORE_ID,
    )

    assert result.can_execute is False
    assert result.can_finalize_new_cohort_block is False


@pytest.mark.anyio
async def test_new_cohort_gate_persists_failure_without_mutating_user_or_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    restore, backup, historical, _reset = _context()
    current = _current(marker=1)
    new_user = User(
        id=UUID("70000000-0000-4000-8000-000000000001"),
        email="new-cohort@example.invalid",
        password_hash="unused",
        role=UserRole.USER,
        email_verified=True,
        is_active=True,
        semester_id=current.id,
    )
    audit = AsyncMock()
    monkeypatch.setattr("app.services.semester_restore.record_audit_log", audit)
    user_snapshot = (new_user.id, new_user.semester_id, new_user.email_verified, new_user.is_active)
    history_snapshot = (
        historical.id,
        historical.status,
        historical.student_accounts_created,
    )

    result = await _apply_locked_gate(
        cast(AsyncSession, object()),
        _actor(),
        restore,
        backup,
        current,
        now=BOUNDARY + timedelta(days=3),
        replay=False,
    )

    assert result == "blocked"
    assert backup.state is SemesterBackupState.RESTORE_BLOCKED_NEW_DATA
    assert backup.restored_at is None
    assert restore.state is SemesterOperationState.FAILED
    assert restore.failure_code == "RESTORE_BLOCKED_NEW_DATA"
    assert current.student_accounts_created == 1
    assert (
        new_user.id,
        new_user.semester_id,
        new_user.email_verified,
        new_user.is_active,
    ) == user_snapshot
    assert (
        historical.id,
        historical.status,
        historical.student_accounts_created,
    ) == history_snapshot
    audit.assert_awaited_once()
