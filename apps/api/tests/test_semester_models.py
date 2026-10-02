"""Domain tests for SEM-001 lifecycle and retention foundations."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models import (
    SEMESTER_BACKUP_RETENTION_DAYS,
    SemesterBackup,
    SemesterBackupState,
    SemesterOperation,
    SemesterOperationState,
    SemesterOperationType,
    SemesterStateTransitionError,
    semester_backup_expires_at,
)

REQUESTED_AT = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)


def _operation() -> SemesterOperation:
    return SemesterOperation(
        operation_type=SemesterOperationType.RESET,
        state=SemesterOperationState.REQUESTED,
        semester_id=uuid4(),
        admin_actor_id=uuid4(),
        requested_at=REQUESTED_AT,
        affected_counts={},
        result_summary={},
    )


def _backup(*, state: SemesterBackupState = SemesterBackupState.CREATING) -> SemesterBackup:
    return SemesterBackup(
        source_semester_id=uuid4(),
        source_boundary_at=REQUESTED_AT,
        created_by_operation_id=uuid4(),
        state=state,
        database_row_counts={},
        avatar_object_count=0,
    )


def test_backup_states_are_exactly_the_confirmed_contract() -> None:
    assert list(SemesterBackupState) == [
        SemesterBackupState.CREATING,
        SemesterBackupState.READY,
        SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
        SemesterBackupState.EXPIRED,
        SemesterBackupState.FAILED,
    ]


def test_retention_is_exactly_thirty_days_and_timezone_safe() -> None:
    non_utc = datetime(2026, 10, 2, 10, 30, tzinfo=timezone(timedelta(hours=2)))

    expires_at = semester_backup_expires_at(non_utc)

    assert SEMESTER_BACKUP_RETENTION_DAYS == 30
    assert expires_at == datetime(2026, 11, 1, 8, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="timezone-aware"):
        semester_backup_expires_at(datetime(2026, 10, 2, 8, 30))


def test_operation_lifecycle_is_monotonic_and_records_sanitized_results() -> None:
    operation = _operation()

    operation.start(at=REQUESTED_AT + timedelta(minutes=1))
    operation.succeed(
        at=REQUESTED_AT + timedelta(minutes=2),
        result_summary={"students": 12},
    )

    assert operation.state is SemesterOperationState.SUCCEEDED
    assert operation.started_at == REQUESTED_AT + timedelta(minutes=1)
    assert operation.completed_at == REQUESTED_AT + timedelta(minutes=2)
    assert operation.result_summary == {"students": 12}
    assert operation.failure_code is None
    with pytest.raises(SemesterStateTransitionError):
        operation.fail(at=REQUESTED_AT + timedelta(minutes=3), failure_code="LATE_FAILURE")


def test_operation_may_fail_during_preflight_but_rejects_unbounded_detail() -> None:
    operation = _operation()

    operation.fail(at=REQUESTED_AT + timedelta(seconds=1), failure_code="BACKUP_FAILED")

    assert operation.state is SemesterOperationState.FAILED
    assert operation.started_at is None
    assert operation.failure_code == "BACKUP_FAILED"
    with pytest.raises(SemesterStateTransitionError):
        operation.start(at=REQUESTED_AT + timedelta(seconds=2))

    second = _operation()
    with pytest.raises(ValueError, match="failure code is invalid"):
        second.fail(at=REQUESTED_AT, failure_code=" ")


@pytest.mark.parametrize(
    ("initial", "allowed"),
    [
        (
            SemesterBackupState.CREATING,
            {SemesterBackupState.READY, SemesterBackupState.FAILED},
        ),
        (
            SemesterBackupState.READY,
            {
                SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
                SemesterBackupState.EXPIRED,
            },
        ),
        (
            SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
            {SemesterBackupState.EXPIRED},
        ),
        (SemesterBackupState.EXPIRED, set()),
        (SemesterBackupState.FAILED, set()),
    ],
)
def test_backup_lifecycle_has_only_the_persisted_edges(
    initial: SemesterBackupState,
    allowed: set[SemesterBackupState],
) -> None:
    for candidate in SemesterBackupState:
        backup = _backup(state=initial)
        if candidate in allowed:
            backup.transition_to(candidate)
            assert backup.state is candidate
        else:
            with pytest.raises(SemesterStateTransitionError):
                backup.transition_to(candidate)
