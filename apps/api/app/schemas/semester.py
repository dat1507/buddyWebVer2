"""Private ADMIN contracts for safeguarded semester reset execution."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from app.models import SemesterBackupState, SemesterOperationState
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
