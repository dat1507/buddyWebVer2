"""Semester boundaries and durable reset/restore operation metadata."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

SEMESTER_BACKUP_RETENTION_DAYS: Final = 30
SEMESTER_BACKUP_RETENTION: Final = timedelta(days=SEMESTER_BACKUP_RETENTION_DAYS)


class SemesterStatus(StrEnum):
    """Minimal persisted lifecycle for one cohort boundary."""

    CURRENT = "CURRENT"
    CLOSED = "CLOSED"


class SemesterOperationType(StrEnum):
    """Destructive workflows that later semester tasks may orchestrate."""

    RESET = "RESET"
    RESTORE = "RESTORE"


class SemesterOperationState(StrEnum):
    """Durable lifecycle shared by reset and restore operations."""

    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class SemesterBackupState(StrEnum):
    """The exact backup states in the semester-management contract."""

    CREATING = "CREATING"
    READY = "READY"
    RESTORE_BLOCKED_NEW_DATA = "RESTORE_BLOCKED_NEW_DATA"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class SemesterStateTransitionError(ValueError):
    """Raised when an in-memory lifecycle transition is not allowed."""


def _aware_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


def semester_backup_expires_at(reset_completed_at: datetime) -> datetime:
    """Return the deterministic 30-day deadline from reset completion."""
    return (
        _aware_utc(
            reset_completed_at,
            field_name="Reset completion time",
        )
        + SEMESTER_BACKUP_RETENTION
    )


class Semester(Base):
    """One immutable cohort boundary with a monotonic registration marker."""

    __tablename__ = "semesters"
    __table_args__ = (
        CheckConstraint(
            "student_accounts_created >= 0",
            name="ck_semesters_student_accounts_created_non_negative",
        ),
        CheckConstraint(
            "(student_accounts_created = 0 AND first_student_created_at IS NULL) "
            "OR (student_accounts_created > 0 AND first_student_created_at IS NOT NULL)",
            name="ck_semesters_student_marker_consistent",
        ),
        CheckConstraint(
            "(status = 'CURRENT' AND closed_at IS NULL AND reset_operation_id IS NULL) "
            "OR (status = 'CLOSED' AND closed_at IS NOT NULL "
            "AND reset_operation_id IS NOT NULL)",
            name="ck_semesters_boundary_state",
        ),
        Index(
            "uq_semesters_current",
            "status",
            unique=True,
            postgresql_where=text("status = 'CURRENT'"),
        ),
        Index("ix_semesters_reset_operation_id", "reset_operation_id"),
    )

    deleted_at = None

    status: Mapped[SemesterStatus] = mapped_column(
        Enum(
            SemesterStatus,
            name="semester_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=SemesterStatus.CURRENT,
        server_default=SemesterStatus.CURRENT.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.statement_timestamp(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_operation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{APPLICATION_SCHEMA}.semester_operations.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_semesters_reset_operation_id_semester_operations",
        ),
        nullable=True,
    )
    student_accounts_created: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    first_student_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @validates("started_at", "closed_at", "first_student_created_at")
    def validate_aware_datetime(
        self,
        key: str,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None:
            return _aware_utc(value, field_name=key.replace("_", " ").title())
        return None


class SemesterOperation(Base):
    """Attributable, durable metadata for one reset or restore workflow."""

    __tablename__ = "semester_operations"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(affected_counts) = 'object'",
            name="ck_semester_operations_affected_counts_object",
        ),
        CheckConstraint(
            "jsonb_typeof(result_summary) = 'object'",
            name="ck_semester_operations_result_summary_object",
        ),
        CheckConstraint(
            "failure_code IS NULL OR char_length(btrim(failure_code)) BETWEEN 1 AND 100",
            name="ck_semester_operations_failure_code_length",
        ),
        CheckConstraint(
            "(state = 'REQUESTED' AND started_at IS NULL AND completed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'RUNNING' AND started_at IS NOT NULL AND completed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'SUCCEEDED' AND started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'FAILED' AND completed_at IS NOT NULL AND failure_code IS NOT NULL)",
            name="ck_semester_operations_lifecycle",
        ),
        CheckConstraint(
            "(started_at IS NULL OR started_at >= requested_at) "
            "AND (completed_at IS NULL OR completed_at >= requested_at) "
            "AND (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)",
            name="ck_semester_operations_timestamp_order",
        ),
        Index("ix_semester_operations_semester_id", "semester_id"),
        Index("ix_semester_operations_admin_actor_id", "admin_actor_id"),
        Index("ix_semester_operations_backup_id", "backup_id"),
        Index("ix_semester_operations_state_requested_at", "state", "requested_at"),
        Index(
            "uq_semester_operations_running",
            "state",
            unique=True,
            postgresql_where=text("state = 'RUNNING'"),
        ),
    )

    deleted_at = None

    operation_type: Mapped[SemesterOperationType] = mapped_column(
        Enum(
            SemesterOperationType,
            name="semester_operation_type",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
    )
    state: Mapped[SemesterOperationState] = mapped_column(
        Enum(
            SemesterOperationState,
            name="semester_operation_state",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
        default=SemesterOperationState.REQUESTED,
        server_default=SemesterOperationState.REQUESTED.value,
    )
    semester_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.semesters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    admin_actor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    backup_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{APPLICATION_SCHEMA}.semester_backups.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_semester_operations_backup_id_semester_backups",
        ),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.statement_timestamp(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    affected_counts: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    failure_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    @validates("requested_at", "started_at", "completed_at")
    def validate_aware_datetime(
        self,
        key: str,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None:
            return _aware_utc(value, field_name=key.replace("_", " ").title())
        return None

    def start(self, *, at: datetime) -> None:
        """Move a requested operation into its single running state."""
        if self.state is not SemesterOperationState.REQUESTED:
            raise SemesterStateTransitionError("Semester operation cannot be started.")
        self.started_at = _aware_utc(at, field_name="Operation start time")
        self.state = SemesterOperationState.RUNNING

    def succeed(self, *, at: datetime, result_summary: dict[str, object] | None = None) -> None:
        """Complete a running operation successfully."""
        if self.state is not SemesterOperationState.RUNNING:
            raise SemesterStateTransitionError("Semester operation cannot succeed.")
        self.completed_at = _aware_utc(at, field_name="Operation completion time")
        self.result_summary = result_summary or {}
        self.failure_code = None
        self.state = SemesterOperationState.SUCCEEDED

    def fail(self, *, at: datetime, failure_code: str) -> None:
        """Fail a requested preflight or a running operation with a sanitized code."""
        if self.state not in {
            SemesterOperationState.REQUESTED,
            SemesterOperationState.RUNNING,
        }:
            raise SemesterStateTransitionError("Semester operation cannot fail.")
        code = failure_code.strip()
        if not 1 <= len(code) <= 100:
            raise ValueError("Semester operation failure code is invalid.")
        self.completed_at = _aware_utc(at, field_name="Operation failure time")
        self.failure_code = code
        self.state = SemesterOperationState.FAILED


class SemesterBackup(Base):
    """Private backup manifest metadata anchored to one source boundary."""

    __tablename__ = "semester_backups"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(database_row_counts) = 'object'",
            name="ck_semester_backups_database_row_counts_object",
        ),
        CheckConstraint(
            "avatar_object_count >= 0",
            name="ck_semester_backups_avatar_object_count_non_negative",
        ),
        CheckConstraint(
            "failure_code IS NULL OR char_length(btrim(failure_code)) BETWEEN 1 AND 100",
            name="ck_semester_backups_failure_code_length",
        ),
        CheckConstraint(
            "(state = 'CREATING' AND verified_at IS NULL AND failure_code IS NULL) OR "
            "(state IN ('READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED') "
            "AND verified_at IS NOT NULL AND expires_at IS NOT NULL "
            "AND database_manifest_location IS NOT NULL "
            "AND database_manifest_checksum IS NOT NULL "
            "AND avatar_manifest_location IS NOT NULL "
            "AND avatar_manifest_checksum IS NOT NULL AND failure_code IS NULL) OR "
            "(state = 'FAILED' AND failure_code IS NOT NULL)",
            name="ck_semester_backups_lifecycle",
        ),
        CheckConstraint(
            "(verified_at IS NULL OR verified_at >= source_boundary_at) "
            "AND (expires_at IS NULL OR verified_at IS NULL OR expires_at > verified_at) "
            "AND (restored_at IS NULL OR verified_at IS NOT NULL)",
            name="ck_semester_backups_timestamp_order",
        ),
        CheckConstraint(
            "(restored_at IS NULL AND restored_by_admin_id IS NULL "
            "AND restore_operation_id IS NULL) OR "
            "(restored_at IS NOT NULL AND restored_by_admin_id IS NOT NULL "
            "AND restore_operation_id IS NOT NULL)",
            name="ck_semester_backups_restore_metadata_complete",
        ),
        Index("ix_semester_backups_source_semester_id", "source_semester_id"),
        Index("ix_semester_backups_created_by_operation_id", "created_by_operation_id"),
        Index("ix_semester_backups_restored_by_admin_id", "restored_by_admin_id"),
        Index("ix_semester_backups_restore_operation_id", "restore_operation_id"),
        Index("ix_semester_backups_state_expires_at", "state", "expires_at"),
    )

    deleted_at = None

    source_semester_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.semesters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_boundary_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_operation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.semester_operations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    state: Mapped[SemesterBackupState] = mapped_column(
        Enum(
            SemesterBackupState,
            name="semester_backup_state",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
        default=SemesterBackupState.CREATING,
        server_default=SemesterBackupState.CREATING.value,
    )
    database_manifest_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    database_manifest_checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    database_row_counts: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    avatar_manifest_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_manifest_checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_object_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_by_admin_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    restore_operation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.semester_operations.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    failure_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    @validates(
        "source_boundary_at",
        "verified_at",
        "expires_at",
        "restored_at",
    )
    def validate_aware_datetime(
        self,
        key: str,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None:
            return _aware_utc(value, field_name=key.replace("_", " ").title())
        return None

    def transition_to(self, state: SemesterBackupState) -> None:
        """Apply only the durable state edges owned by the shared foundation."""
        allowed = {
            SemesterBackupState.CREATING: {
                SemesterBackupState.READY,
                SemesterBackupState.FAILED,
            },
            SemesterBackupState.READY: {
                SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
                SemesterBackupState.EXPIRED,
            },
            SemesterBackupState.RESTORE_BLOCKED_NEW_DATA: {
                SemesterBackupState.EXPIRED,
            },
            SemesterBackupState.EXPIRED: set(),
            SemesterBackupState.FAILED: set(),
        }
        if state not in allowed[self.state]:
            raise SemesterStateTransitionError("Semester backup transition is not allowed.")
        self.state = state
