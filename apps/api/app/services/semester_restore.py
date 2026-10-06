"""SEM-006 guarded restore orchestration and permanent new-cohort blocking."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast
from uuid import UUID

from sqlalchemy import select, text
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
from app.services.audit_logs import record_audit_log
from app.services.database_backup_storage import DatabaseBackupArtifactStore
from app.services.image_storage import ImageStorageService, StorageObjectRef
from app.services.passwords import verify_password
from app.services.semester_avatar_backup import (
    AvatarBackupError,
    AvatarBackupManifest,
    AvatarRestoreResult,
    load_avatar_backup_from_storage,
    restore_avatar_backup_idempotently,
)
from app.services.semester_backup_verification import (
    effective_semester_backup_state,
    validate_semester_backup_manifests,
)
from app.services.semester_database_backup import (
    DatabaseBackupError,
    DatabaseBackupManifest,
    PostgresBinaryCopyBackupAdapter,
    load_database_backup_from_storage,
)

SEMESTER_RESTORE_AUDIT_ACTION: Final = "semester.restore_execute"
SEMESTER_RESTORE_CONFIRMATION_PREFIX: Final = "RESTORE"
SEMESTER_RESTORE_BLOCKED_CODE: Final = "RESTORE_BLOCKED_NEW_DATA"
SEMESTER_RESTORE_EXPIRED_CODE: Final = "RESTORE_BACKUP_EXPIRED"
SEMESTER_RESTORE_ALEMBIC_HEAD: Final = "0021_restore_runtime_permissions"
SEMESTER_RESTORE_COMPATIBLE_MANIFEST_HEADS: Final = frozenset(
    {
        "0019_semester_reset_execution",
        "0020_semester_restore_execution",
        SEMESTER_RESTORE_ALEMBIC_HEAD,
    }
)
_WRITE_BARRIER_SQL: Final = (
    "SELECT pg_try_advisory_xact_lock(hashtextextended('vgu-buddy:semester-write-barrier:v1', 0))"
)


class SemesterRestoreError(RuntimeError):
    """Sanitized restore boundary failure."""


class SemesterRestoreAuthorizationError(SemesterRestoreError):
    """The active Admin failed the step-up check."""


class SemesterRestoreStateError(SemesterRestoreError):
    """Restore, semester, or backup state is not eligible."""


class SemesterRestoreBlockedError(SemesterRestoreStateError):
    """The monotonic current-semester marker permanently blocked this backup."""


class SemesterRestoreBusyError(SemesterRestoreError):
    """Another transaction owns the semester write barrier."""


class SemesterRestorePackageError(SemesterRestoreError):
    """A stored package failed exact validation or compatibility checks."""


class SemesterRestoreStorageError(SemesterRestoreError):
    """Exact avatar restoration did not finish safely."""


@dataclass(frozen=True, slots=True)
class SemesterRestorePreflight:
    operation_id: UUID
    backup_id: UUID
    source_semester_id: UUID
    current_semester_id: UUID
    backup_state: SemesterBackupState
    can_execute: bool
    can_finalize_new_cohort_block: bool
    restored_counts: dict[str, int]
    avatar_object_count: int
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class SemesterRestoreReport:
    operation_id: UUID
    backup_id: UUID
    source_semester_id: UUID
    restored_counts: dict[str, int]
    avatar_objects_restored: int
    operation_state: SemesterOperationState
    backup_state: SemesterBackupState
    idempotent_replay: bool


@dataclass(frozen=True, slots=True)
class _RestorePackage:
    manifest: DatabaseBackupManifest
    manifest_content: bytes
    artifact_path: Path
    avatar_manifest: AvatarBackupManifest
    avatar_manifest_content: bytes
    avatar_object_paths: dict[str, Path]


def semester_restore_confirmation_phrase(backup_id: UUID) -> str:
    """Return the exact stale-backup-resistant confirmation phrase."""
    return f"{SEMESTER_RESTORE_CONFIRMATION_PREFIX} {backup_id}"


def _require_admin(actor: User) -> None:
    if actor.role is not UserRole.ADMIN or not actor.is_active or actor.deleted_at is not None:
        raise SemesterRestoreAuthorizationError("Semester restore authorization failed.")


def _integer_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise SemesterRestoreStateError("Semester restore aggregate metadata is invalid.")
    counts: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or type(count) is not int or count < 0:
            raise SemesterRestoreStateError("Semester restore aggregate metadata is invalid.")
        counts[key] = count
    return counts


async def _database_clock(session: AsyncSession) -> datetime:
    value = await session.scalar(text("SELECT clock_timestamp()"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SemesterRestoreStateError("Database clock is unavailable.")
    return value.astimezone(UTC)


async def _current_semester(session: AsyncSession, *, lock: bool) -> Semester:
    statement = select(Semester).where(Semester.status == SemesterStatus.CURRENT)
    if lock:
        statement = statement.with_for_update()
    semester = await session.scalar(statement)
    if semester is None:
        raise SemesterRestoreStateError("Current semester is unavailable.")
    return semester


def _is_restore_identity_valid(
    operation: SemesterOperation,
    backup: SemesterBackup,
    source_semester: Semester,
    reset_operation: SemesterOperation,
    *,
    admin_id: UUID,
) -> bool:
    return bool(
        operation.operation_type is SemesterOperationType.RESTORE
        and operation.state is SemesterOperationState.RUNNING
        and operation.admin_actor_id == admin_id
        and operation.semester_id == source_semester.id
        and operation.backup_id == backup.id
        and source_semester.status is SemesterStatus.CLOSED
        and source_semester.reset_operation_id == reset_operation.id
        and backup.source_semester_id == source_semester.id
        and backup.source_boundary_at == source_semester.started_at
        and backup.created_by_operation_id == reset_operation.id
        and reset_operation.operation_type is SemesterOperationType.RESET
        and reset_operation.state is SemesterOperationState.SUCCEEDED
        and reset_operation.semester_id == source_semester.id
        and reset_operation.backup_id == backup.id
        and backup.state is SemesterBackupState.READY
        and backup.verified_at is not None
        and backup.expires_at is not None
        and backup.failure_code is None
        and backup.database_manifest_location is not None
        and backup.database_manifest_checksum is not None
        and backup.avatar_manifest_location is not None
        and backup.avatar_manifest_checksum is not None
        and backup.restored_at is None
        and backup.restored_by_admin_id is None
        and backup.restore_operation_id is None
    )


async def get_semester_restore_preflight(
    session: AsyncSession,
    actor: User,
    *,
    operation_id: UUID,
) -> SemesterRestorePreflight:
    """Return an aggregate-only view of one exact restore operation."""
    _require_admin(actor)
    operation = await session.scalar(
        select(SemesterOperation).where(SemesterOperation.id == operation_id)
    )
    if operation is None or operation.backup_id is None:
        raise SemesterRestoreStateError("Semester restore is not eligible.")
    backup = await session.scalar(
        select(SemesterBackup).where(SemesterBackup.id == operation.backup_id)
    )
    source = await session.scalar(select(Semester).where(Semester.id == operation.semester_id))
    if backup is None or source is None:
        raise SemesterRestoreStateError("Semester restore is not eligible.")
    reset = await session.scalar(
        select(SemesterOperation).where(SemesterOperation.id == backup.created_by_operation_id)
    )
    current = await _current_semester(session, lock=False)
    now = await _database_clock(session)
    effective_state = effective_semester_backup_state(backup, now=now)
    new_cohort_blocked = backup.restored_at is None and (
        current.student_accounts_created > 0 or current.first_student_created_at is not None
    )
    state = (
        SemesterBackupState.RESTORE_BLOCKED_NEW_DATA
        if new_cohort_blocked
        else effective_state
    )
    valid = reset is not None and _is_restore_identity_valid(
        operation,
        backup,
        source,
        reset,
        admin_id=actor.id,
    )
    return SemesterRestorePreflight(
        operation_id=operation.id,
        backup_id=backup.id,
        source_semester_id=source.id,
        current_semester_id=current.id,
        backup_state=state,
        can_execute=valid and state is SemesterBackupState.READY,
        can_finalize_new_cohort_block=(
            valid and new_cohort_blocked and effective_state is SemesterBackupState.READY
        ),
        restored_counts=_integer_counts(backup.database_row_counts),
        avatar_object_count=backup.avatar_object_count,
        confirmation_phrase=semester_restore_confirmation_phrase(backup.id),
    )


async def _load_restore_package(
    storage: DatabaseBackupArtifactStore,
    backup: SemesterBackup,
    root: Path,
) -> _RestorePackage:
    database_checksum = backup.database_manifest_checksum
    avatar_checksum = backup.avatar_manifest_checksum
    if database_checksum is None or avatar_checksum is None:
        raise SemesterRestoreStateError("Semester restore package metadata is incomplete.")
    try:
        (
            database_manifest,
            artifact_path,
            database_content,
        ) = await load_database_backup_from_storage(
            storage,
            backup_id=backup.id,
            manifest_checksum=database_checksum,
            workspace=root / "database",
        )
        avatar_manifest, object_paths, avatar_content = await load_avatar_backup_from_storage(
            storage,
            backup_id=backup.id,
            manifest_checksum=avatar_checksum,
            workspace=root / "avatars",
        )
        validate_semester_backup_manifests(
            backup,
            database_manifest,
            avatar_manifest,
            storage=storage,
        )
    except Exception:
        raise SemesterRestorePackageError("Semester restore package is invalid.") from None
    return _RestorePackage(
        manifest=database_manifest,
        manifest_content=database_content,
        artifact_path=artifact_path,
        avatar_manifest=avatar_manifest,
        avatar_manifest_content=avatar_content,
        avatar_object_paths=object_paths,
    )


async def _locked_context(
    session: AsyncSession,
    *,
    operation_id: UUID,
    backup_id: UUID,
    admin_id: UUID,
    current_password: str,
    confirmation_phrase: str,
) -> tuple[
    User,
    SemesterOperation,
    SemesterBackup,
    Semester,
    Semester,
    SemesterOperation,
    datetime,
    bool,
]:
    if not bool(await session.scalar(text(_WRITE_BARRIER_SQL))):
        raise SemesterRestoreBusyError("Another semester operation owns the write barrier.")
    actor = await session.scalar(select(User).where(User.id == admin_id).with_for_update())
    if actor is None:
        raise SemesterRestoreAuthorizationError("Semester restore authorization failed.")
    _require_admin(actor)
    if not verify_password(current_password, actor.password_hash):
        raise SemesterRestoreAuthorizationError("Semester restore authorization failed.")

    operation = await session.scalar(
        select(SemesterOperation).where(SemesterOperation.id == operation_id).with_for_update()
    )
    backup = await session.scalar(
        select(SemesterBackup).where(SemesterBackup.id == backup_id).with_for_update()
    )
    if operation is None or backup is None or operation.backup_id != backup.id:
        raise SemesterRestoreStateError("Semester restore is not eligible.")
    source = await session.scalar(
        select(Semester).where(Semester.id == operation.semester_id).with_for_update()
    )
    reset = await session.scalar(
        select(SemesterOperation)
        .where(SemesterOperation.id == backup.created_by_operation_id)
        .with_for_update()
    )
    current = await _current_semester(session, lock=True)
    now = await _database_clock(session)
    if source is None or reset is None:
        raise SemesterRestoreStateError("Semester restore is not eligible.")
    if confirmation_phrase != semester_restore_confirmation_phrase(backup.id):
        raise SemesterRestoreAuthorizationError("Semester restore authorization failed.")

    replay = operation.state is SemesterOperationState.SUCCEEDED
    if replay:
        if (
            operation.operation_type is not SemesterOperationType.RESTORE
            or operation.admin_actor_id != actor.id
            or operation.semester_id != source.id
            or backup.restored_by_admin_id != actor.id
            or backup.restore_operation_id != operation.id
            or backup.restored_at is None
            or backup.state not in {SemesterBackupState.READY, SemesterBackupState.EXPIRED}
        ):
            raise SemesterRestoreStateError("Completed semester restore metadata is invalid.")
        return actor, operation, backup, source, current, reset, now, True

    if not _is_restore_identity_valid(
        operation,
        backup,
        source,
        reset,
        admin_id=actor.id,
    ):
        raise SemesterRestoreStateError("Semester restore is not eligible.")
    return actor, operation, backup, source, current, reset, now, False


def _parse_restore_summary(value: object) -> tuple[UUID, dict[str, int], int]:
    if not isinstance(value, dict):
        raise SemesterRestoreStateError("Semester restore result metadata is invalid.")
    try:
        source_id = UUID(str(value["source_semester_id"]))
        counts = _integer_counts(value["restored"])
        avatars = value["avatar_objects_restored"]
    except (KeyError, TypeError, ValueError):
        raise SemesterRestoreStateError("Semester restore result metadata is invalid.") from None
    if type(avatars) is not int or avatars < 0:
        raise SemesterRestoreStateError("Semester restore result metadata is invalid.")
    return source_id, counts, avatars


async def _compensate_avatars(
    storage: ImageStorageService,
    references: tuple[StorageObjectRef, ...],
) -> None:
    for reference in reversed(references):
        try:
            await storage.delete_image(reference)
        except Exception:
            pass


async def _apply_locked_gate(
    session: AsyncSession,
    actor: User,
    operation: SemesterOperation,
    backup: SemesterBackup,
    current: Semester,
    *,
    now: datetime,
    replay: bool,
) -> str:
    if replay:
        return "replay"
    if current.student_accounts_created > 0 or current.first_student_created_at is not None:
        backup.transition_to(SemesterBackupState.RESTORE_BLOCKED_NEW_DATA)
        operation.fail(at=now, failure_code=SEMESTER_RESTORE_BLOCKED_CODE)
        await record_audit_log(
            session,
            actor,
            action=SEMESTER_RESTORE_AUDIT_ACTION,
            resource_type="semester_operation",
            resource_id=operation.id,
            new_value={"state": SemesterOperationState.FAILED.value},
            metadata={"failure_code": SEMESTER_RESTORE_BLOCKED_CODE},
        )
        return "blocked"
    if effective_semester_backup_state(backup, now=now) is not SemesterBackupState.READY:
        backup.transition_to(SemesterBackupState.EXPIRED)
        operation.fail(at=now, failure_code=SEMESTER_RESTORE_EXPIRED_CODE)
        return "expired"
    return "ready"


def _restore_report(
    *,
    operation_id: UUID,
    backup_id: UUID,
    summary: object,
    backup_state: SemesterBackupState,
    replay: bool,
) -> SemesterRestoreReport:
    source_id, restored_counts, avatars = _parse_restore_summary(summary)
    return SemesterRestoreReport(
        operation_id=operation_id,
        backup_id=backup_id,
        source_semester_id=source_id,
        restored_counts=restored_counts,
        avatar_objects_restored=avatars,
        operation_state=SemesterOperationState.SUCCEEDED,
        backup_state=backup_state,
        idempotent_replay=replay,
    )


async def execute_semester_restore(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    operation_id: UUID,
    backup_id: UUID,
    admin_id: UUID,
    current_password: str,
    confirmation_phrase: str,
    restore_adapter: PostgresBinaryCopyBackupAdapter,
    backup_storage: DatabaseBackupArtifactStore,
    avatar_storage: ImageStorageService,
) -> SemesterRestoreReport:
    """Restore one exact READY backup while its post-reset boundary is still empty."""
    summary: object = {}
    async with session_factory() as gate_session, gate_session.begin():
        (
            actor,
            operation,
            initial_backup,
            _source,
            current,
            _reset,
            now,
            replay,
        ) = await _locked_context(
            gate_session,
            operation_id=operation_id,
            backup_id=backup_id,
            admin_id=admin_id,
            current_password=current_password,
            confirmation_phrase=confirmation_phrase,
        )
        initial_state = await _apply_locked_gate(
            gate_session,
            actor,
            operation,
            initial_backup,
            current,
            now=now,
            replay=replay,
        )
        summary = operation.result_summary
        initial_persisted_state = initial_backup.state

    if initial_state == "blocked":
        raise SemesterRestoreBlockedError("New-semester data permanently blocked restore.")
    if initial_state == "expired":
        raise SemesterRestoreStateError("Expired semester backups cannot be restored.")
    if initial_state == "replay":
        return _restore_report(
            operation_id=operation_id,
            backup_id=backup_id,
            summary=summary,
            backup_state=initial_persisted_state,
            replay=True,
        )

    with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem006-package-") as temporary:
        package = await _load_restore_package(backup_storage, initial_backup, Path(temporary))
        newly_restored: tuple[StorageObjectRef, ...] = ()
        final_state = "ready"
        final_persisted_state = SemesterBackupState.READY
        try:
            async with session_factory() as session, session.begin():
                (
                    actor,
                    operation,
                    backup,
                    source,
                    current,
                    _reset,
                    now,
                    replay,
                ) = await _locked_context(
                    session,
                    operation_id=operation_id,
                    backup_id=backup_id,
                    admin_id=admin_id,
                    current_password=current_password,
                    confirmation_phrase=confirmation_phrase,
                )
                final_state = await _apply_locked_gate(
                    session,
                    actor,
                    operation,
                    backup,
                    current,
                    now=now,
                    replay=replay,
                )
                final_persisted_state = backup.state
                if final_state == "replay":
                    summary = operation.result_summary
                elif final_state == "ready":
                    if (
                        backup.database_manifest_checksum is None
                        or backup.avatar_manifest_checksum is None
                    ):
                        raise SemesterRestoreStateError(
                            "Semester restore package metadata is incomplete."
                        )
                    validate_semester_backup_manifests(
                        backup,
                        package.manifest,
                        package.avatar_manifest,
                        storage=backup_storage,
                    )
                    avatar_result: AvatarRestoreResult = await restore_avatar_backup_idempotently(
                        avatar_storage,
                        manifest_content=package.avatar_manifest_content,
                        object_paths=package.avatar_object_paths,
                        expected_manifest_checksum=backup.avatar_manifest_checksum,
                    )
                    newly_restored = avatar_result.newly_restored
                    sql_connection = await session.connection()
                    raw_connection = await sql_connection.get_raw_connection()
                    driver_connection = cast(Any, raw_connection.driver_connection)
                    restored_manifest = await restore_adapter.restore_into_transaction(
                        driver_connection,
                        manifest_content=package.manifest_content,
                        artifact_path=package.artifact_path,
                        expected_manifest_checksum=backup.database_manifest_checksum,
                        accepted_manifest_heads=SEMESTER_RESTORE_COMPATIBLE_MANIFEST_HEADS,
                        required_target_head=SEMESTER_RESTORE_ALEMBIC_HEAD,
                    )
                    restored_counts = _integer_counts(restored_manifest.row_counts)
                    restored_avatars = restored_manifest.row_counts.get("profile_photos")
                    if restored_avatars != avatar_result.manifest.object_count:
                        raise SemesterRestorePackageError(
                            "Semester restore package counts mismatched."
                        )
                    summary = {
                        "source_semester_id": str(source.id),
                        "restored": restored_counts,
                        "avatar_objects_restored": avatar_result.manifest.object_count,
                    }
                    backup.restored_at = now
                    backup.restored_by_admin_id = actor.id
                    backup.restore_operation_id = operation.id
                    operation.affected_counts = cast(dict[str, object], restored_counts)
                    operation.succeed(at=now, result_summary=summary)
                    await record_audit_log(
                        session,
                        actor,
                        action=SEMESTER_RESTORE_AUDIT_ACTION,
                        resource_type="semester_operation",
                        resource_id=operation.id,
                        new_value={"state": SemesterOperationState.SUCCEEDED.value},
                        metadata={
                            "source_semester_id": str(source.id),
                            "restored": restored_counts,
                            "avatar_objects_restored": avatar_result.manifest.object_count,
                        },
                    )
        except SemesterRestoreError:
            await _compensate_avatars(avatar_storage, newly_restored)
            raise
        except DatabaseBackupError:
            await _compensate_avatars(avatar_storage, newly_restored)
            raise SemesterRestorePackageError("Semester database restore failed safely.") from None
        except AvatarBackupError:
            await _compensate_avatars(avatar_storage, newly_restored)
            raise SemesterRestoreStorageError("Semester avatar restore failed safely.") from None
        except Exception:
            await _compensate_avatars(avatar_storage, newly_restored)
            raise SemesterRestoreError("Semester restore failed safely.") from None

        if final_state == "blocked":
            raise SemesterRestoreBlockedError("New-semester data permanently blocked restore.")
        if final_state == "expired":
            raise SemesterRestoreStateError("Expired semester backups cannot be restored.")

    return _restore_report(
        operation_id=operation_id,
        backup_id=backup_id,
        summary=summary,
        backup_state=final_persisted_state,
        replay=final_state == "replay",
    )
