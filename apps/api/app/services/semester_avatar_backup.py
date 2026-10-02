"""SEM-003 private avatar-object backup, manifest, validation, and restore rehearsal."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import SemesterBackup, SemesterBackupState
from app.services.database_backup_storage import (
    BackupStorageObjectRef,
    DatabaseBackupArtifactStore,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ImageValidationError,
    StorageObjectRef,
    StorageOperationError,
    validate_stored_image_content,
)
from app.services.semester_database_backup import (
    DatabaseBackupAvatarReference,
    DatabaseBackupValidationError,
    assert_pre_delete_backup_eligibility,
    load_semester_backup_metadata,
    mark_semester_backup_failed,
    validate_database_backup_manifest,
)

AVATAR_BACKUP_MANIFEST_VERSION = 1
AVATAR_BACKUP_MANIFEST_NAME = "avatar-manifest-v1.json"
AVATAR_BACKUP_FAILURE_CODE = "AVATAR_BACKUP_FAILED"
MAX_AVATAR_MANIFEST_BYTES = 1024 * 1024
_SHA256_LENGTH = 64
_MIME_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class AvatarBackupError(RuntimeError):
    """Sanitized failure from the avatar-backup boundary."""


class AvatarBackupValidationError(AvatarBackupError):
    """Avatar objects or their manifest failed closed validation."""


class AvatarBackupBusyError(AvatarBackupError):
    """Another process owns the stable semester backup operation."""


class AvatarBackupAlreadyAttachedError(AvatarBackupError):
    """The stable backup operation already has a complete avatar manifest."""


@dataclass(frozen=True, slots=True)
class AvatarBackupManifestRef:
    backup_id: UUID

    @property
    def object_key(self) -> str:
        return f"{self.backup_id}/avatars/{AVATAR_BACKUP_MANIFEST_NAME}"

    @property
    def content_type(self) -> str:
        return "application/json"


@dataclass(frozen=True, slots=True)
class AvatarBackupBinaryRef:
    backup_id: UUID
    photo_id: UUID
    mime_type: str

    def __post_init__(self) -> None:
        if self.mime_type not in _MIME_EXTENSION:
            raise AvatarBackupValidationError("Avatar backup MIME type is invalid.")

    @property
    def object_key(self) -> str:
        extension = _MIME_EXTENSION[self.mime_type]
        return f"{self.backup_id}/avatars/objects/{self.photo_id}.{extension}"

    @property
    def content_type(self) -> str:
        return self.mime_type


class _StrictManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AvatarBackupObjectManifest(_StrictManifestModel):
    photo_id: UUID
    profile_id: UUID
    owner_user_id: UUID
    source_bucket: Literal["profile-images"]
    source_object_key: str = Field(min_length=40, max_length=41)
    backup_object_key: str = Field(min_length=1, max_length=255)
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
    byte_size: int = Field(gt=0, le=5 * 1024 * 1024)
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    sha256: str = Field(min_length=_SHA256_LENGTH, max_length=_SHA256_LENGTH)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("Avatar object checksum is invalid.")
        return value


class AvatarBackupManifest(_StrictManifestModel):
    manifest_version: Literal[1] = 1
    backup_id: UUID
    source_semester_id: UUID
    source_boundary_at: datetime
    created_at: datetime
    database_manifest_checksum: str = Field(min_length=_SHA256_LENGTH, max_length=_SHA256_LENGTH)
    object_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    objects: tuple[AvatarBackupObjectManifest, ...]

    @field_validator("source_boundary_at", "created_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Avatar manifest timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("database_manifest_checksum")
    @classmethod
    def validate_database_checksum(cls, value: str) -> str:
        if any(character not in "0123456789abcdef" for character in value):
            raise ValueError("Database manifest checksum is invalid.")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.object_count != len(self.objects):
            raise ValueError("Avatar object count is inconsistent.")
        if self.total_bytes != sum(item.byte_size for item in self.objects):
            raise ValueError("Avatar byte count is inconsistent.")
        if tuple(sorted(self.objects, key=lambda item: item.photo_id.int)) != self.objects:
            raise ValueError("Avatar objects are not deterministic.")
        unique_fields = (
            {item.photo_id for item in self.objects},
            {item.source_object_key for item in self.objects},
            {item.backup_object_key for item in self.objects},
        )
        if any(len(values) != len(self.objects) for values in unique_fields):
            raise ValueError("Avatar manifest contains duplicate objects.")
        for item in self.objects:
            expected = AvatarBackupBinaryRef(
                self.backup_id,
                item.photo_id,
                item.mime_type,
            ).object_key
            if item.backup_object_key != expected:
                raise ValueError("Avatar backup object identity is invalid.")
            try:
                source = StorageObjectRef(
                    ImageBucket(item.source_bucket),
                    item.source_object_key,
                )
            except (ValueError, ImageValidationError) as error:
                raise ValueError("Avatar source object identity is invalid.") from error
            extension = source.object_key.rsplit(".", maxsplit=1)[1]
            if _MIME_EXTENSION[item.mime_type] != extension:
                raise ValueError("Avatar source metadata is incompatible.")
        return self


@dataclass(frozen=True, slots=True)
class AvatarBackupPackage:
    manifest: AvatarBackupManifest
    manifest_path: Path
    object_files: tuple[tuple[AvatarBackupBinaryRef, Path], ...]
    manifest_checksum: str


@dataclass(frozen=True, slots=True)
class AvatarBackupReport:
    backup_id: UUID
    object_count: int
    total_bytes: int
    manifest_checksum: str
    state: SemesterBackupState


def _manifest_bytes(manifest: AvatarBackupManifest) -> bytes:
    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_private_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        with path.open("xb") as writer:
            writer.write(content)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except FileExistsError as error:
        raise AvatarBackupError("Avatar backup workspace is not empty.") from error
    except OSError as error:
        path.unlink(missing_ok=True)
        raise AvatarBackupError("Avatar backup file could not be created.") from error


def _sha256(path: Path, *, maximum: int = 5 * 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as reader:
            while chunk := reader.read(1024 * 1024):
                total += len(chunk)
                if total > maximum:
                    raise AvatarBackupValidationError("Avatar backup object is oversized.")
                digest.update(chunk)
    except AvatarBackupValidationError:
        raise
    except OSError as error:
        raise AvatarBackupValidationError("Avatar backup object is unavailable.") from error
    if total == 0:
        raise AvatarBackupValidationError("Avatar backup object is empty.")
    return digest.hexdigest(), total


def validate_avatar_backup_manifest(
    content: bytes,
    *,
    expected_backup_id: UUID | None = None,
    expected_manifest_checksum: str | None = None,
) -> AvatarBackupManifest:
    if not 1 <= len(content) <= MAX_AVATAR_MANIFEST_BYTES:
        raise AvatarBackupValidationError("Avatar backup manifest size is invalid.")
    if expected_manifest_checksum is not None and (
        hashlib.sha256(content).hexdigest() != expected_manifest_checksum
    ):
        raise AvatarBackupValidationError("Avatar backup manifest checksum mismatched.")
    try:
        manifest = AvatarBackupManifest.model_validate_json(content)
    except Exception:
        raise AvatarBackupValidationError("Avatar backup manifest is invalid.") from None
    if expected_backup_id is not None and manifest.backup_id != expected_backup_id:
        raise AvatarBackupValidationError("Avatar backup identity mismatched.")
    return manifest


def validate_avatar_backup_package(
    manifest_content: bytes,
    object_paths: Mapping[str, Path],
    *,
    expected_backup_id: UUID | None = None,
    expected_manifest_checksum: str | None = None,
) -> AvatarBackupManifest:
    """Validate exact membership, identity, metadata, size and checksum for every avatar."""
    manifest = validate_avatar_backup_manifest(
        manifest_content,
        expected_backup_id=expected_backup_id,
        expected_manifest_checksum=expected_manifest_checksum,
    )
    expected_keys = {item.backup_object_key for item in manifest.objects}
    if set(object_paths) != expected_keys:
        raise AvatarBackupValidationError("Avatar backup object membership mismatched.")
    for item in manifest.objects:
        path = object_paths[item.backup_object_key]
        checksum, byte_size = _sha256(path)
        if checksum != item.sha256 or byte_size != item.byte_size:
            raise AvatarBackupValidationError("Avatar backup object integrity mismatched.")
        try:
            content = path.read_bytes()
            validate_stored_image_content(
                StorageObjectRef(ImageBucket.PROFILE_IMAGES, item.source_object_key),
                content=content,
                mime_type=item.mime_type,
                byte_size=item.byte_size,
                width=item.width,
                height=item.height,
            )
        except (OSError, ImageValidationError, StorageOperationError):
            raise AvatarBackupValidationError("Avatar backup object is invalid.") from None
    return manifest


class AvatarBackupAdapter:
    """Copy only database-manifest-referenced avatars into a deterministic local package."""

    def __init__(self, source_storage: ImageStorageService) -> None:
        self._source_storage = source_storage

    async def export(
        self,
        *,
        backup_id: UUID,
        source_semester_id: UUID,
        source_boundary_at: datetime,
        created_at: datetime,
        database_manifest_checksum: str,
        references: tuple[DatabaseBackupAvatarReference, ...],
        workspace: Path,
    ) -> AvatarBackupPackage:
        workspace.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(workspace, 0o700)
        except OSError:
            pass
        objects: list[AvatarBackupObjectManifest] = []
        files: list[tuple[AvatarBackupBinaryRef, Path]] = []
        for reference in references:
            source_ref = StorageObjectRef(
                ImageBucket(reference.bucket),
                reference.object_key,
            )
            try:
                content = await self._source_storage.download_image(source_ref)
                validate_stored_image_content(
                    source_ref,
                    content=content,
                    mime_type=reference.mime_type,
                    byte_size=reference.byte_size,
                    width=reference.width,
                    height=reference.height,
                )
            except (ImageValidationError, StorageOperationError):
                raise AvatarBackupError(
                    "A referenced avatar object is unavailable or invalid."
                ) from None
            backup_ref = AvatarBackupBinaryRef(
                backup_id,
                reference.photo_id,
                reference.mime_type,
            )
            local_path = workspace / "objects" / Path(backup_ref.object_key).name
            _write_private_file(local_path, content)
            checksum, byte_size = _sha256(local_path)
            objects.append(
                AvatarBackupObjectManifest(
                    photo_id=reference.photo_id,
                    profile_id=reference.profile_id,
                    owner_user_id=reference.owner_user_id,
                    source_bucket=reference.bucket,
                    source_object_key=reference.object_key,
                    backup_object_key=backup_ref.object_key,
                    mime_type=reference.mime_type,
                    byte_size=byte_size,
                    width=reference.width,
                    height=reference.height,
                    sha256=checksum,
                )
            )
            files.append((backup_ref, local_path))

        manifest = AvatarBackupManifest(
            backup_id=backup_id,
            source_semester_id=source_semester_id,
            source_boundary_at=source_boundary_at,
            created_at=created_at,
            database_manifest_checksum=database_manifest_checksum,
            object_count=len(objects),
            total_bytes=sum(item.byte_size for item in objects),
            objects=tuple(objects),
        )
        content = _manifest_bytes(manifest)
        manifest_path = workspace / AVATAR_BACKUP_MANIFEST_NAME
        _write_private_file(manifest_path, content)
        checksum = hashlib.sha256(content).hexdigest()
        validate_avatar_backup_package(
            content,
            {reference.object_key: path for reference, path in files},
            expected_backup_id=backup_id,
            expected_manifest_checksum=checksum,
        )
        return AvatarBackupPackage(manifest, manifest_path, tuple(files), checksum)


async def store_avatar_backup_package(
    storage: DatabaseBackupArtifactStore,
    package: AvatarBackupPackage,
) -> tuple[BackupStorageObjectRef, ...]:
    """Upload non-upsert objects and remove the exact partial set on failure."""
    uploaded: list[BackupStorageObjectRef] = []
    try:
        for reference, path in package.object_files:
            await storage.put_file(reference, path)
            uploaded.append(reference)
        manifest_ref = AvatarBackupManifestRef(package.manifest.backup_id)
        await storage.put_file(manifest_ref, package.manifest_path)
        uploaded.append(manifest_ref)
    except Exception:
        for uploaded_reference in reversed(uploaded):
            try:
                await storage.delete(uploaded_reference)
            except Exception:
                pass
        raise
    return tuple(uploaded)


async def load_avatar_backup_from_storage(
    storage: DatabaseBackupArtifactStore,
    *,
    backup_id: UUID,
    manifest_checksum: str,
    workspace: Path,
) -> tuple[AvatarBackupManifest, dict[str, Path], bytes]:
    manifest_path = workspace / AVATAR_BACKUP_MANIFEST_NAME
    await storage.get_file(AvatarBackupManifestRef(backup_id), manifest_path)
    try:
        content = manifest_path.read_bytes()
    except OSError as error:
        raise AvatarBackupValidationError("Avatar backup manifest is unavailable.") from error
    manifest = validate_avatar_backup_manifest(
        content,
        expected_backup_id=backup_id,
        expected_manifest_checksum=manifest_checksum,
    )
    paths: dict[str, Path] = {}
    for item in manifest.objects:
        reference = AvatarBackupBinaryRef(backup_id, item.photo_id, item.mime_type)
        target = workspace / "objects" / Path(reference.object_key).name
        await storage.get_file(reference, target)
        paths[reference.object_key] = target
    validate_avatar_backup_package(
        content,
        paths,
        expected_backup_id=backup_id,
        expected_manifest_checksum=manifest_checksum,
    )
    return manifest, paths, content


async def restore_avatar_backup_for_rehearsal(
    target_storage: ImageStorageService,
    *,
    manifest_content: bytes,
    object_paths: Mapping[str, Path],
    expected_manifest_checksum: str,
) -> AvatarBackupManifest:
    """Restore exact source keys into a clean target; SEM-006 owns production orchestration."""
    manifest = validate_avatar_backup_package(
        manifest_content,
        object_paths,
        expected_manifest_checksum=expected_manifest_checksum,
    )
    restored: list[StorageObjectRef] = []
    try:
        for item in manifest.objects:
            reference = StorageObjectRef(ImageBucket.PROFILE_IMAGES, item.source_object_key)
            content = object_paths[item.backup_object_key].read_bytes()
            await target_storage.restore_image(
                reference,
                content=content,
                mime_type=item.mime_type,
                byte_size=item.byte_size,
                width=item.width,
                height=item.height,
            )
            restored.append(reference)
    except Exception as error:
        for reference in reversed(restored):
            try:
                await target_storage.delete_image(reference)
            except Exception:
                pass
        if isinstance(error, AvatarBackupError):
            raise
        raise AvatarBackupError("Avatar backup rehearsal restore failed.") from None
    return manifest


async def create_semester_avatar_backup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    backup_id: UUID,
    adapter: AvatarBackupAdapter,
    storage: DatabaseBackupArtifactStore,
) -> AvatarBackupReport:
    """Create, remotely verify, and atomically attach avatar metadata to SEM-001."""
    manifest_ref = AvatarBackupManifestRef(backup_id)
    uploaded: list[BackupStorageObjectRef] = []
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
                raise AvatarBackupBusyError("Semester avatar backup is already running.")
            backup = await load_semester_backup_metadata(session, backup_id)
            if backup.state is not SemesterBackupState.CREATING:
                raise AvatarBackupError("Semester backup is not in the creating state.")
            if backup.avatar_manifest_location is not None and (
                backup.avatar_manifest_checksum is not None
            ):
                raise AvatarBackupAlreadyAttachedError(
                    "Semester avatar backup is already attached."
                )
            if (
                backup.avatar_manifest_location is not None
                or backup.avatar_manifest_checksum is not None
                or backup.avatar_object_count != 0
            ):
                raise AvatarBackupError("Semester avatar backup metadata is incomplete.")
            if (
                backup.database_manifest_location is None
                or backup.database_manifest_checksum is None
                or not backup.database_row_counts
            ):
                raise AvatarBackupError("Database backup must be attached before avatar backup.")
            await assert_pre_delete_backup_eligibility(session, backup)
            created_at = await session.scalar(text("SELECT statement_timestamp()"))
            if not isinstance(created_at, datetime):
                raise AvatarBackupError("Database clock is unavailable.")

            with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem003-avatar-") as temporary:
                workspace = Path(temporary)
                database_manifest_path = workspace / "database-manifest.json"
                await storage.get_file(
                    DatabaseBackupObjectRef(backup_id, DatabaseBackupObjectKind.MANIFEST),
                    database_manifest_path,
                )
                try:
                    database_content = database_manifest_path.read_bytes()
                except OSError as error:
                    raise AvatarBackupError("Database backup manifest is unavailable.") from error
                try:
                    database_manifest = validate_database_backup_manifest(
                        database_content,
                        expected_backup_id=backup_id,
                        expected_manifest_checksum=backup.database_manifest_checksum,
                    )
                except DatabaseBackupValidationError:
                    raise AvatarBackupError("Database backup manifest is invalid.") from None
                if (
                    database_manifest.source_semester_id != backup.source_semester_id
                    or database_manifest.source_boundary_at != backup.source_boundary_at
                    or database_manifest.row_counts.get("profile_photos")
                    != len(database_manifest.avatar_references)
                ):
                    raise AvatarBackupError("Database and avatar backup scopes are inconsistent.")

                package = await adapter.export(
                    backup_id=backup_id,
                    source_semester_id=backup.source_semester_id,
                    source_boundary_at=backup.source_boundary_at,
                    created_at=created_at,
                    database_manifest_checksum=backup.database_manifest_checksum,
                    references=database_manifest.avatar_references,
                    workspace=workspace / "package",
                )
                uploaded.extend(await store_avatar_backup_package(storage, package))

                remote_root = workspace / "remote"
                remote_root.mkdir(mode=0o700)
                remote_manifest, _, _ = await load_avatar_backup_from_storage(
                    storage,
                    backup_id=backup_id,
                    manifest_checksum=package.manifest_checksum,
                    workspace=remote_root,
                )
                locked_backup = await session.scalar(
                    select(SemesterBackup)
                    .where(SemesterBackup.id == backup_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if (
                    locked_backup is None
                    or locked_backup.state is not SemesterBackupState.CREATING
                    or locked_backup.avatar_manifest_location is not None
                    or locked_backup.avatar_manifest_checksum is not None
                    or locked_backup.avatar_object_count != 0
                ):
                    raise AvatarBackupError("Semester backup metadata changed concurrently.")
                locked_backup.avatar_manifest_location = storage.location(manifest_ref)
                locked_backup.avatar_manifest_checksum = package.manifest_checksum
                locked_backup.avatar_object_count = remote_manifest.object_count

                report = AvatarBackupReport(
                    backup_id=backup_id,
                    object_count=remote_manifest.object_count,
                    total_bytes=remote_manifest.total_bytes,
                    manifest_checksum=package.manifest_checksum,
                    state=SemesterBackupState.CREATING,
                )
        return report
    except Exception as error:
        for uploaded_reference in reversed(uploaded):
            try:
                await storage.delete(uploaded_reference)
            except Exception:
                pass
        if not isinstance(error, (AvatarBackupBusyError, AvatarBackupAlreadyAttachedError)):
            try:
                async with session_factory() as failure_session:
                    await mark_semester_backup_failed(
                        failure_session,
                        backup_id,
                        failure_code=AVATAR_BACKUP_FAILURE_CODE,
                    )
            except Exception:
                pass
        if isinstance(error, AvatarBackupError):
            raise
        raise AvatarBackupError("Semester avatar backup failed.") from None
