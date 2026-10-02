"""SEM-004 combined verification, effective expiry, and private artifact cleanup."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    SemesterBackup,
    SemesterBackupState,
    SemesterOperation,
    SemesterOperationState,
    SemesterOperationType,
    semester_backup_expires_at,
)
from app.services.database_backup_storage import (
    BackupStorageObjectRef,
    DatabaseBackupArtifactStore,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
    DatabaseBackupStorageNotFoundError,
)
from app.services.semester_avatar_backup import (
    AVATAR_BACKUP_MANIFEST_NAME,
    AvatarBackupBinaryRef,
    AvatarBackupManifest,
    AvatarBackupManifestRef,
    AvatarBackupValidationError,
    load_avatar_backup_from_storage,
    validate_avatar_backup_manifest,
)
from app.services.semester_database_backup import (
    DatabaseBackupManifest,
    DatabaseBackupValidationError,
    load_database_backup_from_storage,
    mark_semester_backup_failed,
    validate_database_backup_manifest,
)

BACKUP_VERIFICATION_FAILURE_CODE: Final = "BACKUP_VERIFICATION_FAILED"
DEFAULT_BACKUP_EXPIRY_BATCH_SIZE: Final = 20
MAX_BACKUP_EXPIRY_BATCH_SIZE: Final = 100


class SemesterBackupVerificationError(RuntimeError):
    """Sanitized failure at the combined backup-verification boundary."""


class SemesterBackupVerificationBusyError(SemesterBackupVerificationError):
    """Another worker owns the verification transaction."""


class SemesterBackupStateError(SemesterBackupVerificationError):
    """The requested operation is invalid for the persisted lifecycle."""


class SemesterBackupPackageError(SemesterBackupVerificationError):
    """A required private artifact or cross-manifest invariant is invalid."""


class SemesterBackupExpiryError(RuntimeError):
    """Sanitized expiry/cleanup failure."""


class SemesterBackupExpiryValidationError(ValueError):
    """The expiry job received an unsafe bound or test timestamp."""


@dataclass(frozen=True, slots=True)
class SemesterBackupVerificationReport:
    """Aggregate-only result with effective state and immutable retention metadata."""

    backup_id: UUID
    persisted_state: SemesterBackupState
    effective_state: SemesterBackupState
    verified_at: datetime | None
    expires_at: datetime | None
    database_rows: int
    avatar_objects: int
    newly_verified: bool
    newly_ready: bool


@dataclass(frozen=True, slots=True)
class SemesterBackupExpiryReport:
    """Safe aggregate result from one bounded physical-cleanup batch."""

    selected: int
    expired: int
    cleaned: int
    failed: int


def _utc_instant(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SemesterBackupExpiryValidationError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


def effective_semester_backup_state(
    backup: SemesterBackup,
    *,
    now: datetime,
) -> SemesterBackupState:
    """Apply the inclusive expiry boundary without waiting for physical cleanup."""
    current = _utc_instant(now, field_name="Backup state timestamp")
    if backup.state in {
        SemesterBackupState.READY,
        SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
    }:
        if backup.expires_at is None:
            raise SemesterBackupStateError("Semester backup retention metadata is incomplete.")
        if current >= backup.expires_at.astimezone(UTC):
            return SemesterBackupState.EXPIRED
    return backup.state


def _avatar_identity_from_database(
    manifest: DatabaseBackupManifest,
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            item.photo_id,
            item.profile_id,
            item.owner_user_id,
            item.bucket,
            item.object_key,
            item.mime_type,
            item.byte_size,
            item.width,
            item.height,
        )
        for item in manifest.avatar_references
    )


def _avatar_identity_from_avatar(manifest: AvatarBackupManifest) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            item.photo_id,
            item.profile_id,
            item.owner_user_id,
            item.source_bucket,
            item.source_object_key,
            item.mime_type,
            item.byte_size,
            item.width,
            item.height,
        )
        for item in manifest.objects
    )


def validate_semester_backup_manifests(
    backup: SemesterBackup,
    database_manifest: DatabaseBackupManifest,
    avatar_manifest: AvatarBackupManifest,
    *,
    storage: DatabaseBackupArtifactStore,
) -> None:
    """Validate exact metadata, scope, compatibility link, and artifact identity."""
    database_ref = DatabaseBackupObjectRef(backup.id, DatabaseBackupObjectKind.MANIFEST)
    database_artifact_ref = DatabaseBackupObjectRef(
        backup.id,
        DatabaseBackupObjectKind.ARTIFACT,
    )
    avatar_ref = AvatarBackupManifestRef(backup.id)
    if (
        database_manifest.backup_id != backup.id
        or avatar_manifest.backup_id != backup.id
        or database_manifest.source_semester_id != backup.source_semester_id
        or avatar_manifest.source_semester_id != backup.source_semester_id
        or database_manifest.source_boundary_at != backup.source_boundary_at
        or avatar_manifest.source_boundary_at != backup.source_boundary_at
        or database_manifest.artifact_location != storage.location(database_artifact_ref)
        or backup.database_manifest_location != storage.location(database_ref)
        or backup.avatar_manifest_location != storage.location(avatar_ref)
        or avatar_manifest.database_manifest_checksum != backup.database_manifest_checksum
        or database_manifest.row_counts != backup.database_row_counts
        or avatar_manifest.object_count != backup.avatar_object_count
        or database_manifest.row_counts.get("profile_photos") != backup.avatar_object_count
        or _avatar_identity_from_database(database_manifest)
        != _avatar_identity_from_avatar(avatar_manifest)
    ):
        raise SemesterBackupPackageError("Semester backup package linkage is invalid.")


async def _assert_database_compatibility(
    session: AsyncSession,
    manifest: DatabaseBackupManifest,
) -> None:
    server_version = await session.scalar(text("SELECT current_setting('server_version_num')"))
    alembic_head = await session.scalar(text("SELECT version_num FROM alembic_version"))
    try:
        server_major = int(str(server_version)) // 10000
    except (TypeError, ValueError):
        raise SemesterBackupPackageError(
            "Database compatibility metadata is unavailable."
        ) from None
    if (
        server_major != manifest.compatibility.required_target_postgresql_major
        or alembic_head != manifest.compatibility.required_alembic_head
    ):
        raise SemesterBackupPackageError("Database backup compatibility is invalid.")


def _require_attached_package(backup: SemesterBackup) -> tuple[str, str]:
    if (
        backup.database_manifest_location is None
        or backup.database_manifest_checksum is None
        or not backup.database_row_counts
        or backup.avatar_manifest_location is None
        or backup.avatar_manifest_checksum is None
        or backup.avatar_object_count < 0
    ):
        raise SemesterBackupPackageError("Semester backup metadata is incomplete.")
    return backup.database_manifest_checksum, backup.avatar_manifest_checksum


async def _database_clock(session: AsyncSession) -> datetime:
    value = await session.scalar(text("SELECT clock_timestamp()"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SemesterBackupVerificationError("Database clock is unavailable.")
    return value.astimezone(UTC)


def _report(
    backup: SemesterBackup,
    *,
    now: datetime,
    newly_verified: bool,
    newly_ready: bool,
) -> SemesterBackupVerificationReport:
    row_counts = tuple(backup.database_row_counts.values())
    if any(type(value) is not int or value < 0 for value in row_counts):
        raise SemesterBackupStateError("Semester backup row-count metadata is invalid.")
    return SemesterBackupVerificationReport(
        backup_id=backup.id,
        persisted_state=backup.state,
        effective_state=effective_semester_backup_state(backup, now=now),
        verified_at=backup.verified_at,
        expires_at=backup.expires_at,
        database_rows=sum(value for value in row_counts if isinstance(value, int)),
        avatar_objects=backup.avatar_object_count,
        newly_verified=newly_verified,
        newly_ready=newly_ready,
    )


async def verify_semester_backup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    backup_id: UUID,
    storage: DatabaseBackupArtifactStore,
) -> SemesterBackupVerificationReport:
    """Verify both packages and finalize READY only from persisted reset completion."""
    try:
        async with session_factory() as session, session.begin():
            locked = bool(
                await session.scalar(
                    text(
                        "SELECT pg_try_advisory_xact_lock(hashtextextended(CAST(:id AS text), 0))"
                    ),
                    {"id": str(backup_id)},
                )
            )
            if not locked:
                raise SemesterBackupVerificationBusyError(
                    "Semester backup verification is already running."
                )
            backup = await session.scalar(
                select(SemesterBackup).where(SemesterBackup.id == backup_id).with_for_update()
            )
            if backup is None:
                raise SemesterBackupStateError("Semester backup does not exist.")
            now = await _database_clock(session)
            if backup.state in {
                SemesterBackupState.READY,
                SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
                SemesterBackupState.EXPIRED,
            }:
                return _report(
                    backup,
                    now=now,
                    newly_verified=False,
                    newly_ready=False,
                )
            if backup.state is SemesterBackupState.FAILED:
                raise SemesterBackupStateError("Failed semester backups cannot be retried.")
            database_checksum, avatar_checksum = _require_attached_package(backup)
            operation = await session.scalar(
                select(SemesterOperation)
                .where(SemesterOperation.id == backup.created_by_operation_id)
                .with_for_update()
            )
            if (
                operation is None
                or operation.operation_type is not SemesterOperationType.RESET
                or operation.semester_id != backup.source_semester_id
                or operation.state
                not in {SemesterOperationState.RUNNING, SemesterOperationState.SUCCEEDED}
                or operation.backup_id not in {None, backup.id}
                or (
                    operation.state is SemesterOperationState.SUCCEEDED
                    and operation.backup_id != backup.id
                )
            ):
                raise SemesterBackupStateError("Reset operation is not eligible for verification.")

            with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem004-verify-") as temporary:
                root = Path(temporary)
                database_manifest, _, _ = await load_database_backup_from_storage(
                    storage,
                    backup_id=backup.id,
                    manifest_checksum=database_checksum,
                    workspace=root / "database",
                )
                avatar_manifest, _, _ = await load_avatar_backup_from_storage(
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
                await _assert_database_compatibility(session, database_manifest)

            verified_now = await _database_clock(session)
            newly_verified = backup.verified_at is None
            if newly_verified:
                backup.verified_at = verified_now
            if operation.backup_id is None:
                operation.backup_id = backup.id

            newly_ready = False
            if operation.state is SemesterOperationState.SUCCEEDED:
                if operation.completed_at is None or operation.backup_id != backup.id:
                    raise SemesterBackupStateError("Reset completion metadata is incomplete.")
                expires_at = semester_backup_expires_at(operation.completed_at)
                if verified_now >= expires_at:
                    raise SemesterBackupPackageError("Semester backup retention already elapsed.")
                backup.expires_at = expires_at
                backup.transition_to(SemesterBackupState.READY)
                newly_ready = True

            return _report(
                backup,
                now=verified_now,
                newly_verified=newly_verified,
                newly_ready=newly_ready,
            )
    except Exception as error:
        if isinstance(error, (SemesterBackupVerificationBusyError, SemesterBackupStateError)):
            raise
        try:
            async with session_factory() as failure_session:
                await mark_semester_backup_failed(
                    failure_session,
                    backup_id,
                    failure_code=BACKUP_VERIFICATION_FAILURE_CODE,
                )
        except Exception:
            pass
        if isinstance(error, SemesterBackupVerificationError):
            raise
        raise SemesterBackupPackageError("Semester backup verification failed.") from None


async def _read_optional_manifest(
    storage: DatabaseBackupArtifactStore,
    reference: BackupStorageObjectRef,
    target: Path,
) -> bytes | None:
    try:
        await storage.get_file(reference, target)
    except DatabaseBackupStorageNotFoundError:
        return None
    try:
        return target.read_bytes()
    except OSError as error:
        raise SemesterBackupExpiryError("Semester backup cleanup failed.") from error


def _validate_partial_cleanup_manifests(
    backup: SemesterBackup,
    database_manifest: DatabaseBackupManifest | None,
    avatar_manifest: AvatarBackupManifest | None,
    *,
    storage: DatabaseBackupArtifactStore,
) -> tuple[AvatarBackupBinaryRef, ...]:
    database_manifest_ref = DatabaseBackupObjectRef(
        backup.id,
        DatabaseBackupObjectKind.MANIFEST,
    )
    database_artifact_ref = DatabaseBackupObjectRef(
        backup.id,
        DatabaseBackupObjectKind.ARTIFACT,
    )
    avatar_manifest_ref = AvatarBackupManifestRef(backup.id)
    if (
        backup.database_manifest_location != storage.location(database_manifest_ref)
        or backup.avatar_manifest_location != storage.location(avatar_manifest_ref)
        or (
            database_manifest is not None
            and database_manifest.artifact_location != storage.location(database_artifact_ref)
        )
    ):
        raise SemesterBackupExpiryError("Semester backup cleanup identity is invalid.")
    if database_manifest is not None and avatar_manifest is not None:
        validate_semester_backup_manifests(
            backup,
            database_manifest,
            avatar_manifest,
            storage=storage,
        )
    elif database_manifest is not None:
        if (
            database_manifest.backup_id != backup.id
            or database_manifest.source_semester_id != backup.source_semester_id
            or database_manifest.source_boundary_at != backup.source_boundary_at
            or database_manifest.row_counts != backup.database_row_counts
            or len(database_manifest.avatar_references) != backup.avatar_object_count
        ):
            raise SemesterBackupExpiryError("Semester backup cleanup manifest is invalid.")
    elif avatar_manifest is not None:
        if (
            avatar_manifest.backup_id != backup.id
            or avatar_manifest.source_semester_id != backup.source_semester_id
            or avatar_manifest.source_boundary_at != backup.source_boundary_at
            or avatar_manifest.database_manifest_checksum != backup.database_manifest_checksum
            or avatar_manifest.object_count != backup.avatar_object_count
        ):
            raise SemesterBackupExpiryError("Semester backup cleanup manifest is invalid.")

    if database_manifest is not None:
        return tuple(
            AvatarBackupBinaryRef(backup.id, item.photo_id, item.mime_type)
            for item in database_manifest.avatar_references
        )
    if avatar_manifest is not None:
        return tuple(
            AvatarBackupBinaryRef(backup.id, item.photo_id, item.mime_type)
            for item in avatar_manifest.objects
        )
    return ()


async def _cleanup_expired_backup_artifacts(
    storage: DatabaseBackupArtifactStore,
    backup: SemesterBackup,
    *,
    workspace: Path,
) -> None:
    database_checksum, avatar_checksum = _require_attached_package(backup)
    database_manifest_ref = DatabaseBackupObjectRef(
        backup.id,
        DatabaseBackupObjectKind.MANIFEST,
    )
    avatar_manifest_ref = AvatarBackupManifestRef(backup.id)
    database_content = await _read_optional_manifest(
        storage,
        database_manifest_ref,
        workspace / "database-manifest.json",
    )
    avatar_content = await _read_optional_manifest(
        storage,
        avatar_manifest_ref,
        workspace / AVATAR_BACKUP_MANIFEST_NAME,
    )
    try:
        database_manifest = (
            validate_database_backup_manifest(
                database_content,
                expected_backup_id=backup.id,
                expected_manifest_checksum=database_checksum,
            )
            if database_content is not None
            else None
        )
        avatar_manifest = (
            validate_avatar_backup_manifest(
                avatar_content,
                expected_backup_id=backup.id,
                expected_manifest_checksum=avatar_checksum,
            )
            if avatar_content is not None
            else None
        )
    except (
        AvatarBackupValidationError,
        DatabaseBackupValidationError,
        SemesterBackupVerificationError,
    ) as error:
        raise SemesterBackupExpiryError("Semester backup cleanup manifest is invalid.") from error
    avatar_refs = _validate_partial_cleanup_manifests(
        backup,
        database_manifest,
        avatar_manifest,
        storage=storage,
    )
    for reference in avatar_refs:
        await storage.delete(reference)
    await storage.delete(DatabaseBackupObjectRef(backup.id, DatabaseBackupObjectKind.ARTIFACT))
    await storage.delete(database_manifest_ref)
    await storage.delete(avatar_manifest_ref)


async def process_expired_semester_backup_batch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    storage: DatabaseBackupArtifactStore,
    batch_size: int = DEFAULT_BACKUP_EXPIRY_BATCH_SIZE,
    expiry_now: datetime | None = None,
) -> SemesterBackupExpiryReport:
    """Delete exact due artifacts under row locks, then persist EXPIRED."""
    if not 1 <= batch_size <= MAX_BACKUP_EXPIRY_BATCH_SIZE:
        raise SemesterBackupExpiryValidationError(
            "Semester backup expiry batch size is outside the supported range."
        )
    cutoff = _utc_instant(expiry_now, field_name="Backup expiry timestamp") if expiry_now else None
    selected = expired = cleaned = failed = 0
    failed_ids: set[UUID] = set()
    while selected < batch_size:
        selected_id: UUID | None = None
        try:
            async with session_factory() as session, session.begin():
                now_expression = cutoff if cutoff is not None else func.statement_timestamp()
                statement = (
                    select(SemesterBackup)
                    .where(
                        SemesterBackup.state.in_(
                            (
                                SemesterBackupState.READY,
                                SemesterBackupState.RESTORE_BLOCKED_NEW_DATA,
                            )
                        ),
                        SemesterBackup.expires_at.is_not(None),
                        SemesterBackup.expires_at <= now_expression,
                    )
                    .order_by(SemesterBackup.expires_at, SemesterBackup.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if failed_ids:
                    statement = statement.where(SemesterBackup.id.not_in(failed_ids))
                backup = await session.scalar(statement)
                if backup is None:
                    break
                selected_id = backup.id
                selected += 1
                with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem004-expiry-") as temporary:
                    await _cleanup_expired_backup_artifacts(
                        storage,
                        backup,
                        workspace=Path(temporary),
                    )
                backup.transition_to(SemesterBackupState.EXPIRED)
            expired += 1
            cleaned += 1
        except Exception:
            if selected_id is None:
                raise SemesterBackupExpiryError("Semester backup expiry failed.") from None
            failed_ids.add(selected_id)
            failed += 1
    return SemesterBackupExpiryReport(
        selected=selected,
        expired=expired,
        cleaned=cleaned,
        failed=failed,
    )
