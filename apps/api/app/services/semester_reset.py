"""SEM-005 guarded semester reset orchestration and aggregate preflight."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final
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
from app.services.database_backup_storage import (
    DatabaseBackupArtifactStore,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)
from app.services.passwords import verify_password
from app.services.semester_avatar_backup import (
    AvatarBackupManifest,
    AvatarBackupManifestRef,
    validate_avatar_backup_manifest,
)
from app.services.semester_backup_verification import (
    SemesterBackupVerificationError,
    SemesterBackupVerificationReport,
    validate_semester_backup_manifests,
    verify_semester_backup,
)
from app.services.semester_database_backup import (
    DatabaseBackupManifest,
    PostgresBinaryCopyBackupAdapter,
    validate_database_backup_manifest,
)

SEMESTER_RESET_AUDIT_ACTION: Final = "semester.reset_execute"
SEMESTER_RESET_CONFIRMATION_PREFIX: Final = "RESET"
SEMESTER_RESET_FAILURE_CODE: Final = "SEMESTER_RESET_FAILED"
_WRITE_BARRIER_SQL: Final = (
    "SELECT pg_try_advisory_xact_lock(hashtextextended('vgu-buddy:semester-write-barrier:v1', 0))"
)

_COUNT_SQL: Final = """
SELECT jsonb_build_object(
    'users', (
        SELECT count(*) FROM app_private.users
        WHERE role = 'USER' AND semester_id = :semester_id
    ),
    'email_verification_tokens', (
        SELECT count(*) FROM app_private.email_verification_tokens
        WHERE user_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    ),
    'refresh_sessions', (
        SELECT count(*) FROM app_private.refresh_sessions
        WHERE user_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    ),
    'student_profiles', (
        SELECT count(*) FROM app_private.student_profiles
        WHERE user_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    ),
    'profile_photos', (
        SELECT count(*) FROM app_private.profile_photos
        WHERE profile_id IN (
            SELECT profile.id FROM app_private.student_profiles AS profile
            JOIN app_private.users AS owner ON owner.id = profile.user_id
            WHERE owner.role = 'USER' AND owner.semester_id = :semester_id
        )
    ),
    'profile_interests', (
        SELECT count(*) FROM app_private.profile_interests
        WHERE profile_id IN (
            SELECT profile.id FROM app_private.student_profiles AS profile
            JOIN app_private.users AS owner ON owner.id = profile.user_id
            WHERE owner.role = 'USER' AND owner.semester_id = :semester_id
        )
    ),
    'profile_languages', (
        SELECT count(*) FROM app_private.profile_languages
        WHERE profile_id IN (
            SELECT profile.id FROM app_private.student_profiles AS profile
            JOIN app_private.users AS owner ON owner.id = profile.user_id
            WHERE owner.role = 'USER' AND owner.semester_id = :semester_id
        )
    ),
    'profile_activities', (
        SELECT count(*) FROM app_private.profile_activities
        WHERE profile_id IN (
            SELECT profile.id FROM app_private.student_profiles AS profile
            JOIN app_private.users AS owner ON owner.id = profile.user_id
            WHERE owner.role = 'USER' AND owner.semester_id = :semester_id
        )
    ),
    'profile_custom_preferences', (
        SELECT count(*) FROM app_private.profile_custom_preferences
        WHERE profile_id IN (
            SELECT profile.id FROM app_private.student_profiles AS profile
            JOIN app_private.users AS owner ON owner.id = profile.user_id
            WHERE owner.role = 'USER' AND owner.semester_id = :semester_id
        )
    ),
    'event_registrations', (
        SELECT count(*) FROM app_private.event_registrations
        WHERE user_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    ),
    'matching_invitations', (
        SELECT count(*) FROM app_private.matching_invitations
        WHERE sender_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        ) OR recipient_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    ),
    'matches', (
        SELECT count(*) FROM app_private.matches WHERE semester_id = :semester_id
    ),
    'buddy_conversations', (
        SELECT count(*) FROM app_private.buddy_conversations
        WHERE semester_id = :semester_id
    ),
    'buddy_messages', (
        SELECT count(*) FROM app_private.buddy_messages
        WHERE conversation_id IN (
            SELECT id FROM app_private.buddy_conversations
            WHERE semester_id = :semester_id
        )
    ),
    'transactional_outbox', (
        SELECT count(*) FROM app_private.transactional_outbox
        WHERE recipient_user_id IN (
            SELECT id FROM app_private.users
            WHERE role = 'USER' AND semester_id = :semester_id
        )
    )
)
"""

_PRESERVED_COUNT_SQL: Final = """
SELECT jsonb_build_object(
    'admins', (SELECT count(*) FROM app_private.users WHERE role = 'ADMIN'),
    'interests', (SELECT count(*) FROM app_private.interests),
    'languages', (SELECT count(*) FROM app_private.languages),
    'activities', (SELECT count(*) FROM app_private.activities),
    'semester_backups', (SELECT count(*) FROM app_private.semester_backups),
    'semester_operations', (SELECT count(*) FROM app_private.semester_operations)
)
"""


class SemesterResetError(RuntimeError):
    """Sanitized reset boundary failure."""


class SemesterResetAuthorizationError(SemesterResetError):
    """The active Admin failed the destructive step-up check."""


class SemesterResetStateError(SemesterResetError):
    """Reset, semester, or backup state is not eligible."""


class SemesterResetBusyError(SemesterResetError):
    """Another transaction owns the exclusive reset barrier."""


class SemesterResetSnapshotError(SemesterResetError):
    """The current cohort no longer matches its verified backup."""


class SemesterResetStorageError(SemesterResetError):
    """Exact managed-avatar cleanup did not finish."""


@dataclass(frozen=True, slots=True)
class SemesterResetPreflight:
    semester_id: UUID
    operation_id: UUID | None
    backup_id: UUID | None
    backup_state: SemesterBackupState | None
    backup_verified: bool
    can_execute: bool
    affected_counts: dict[str, int]
    preserved_counts: dict[str, int]
    confirmation_phrase: str


@dataclass(frozen=True, slots=True)
class SemesterResetReport:
    operation_id: UUID
    backup_id: UUID
    closed_semester_id: UUID
    new_semester_id: UUID
    deleted_counts: dict[str, int]
    avatar_objects_processed: int
    operation_state: SemesterOperationState
    backup_state: SemesterBackupState
    idempotent_replay: bool


def semester_reset_confirmation_phrase(semester_id: UUID) -> str:
    """Return the exact stale-boundary-resistant destructive phrase."""
    return f"{SEMESTER_RESET_CONFIRMATION_PREFIX} {semester_id}"


def _require_admin(actor: User) -> None:
    if actor.role is not UserRole.ADMIN or not actor.is_active or actor.deleted_at is not None:
        raise SemesterResetAuthorizationError("Semester reset authorization failed.")


def _integer_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise SemesterResetStateError("Semester reset aggregate metadata is invalid.")
    counts: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or type(count) is not int or count < 0:
            raise SemesterResetStateError("Semester reset aggregate metadata is invalid.")
        counts[key] = count
    return counts


async def _aggregate_counts(session: AsyncSession, semester_id: UUID) -> dict[str, int]:
    value = await session.scalar(text(_COUNT_SQL), {"semester_id": semester_id})
    return _integer_counts(value)


async def _preserved_counts(session: AsyncSession) -> dict[str, int]:
    return _integer_counts(await session.scalar(text(_PRESERVED_COUNT_SQL)))


def _is_reset_execution_eligible(
    operation: SemesterOperation,
    backup: SemesterBackup,
    semester: Semester,
    *,
    admin_id: UUID,
) -> bool:
    """Apply the complete pre-delete gate without touching external storage."""
    return bool(
        operation.operation_type is SemesterOperationType.RESET
        and operation.state is SemesterOperationState.RUNNING
        and operation.admin_actor_id == admin_id
        and operation.semester_id == semester.id
        and operation.backup_id == backup.id
        and semester.status is SemesterStatus.CURRENT
        and semester.reset_operation_id is None
        and backup.created_by_operation_id == operation.id
        and backup.source_semester_id == semester.id
        and backup.source_boundary_at == semester.started_at
        and backup.state is SemesterBackupState.CREATING
        and backup.verified_at is not None
        and backup.expires_at is None
        and backup.failure_code is None
        and backup.database_manifest_location is not None
        and backup.database_manifest_checksum is not None
        and backup.avatar_manifest_location is not None
        and backup.avatar_manifest_checksum is not None
    )


async def get_semester_reset_preflight(
    session: AsyncSession,
    actor: User,
) -> SemesterResetPreflight:
    """Return bounded counts and the currently eligible reset identity."""
    _require_admin(actor)
    semester = await session.scalar(
        select(Semester).where(Semester.status == SemesterStatus.CURRENT)
    )
    if semester is None:
        raise SemesterResetStateError("Current semester is unavailable.")
    operation = await session.scalar(
        select(SemesterOperation)
        .where(
            SemesterOperation.semester_id == semester.id,
            SemesterOperation.operation_type == SemesterOperationType.RESET,
            SemesterOperation.state == SemesterOperationState.RUNNING,
        )
        .order_by(SemesterOperation.requested_at.desc())
        .limit(1)
    )
    backup: SemesterBackup | None = None
    if operation is not None and operation.backup_id is not None:
        backup = await session.scalar(
            select(SemesterBackup).where(SemesterBackup.id == operation.backup_id)
        )
    verified = (
        operation is not None
        and backup is not None
        and _is_reset_execution_eligible(
            operation,
            backup,
            semester,
            admin_id=actor.id,
        )
    )
    return SemesterResetPreflight(
        semester_id=semester.id,
        operation_id=operation.id if operation is not None else None,
        backup_id=backup.id if backup is not None else None,
        backup_state=backup.state if backup is not None else None,
        backup_verified=verified,
        can_execute=verified,
        affected_counts=await _aggregate_counts(session, semester.id),
        preserved_counts=await _preserved_counts(session),
        confirmation_phrase=semester_reset_confirmation_phrase(semester.id),
    )


def _validate_current_snapshot(
    backed_up: DatabaseBackupManifest,
    current: DatabaseBackupManifest,
) -> None:
    backed_up_tables = tuple(
        (item.table_name, item.columns, item.row_count, item.sha256) for item in backed_up.tables
    )
    current_tables = tuple(
        (item.table_name, item.columns, item.row_count, item.sha256) for item in current.tables
    )
    if (
        backed_up.backup_id != current.backup_id
        or backed_up.source_semester_id != current.source_semester_id
        or backed_up.source_boundary_at != current.source_boundary_at
        or backed_up_tables != current_tables
        or backed_up.shared_references != current.shared_references
        or backed_up.avatar_references != current.avatar_references
        or backed_up.compatibility != current.compatibility
    ):
        raise SemesterResetSnapshotError("Semester data changed after backup verification.")


async def _load_verified_manifests(
    storage: DatabaseBackupArtifactStore,
    backup: SemesterBackup,
    root: Path,
) -> tuple[DatabaseBackupManifest, AvatarBackupManifest]:
    database_checksum = backup.database_manifest_checksum
    avatar_checksum = backup.avatar_manifest_checksum
    if database_checksum is None or avatar_checksum is None:
        raise SemesterResetStateError("Semester backup verification metadata is incomplete.")
    database_path = root / "database-manifest.json"
    avatar_path = root / "avatar-manifest.json"
    try:
        await storage.get_file(
            DatabaseBackupObjectRef(backup.id, DatabaseBackupObjectKind.MANIFEST),
            database_path,
        )
        await storage.get_file(AvatarBackupManifestRef(backup.id), avatar_path)
        database_manifest = validate_database_backup_manifest(
            database_path.read_bytes(),
            expected_backup_id=backup.id,
            expected_manifest_checksum=database_checksum,
        )
        avatar_manifest = validate_avatar_backup_manifest(
            avatar_path.read_bytes(),
            expected_backup_id=backup.id,
            expected_manifest_checksum=avatar_checksum,
        )
        validate_semester_backup_manifests(
            backup,
            database_manifest,
            avatar_manifest,
            storage=storage,
        )
    except SemesterResetError:
        raise
    except Exception:
        raise SemesterResetSnapshotError("Verified semester backup is unavailable.") from None
    return database_manifest, avatar_manifest


async def _delete_managed_avatars(
    storage: ImageStorageService,
    manifest: AvatarBackupManifest,
) -> int:
    for item in manifest.objects:
        try:
            await storage.delete_image(
                StorageObjectRef(
                    ImageBucket.PROFILE_IMAGES,
                    item.source_object_key,
                )
            )
        except StorageOperationError as error:
            if error.status_code != 404:
                raise SemesterResetStorageError("Semester avatar cleanup failed.") from None
    return len(manifest.objects)


def _parse_reset_summary(value: object) -> tuple[UUID, UUID, dict[str, int], int]:
    if not isinstance(value, dict):
        raise SemesterResetStateError("Semester reset result metadata is invalid.")
    try:
        closed_semester_id = UUID(str(value["closed_semester_id"]))
        new_semester_id = UUID(str(value["new_semester_id"]))
        deleted = _integer_counts(value["deleted"])
        avatars = value["avatar_objects_processed"]
    except (KeyError, TypeError, ValueError):
        raise SemesterResetStateError("Semester reset result metadata is invalid.") from None
    if type(avatars) is not int or avatars < 0:
        raise SemesterResetStateError("Semester reset result metadata is invalid.")
    return closed_semester_id, new_semester_id, deleted, avatars


async def _locked_reset_context(
    session: AsyncSession,
    *,
    operation_id: UUID,
    backup_id: UUID,
    admin_id: UUID,
    current_password: str,
    confirmation_phrase: str,
) -> tuple[User, SemesterOperation, SemesterBackup, Semester, bool]:
    locked = bool(await session.scalar(text(_WRITE_BARRIER_SQL)))
    if not locked:
        raise SemesterResetBusyError("Another semester operation owns the write barrier.")
    actor = await session.scalar(select(User).where(User.id == admin_id).with_for_update())
    if actor is None:
        raise SemesterResetAuthorizationError("Semester reset authorization failed.")
    _require_admin(actor)
    if not verify_password(current_password, actor.password_hash):
        raise SemesterResetAuthorizationError("Semester reset authorization failed.")

    operation = await session.scalar(
        select(SemesterOperation).where(SemesterOperation.id == operation_id).with_for_update()
    )
    backup = await session.scalar(
        select(SemesterBackup).where(SemesterBackup.id == backup_id).with_for_update()
    )
    if operation is None or backup is None:
        raise SemesterResetStateError("Semester reset is not eligible.")
    semester = await session.scalar(
        select(Semester).where(Semester.id == operation.semester_id).with_for_update()
    )
    if semester is None or confirmation_phrase != semester_reset_confirmation_phrase(semester.id):
        raise SemesterResetAuthorizationError("Semester reset authorization failed.")

    replay = operation.state is SemesterOperationState.SUCCEEDED
    if replay:
        if (
            operation.operation_type is not SemesterOperationType.RESET
            or operation.admin_actor_id != actor.id
            or operation.backup_id != backup.id
            or semester.status is not SemesterStatus.CLOSED
            or semester.reset_operation_id != operation.id
            or backup.state not in {SemesterBackupState.CREATING, SemesterBackupState.READY}
        ):
            raise SemesterResetStateError("Completed semester reset metadata is invalid.")
        return actor, operation, backup, semester, True

    if not _is_reset_execution_eligible(
        operation,
        backup,
        semester,
        admin_id=actor.id,
    ):
        raise SemesterResetStateError("Semester reset is not eligible.")
    return actor, operation, backup, semester, False


async def execute_semester_reset(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    operation_id: UUID,
    backup_id: UUID,
    admin_id: UUID,
    current_password: str,
    confirmation_phrase: str,
    snapshot_adapter: PostgresBinaryCopyBackupAdapter,
    backup_storage: DatabaseBackupArtifactStore,
    avatar_storage: ImageStorageService,
) -> SemesterResetReport:
    """Delete exactly one verified cohort and finalize its retained backup."""
    summary: object
    replay = False
    async with session_factory() as session, session.begin():
        actor, operation, backup, semester, replay = await _locked_reset_context(
            session,
            operation_id=operation_id,
            backup_id=backup_id,
            admin_id=admin_id,
            current_password=current_password,
            confirmation_phrase=confirmation_phrase,
        )
        if replay:
            summary = operation.result_summary
        else:
            with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem005-reset-") as temporary:
                root = Path(temporary)
                database_manifest, avatar_manifest = await _load_verified_manifests(
                    backup_storage,
                    backup,
                    root,
                )
                current_package = await snapshot_adapter.export(
                    backup_id=backup.id,
                    source_semester_id=semester.id,
                    source_boundary_at=semester.started_at,
                    artifact_location="private-verification://semester-reset",
                    workspace=root / "current-snapshot",
                )
                _validate_current_snapshot(database_manifest, current_package.manifest)
                avatars_processed = await _delete_managed_avatars(
                    avatar_storage,
                    avatar_manifest,
                )
                summary = await session.scalar(
                    text(
                        "SELECT app_private.execute_semester_reset("
                        ":operation_id, :backup_id, :admin_id, :avatar_count)"
                    ),
                    {
                        "operation_id": operation.id,
                        "backup_id": backup.id,
                        "admin_id": actor.id,
                        "avatar_count": avatars_processed,
                    },
                )
                closed_id, new_id, deleted, _ = _parse_reset_summary(summary)
                await record_audit_log(
                    session,
                    actor,
                    action=SEMESTER_RESET_AUDIT_ACTION,
                    resource_type="semester_operation",
                    resource_id=operation.id,
                    new_value={"state": SemesterOperationState.SUCCEEDED.value},
                    metadata={
                        "closed_semester_id": str(closed_id),
                        "new_semester_id": str(new_id),
                        "deleted": deleted,
                        "avatar_objects_processed": avatars_processed,
                    },
                )

    try:
        verification: SemesterBackupVerificationReport = await verify_semester_backup(
            session_factory,
            backup_id=backup_id,
            storage=backup_storage,
        )
    except SemesterBackupVerificationError:
        raise SemesterResetStateError("Semester backup finalization failed.") from None
    if (
        verification.persisted_state is not SemesterBackupState.READY
        or verification.effective_state is not SemesterBackupState.READY
    ):
        raise SemesterResetStateError("Semester backup finalization failed.")
    closed_id, new_id, deleted, avatars = _parse_reset_summary(summary)
    return SemesterResetReport(
        operation_id=operation_id,
        backup_id=backup_id,
        closed_semester_id=closed_id,
        new_semester_id=new_id,
        deleted_counts=deleted,
        avatar_objects_processed=avatars,
        operation_state=SemesterOperationState.SUCCEEDED,
        backup_state=verification.persisted_state,
        idempotent_replay=replay,
    )
