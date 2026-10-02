"""SEM-007 server-authoritative lifecycle discovery and preparation bridge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from app.services.database_backup_storage import DatabaseBackupArtifactStore
from app.services.image_storage import ImageStorageService
from app.services.semester_avatar_backup import (
    AvatarBackupAdapter,
    AvatarBackupAlreadyAttachedError,
    AvatarBackupBusyError,
    create_semester_avatar_backup,
)
from app.services.semester_backup_verification import (
    SemesterBackupVerificationBusyError,
    effective_semester_backup_state,
    verify_semester_backup,
)
from app.services.semester_database_backup import (
    DatabaseBackupAlreadyAttachedError,
    DatabaseBackupBusyError,
    PostgresBinaryCopyBackupAdapter,
    create_semester_database_backup,
)

_PREPARE_LOCK_SQL: Final = (
    "SELECT pg_advisory_xact_lock(hashtextextended('vgu-buddy:semester-management:v1', 0))"
)
RestoreBlockReason = Literal[
    "NEW_COHORT",
    "EXPIRED",
    "NOT_READY",
    "ALREADY_RESTORED",
    "OPERATION_RUNNING",
]


class SemesterManagementError(RuntimeError):
    """Sanitized lifecycle bridge failure."""


class SemesterManagementConflictError(SemesterManagementError):
    """The requested lifecycle preparation is not currently eligible."""


@dataclass(frozen=True, slots=True)
class SemesterOperationStatus:
    id: UUID
    operation_type: SemesterOperationType
    state: SemesterOperationState
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None


@dataclass(frozen=True, slots=True)
class SemesterBackupStatus:
    id: UUID
    state: SemesterBackupState
    created_at: datetime
    verified_at: datetime | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class SemesterManagementStatus:
    current_semester_id: UUID
    current_semester_status: SemesterStatus
    current_student_accounts_created: int
    reset_operation: SemesterOperationStatus | None
    restore_operation: SemesterOperationStatus | None
    backup: SemesterBackupStatus | None
    can_prepare_reset: bool
    can_prepare_restore: bool
    restore_block_reason: RestoreBlockReason | None


def _require_admin(actor: User) -> None:
    if actor.role is not UserRole.ADMIN:
        raise SemesterManagementError("Semester management authorization failed.")


async def _database_clock(session: AsyncSession) -> datetime:
    now = await session.scalar(text("SELECT statement_timestamp()"))
    if not isinstance(now, datetime):
        raise SemesterManagementError("Semester management clock is unavailable.")
    return now


def _operation_status(operation: SemesterOperation | None) -> SemesterOperationStatus | None:
    if operation is None:
        return None
    return SemesterOperationStatus(
        id=operation.id,
        operation_type=operation.operation_type,
        state=operation.state,
        requested_at=operation.requested_at,
        started_at=operation.started_at,
        completed_at=operation.completed_at,
        failure_code=operation.failure_code,
    )


async def get_semester_management_status(
    session: AsyncSession,
    actor: User,
) -> SemesterManagementStatus:
    """Return the complete safe read model needed to reconstruct the Admin UI."""
    _require_admin(actor)
    current = await session.scalar(
        select(Semester).where(Semester.status == SemesterStatus.CURRENT)
    )
    if current is None:
        raise SemesterManagementError("Current semester is unavailable.")
    reset = await session.scalar(
        select(SemesterOperation)
        .where(SemesterOperation.operation_type == SemesterOperationType.RESET)
        .order_by(SemesterOperation.requested_at.desc())
        .limit(1)
    )
    backup = None
    if reset is not None and reset.backup_id is not None:
        backup = await session.get(SemesterBackup, reset.backup_id)
    restore = None
    if backup is not None:
        restore = await session.scalar(
            select(SemesterOperation)
            .where(
                SemesterOperation.operation_type == SemesterOperationType.RESTORE,
                SemesterOperation.backup_id == backup.id,
            )
            .order_by(SemesterOperation.requested_at.desc())
            .limit(1)
        )
    active = await session.scalar(
        select(SemesterOperation).where(SemesterOperation.state == SemesterOperationState.RUNNING)
    )
    now = await _database_clock(session)
    effective_state = effective_semester_backup_state(backup, now=now) if backup else None
    blocked: RestoreBlockReason | None = None
    if backup is not None and backup.restored_at is not None:
        blocked = "ALREADY_RESTORED"
    elif current.student_accounts_created > 0 or current.first_student_created_at is not None:
        blocked = "NEW_COHORT"
    elif effective_state is SemesterBackupState.EXPIRED:
        blocked = "EXPIRED"
    elif backup is not None and effective_state is not SemesterBackupState.READY:
        blocked = "NOT_READY"
    elif active is not None and active.operation_type is not SemesterOperationType.RESTORE:
        blocked = "OPERATION_RUNNING"

    backup_status = None
    if backup is not None and effective_state is not None:
        backup_status = SemesterBackupStatus(
            id=backup.id,
            state=effective_state,
            created_at=backup.created_at,
            verified_at=backup.verified_at,
            expires_at=backup.expires_at,
        )
    return SemesterManagementStatus(
        current_semester_id=current.id,
        current_semester_status=current.status,
        current_student_accounts_created=current.student_accounts_created,
        reset_operation=_operation_status(reset),
        restore_operation=_operation_status(restore),
        backup=backup_status,
        can_prepare_reset=active is None and current.reset_operation_id is None,
        can_prepare_restore=bool(
            backup is not None
            and reset is not None
            and reset.state is SemesterOperationState.SUCCEEDED
            and active is None
            and blocked is None
        ),
        restore_block_reason=blocked,
    )


async def _prepare_reset_metadata(
    session_factory: async_sessionmaker[AsyncSession], actor: User
) -> tuple[UUID, UUID]:
    async with session_factory() as session, session.begin():
        await session.execute(text(_PREPARE_LOCK_SQL))
        persisted_actor = await session.get(User, actor.id)
        if persisted_actor is None:
            raise SemesterManagementError("Semester management authorization failed.")
        _require_admin(persisted_actor)
        current = await session.scalar(
            select(Semester).where(Semester.status == SemesterStatus.CURRENT).with_for_update()
        )
        if current is None or current.reset_operation_id is not None:
            raise SemesterManagementConflictError("Semester reset preparation is not eligible.")
        running = await session.scalar(
            select(SemesterOperation).where(
                SemesterOperation.state == SemesterOperationState.RUNNING
            )
        )
        if running is not None:
            if (
                running.operation_type is SemesterOperationType.RESET
                and running.semester_id == current.id
                and running.admin_actor_id == actor.id
                and running.backup_id is not None
            ):
                return running.id, running.backup_id
            raise SemesterManagementConflictError("Another semester operation is running.")
        now = await _database_clock(session)
        operation = SemesterOperation(
            operation_type=SemesterOperationType.RESET,
            state=SemesterOperationState.RUNNING,
            semester_id=current.id,
            admin_actor_id=actor.id,
            requested_at=now,
            started_at=now,
        )
        session.add(operation)
        await session.flush()
        backup = SemesterBackup(
            source_semester_id=current.id,
            source_boundary_at=current.started_at,
            created_by_operation_id=operation.id,
        )
        session.add(backup)
        await session.flush()
        operation.backup_id = backup.id
        return operation.id, backup.id


async def prepare_semester_reset(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    actor: User,
    snapshot_adapter: PostgresBinaryCopyBackupAdapter,
    backup_storage: DatabaseBackupArtifactStore,
    avatar_storage: ImageStorageService,
) -> tuple[UUID, UUID]:
    """Create/reuse one reset aggregate and prepare its verified immutable backup."""
    try:
        operation_id, backup_id = await _prepare_reset_metadata(session_factory, actor)
    except IntegrityError as error:
        raise SemesterManagementConflictError("Another semester operation is running.") from error

    try:
        try:
            await create_semester_database_backup(
                session_factory,
                backup_id=backup_id,
                adapter=snapshot_adapter,
                storage=backup_storage,
            )
        except DatabaseBackupBusyError:
            return operation_id, backup_id
        except DatabaseBackupAlreadyAttachedError:
            pass
        try:
            await create_semester_avatar_backup(
                session_factory,
                backup_id=backup_id,
                adapter=AvatarBackupAdapter(avatar_storage),
                storage=backup_storage,
            )
        except AvatarBackupBusyError:
            return operation_id, backup_id
        except AvatarBackupAlreadyAttachedError:
            pass
        try:
            await verify_semester_backup(
                session_factory,
                backup_id=backup_id,
                storage=backup_storage,
            )
        except SemesterBackupVerificationBusyError:
            return operation_id, backup_id
    except Exception as error:
        async with session_factory() as session, session.begin():
            operation = await session.get(SemesterOperation, operation_id, with_for_update=True)
            if operation is not None and operation.state is SemesterOperationState.RUNNING:
                operation.fail(
                    at=await _database_clock(session), failure_code="RESET_PREPARATION_FAILED"
                )
        raise SemesterManagementError("Semester reset preparation failed safely.") from error
    return operation_id, backup_id


async def prepare_semester_restore(
    session_factory: async_sessionmaker[AsyncSession], actor: User
) -> tuple[UUID, UUID]:
    """Create/reuse one restore operation for the only eligible retained backup."""
    try:
        async with session_factory() as session, session.begin():
            await session.execute(text(_PREPARE_LOCK_SQL))
            persisted_actor = await session.get(User, actor.id)
            if persisted_actor is None:
                raise SemesterManagementError("Semester management authorization failed.")
            _require_admin(persisted_actor)
            current = await session.scalar(
                select(Semester).where(Semester.status == SemesterStatus.CURRENT).with_for_update()
            )
            if current is None:
                raise SemesterManagementConflictError(
                    "Semester restore preparation is unavailable."
                )
            running = await session.scalar(
                select(SemesterOperation).where(
                    SemesterOperation.state == SemesterOperationState.RUNNING
                )
            )
            if running is not None:
                if (
                    running.operation_type is SemesterOperationType.RESTORE
                    and running.admin_actor_id == actor.id
                    and running.backup_id is not None
                ):
                    return running.id, running.backup_id
                raise SemesterManagementConflictError("Another semester operation is running.")
            reset = await session.scalar(
                select(SemesterOperation)
                .where(
                    SemesterOperation.operation_type == SemesterOperationType.RESET,
                    SemesterOperation.state == SemesterOperationState.SUCCEEDED,
                )
                .order_by(SemesterOperation.completed_at.desc())
                .limit(1)
                .with_for_update()
            )
            backup = (
                await session.get(SemesterBackup, reset.backup_id, with_for_update=True)
                if reset is not None and reset.backup_id is not None
                else None
            )
            now = await _database_clock(session)
            if (
                reset is None
                or backup is None
                or effective_semester_backup_state(backup, now=now) is not SemesterBackupState.READY
                or backup.restored_at is not None
                or current.student_accounts_created > 0
                or current.first_student_created_at is not None
            ):
                raise SemesterManagementConflictError(
                    "Semester restore preparation is not eligible."
                )
            operation = SemesterOperation(
                operation_type=SemesterOperationType.RESTORE,
                state=SemesterOperationState.RUNNING,
                semester_id=reset.semester_id,
                admin_actor_id=actor.id,
                backup_id=backup.id,
                requested_at=now,
                started_at=now,
            )
            session.add(operation)
            await session.flush()
            return operation.id, backup.id
    except IntegrityError as error:
        raise SemesterManagementConflictError("Another semester operation is running.") from error
