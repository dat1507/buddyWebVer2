"""Private ADMIN contracts for safeguarded semester reset execution."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from app.models import (
    SemesterBackupState,
    SemesterOperationState,
    SemesterOperationType,
    SemesterStatus,
)
from app.services.passwords import BCRYPT_MAX_PASSWORD_BYTES


class SemesterResetExecuteRequest(BaseModel):
    """Explicit step-up and stable identities for one destructive execution."""

    model_config = ConfigDict(extra="forbid")

    backup_id: UUID
    confirmation_phrase: StrictStr = Field(min_length=1, max_length=64)
    current_password: StrictStr = Field(
        min_length=1,
        max_length=BCRYPT_MAX_PASSWORD_BYTES,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class SemesterResetPreflightResponse(BaseModel):
    """Aggregate-only destructive scope and authoritative gate state."""

    model_config = ConfigDict(extra="forbid")

    semester_id: UUID
    operation_id: UUID | None
    backup_id: UUID | None
    backup_state: SemesterBackupState | None
    backup_verified: bool
    can_execute: bool
    affected_counts: dict[str, int]
    preserved_counts: dict[str, int]
    confirmation_phrase: str
    retention_days: Literal[30] = 30


class SemesterResetExecuteResponse(BaseModel):
    """Safe terminal summary without row identities or private object paths."""

    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    backup_id: UUID
    closed_semester_id: UUID
    new_semester_id: UUID
    deleted_counts: dict[str, int]
    avatar_objects_processed: int = Field(ge=0)
    operation_state: SemesterOperationState
    backup_state: SemesterBackupState
    idempotent_replay: bool


class SemesterRestoreExecuteRequest(BaseModel):
    """Explicit step-up and stable backup identity for one restore."""

    model_config = ConfigDict(extra="forbid")

    backup_id: UUID
    confirmation_phrase: StrictStr = Field(min_length=1, max_length=64)
    current_password: StrictStr = Field(
        min_length=1,
        max_length=BCRYPT_MAX_PASSWORD_BYTES,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class SemesterRestorePreflightResponse(BaseModel):
    """Aggregate-only restore eligibility and exact confirmation phrase."""

    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    backup_id: UUID
    source_semester_id: UUID
    current_semester_id: UUID
    backup_state: SemesterBackupState
    can_execute: bool
    can_finalize_new_cohort_block: bool
    restored_counts: dict[str, int]
    avatar_object_count: int = Field(ge=0)
    confirmation_phrase: str


class SemesterRestoreExecuteResponse(BaseModel):
    """Safe terminal restore summary without row or object identities."""

    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    backup_id: UUID
    source_semester_id: UUID
    restored_counts: dict[str, int]
    avatar_objects_restored: int = Field(ge=0)
    operation_state: SemesterOperationState
    backup_state: SemesterBackupState
    idempotent_replay: bool


class SemesterOperationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    operation_type: SemesterOperationType
    state: SemesterOperationState
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None


class SemesterBackupStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    state: SemesterBackupState
    created_at: datetime
    verified_at: datetime | None
    expires_at: datetime | None


class SemesterManagementStatusResponse(BaseModel):
    """Private reload-safe lifecycle projection without storage or database internals."""

    model_config = ConfigDict(extra="forbid")

    current_semester_id: UUID
    current_semester_status: SemesterStatus
    current_student_accounts_created: int = Field(ge=0)
    reset_operation: SemesterOperationStatusResponse | None
    restore_operation: SemesterOperationStatusResponse | None
    backup: SemesterBackupStatusResponse | None
    can_prepare_reset: bool
    can_prepare_restore: bool
    restore_block_reason: (
        Literal[
            "NEW_COHORT",
            "EXPIRED",
            "NOT_READY",
            "ALREADY_RESTORED",
            "OPERATION_RUNNING",
        ]
        | None
    )


class SemesterOperationPreparedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: UUID
    backup_id: UUID
