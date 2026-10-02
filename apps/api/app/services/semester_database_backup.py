"""SEM-002 PostgreSQL-native scoped backup, manifest, verification, and rehearsal restore."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
import os
import re
import tarfile
import tempfile
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Self, cast
from uuid import UUID

import asyncpg  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import BackupDatabaseSettings
from app.core.database import APPLICATION_SCHEMA, backup_database_url
from app.models import (
    SEMESTER_BACKUP_RETENTION_DAYS,
    Base,
    SemesterBackup,
    SemesterBackupState,
)
from app.services.database_backup_storage import (
    MAX_DATABASE_BACKUP_BYTES,
    DatabaseBackupArtifactStore,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
)

DATABASE_BACKUP_FORMAT: Final = "postgresql-binary-copy-tar-gzip"
DATABASE_BACKUP_FORMAT_VERSION: Final = 1
DATABASE_BACKUP_MANIFEST_VERSION: Final = 1
DATABASE_BACKUP_FAILURE_CODE: Final = "DATABASE_BACKUP_FAILED"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SNAPSHOT_TABLES = """SELECT id FROM app_private.users
WHERE role = 'USER' AND semester_id = $1"""
_SNAPSHOT_PROFILES = f"""SELECT id FROM app_private.student_profiles
WHERE user_id IN ({_SNAPSHOT_TABLES})"""
_SNAPSHOT_INVITATIONS = f"""SELECT id FROM app_private.matching_invitations
WHERE sender_id IN ({_SNAPSHOT_TABLES}) AND recipient_id IN ({_SNAPSHOT_TABLES})"""
_SNAPSHOT_MATCHES = f"""SELECT id FROM app_private.matches
WHERE semester_id = $1
  AND participant_one_user_id IN ({_SNAPSHOT_TABLES})
  AND participant_two_user_id IN ({_SNAPSHOT_TABLES})"""
_SNAPSHOT_CONVERSATIONS = f"""SELECT id FROM app_private.buddy_conversations
WHERE semester_id = $1 AND match_id IN ({_SNAPSHOT_MATCHES})"""


class DatabaseBackupError(RuntimeError):
    """Sanitized failure from the database-backup boundary."""


class DatabaseBackupValidationError(DatabaseBackupError):
    """An artifact, manifest, or compatibility check failed closed."""


class DatabaseBackupBusyError(DatabaseBackupError):
    """Another process already owns the stable backup operation."""


class DatabaseBackupAlreadyAttachedError(DatabaseBackupError):
    """The stable backup operation already has a complete database artifact."""


@dataclass(frozen=True, slots=True)
class BackupTableSpec:
    table_name: str
    predicate: str

    @property
    def archive_name(self) -> str:
        return f"tables/{self.table_name}.copy"


BACKUP_TABLES: Final[tuple[BackupTableSpec, ...]] = (
    BackupTableSpec("users", "role = 'USER' AND semester_id = $1"),
    BackupTableSpec("email_verification_tokens", f"user_id IN ({_SNAPSHOT_TABLES})"),
    BackupTableSpec("refresh_sessions", f"user_id IN ({_SNAPSHOT_TABLES})"),
    BackupTableSpec("student_profiles", f"user_id IN ({_SNAPSHOT_TABLES})"),
    BackupTableSpec("profile_photos", f"profile_id IN ({_SNAPSHOT_PROFILES})"),
    BackupTableSpec("profile_interests", f"profile_id IN ({_SNAPSHOT_PROFILES})"),
    BackupTableSpec("profile_languages", f"profile_id IN ({_SNAPSHOT_PROFILES})"),
    BackupTableSpec("profile_activities", f"profile_id IN ({_SNAPSHOT_PROFILES})"),
    BackupTableSpec("profile_custom_preferences", f"profile_id IN ({_SNAPSHOT_PROFILES})"),
    BackupTableSpec("event_registrations", f"user_id IN ({_SNAPSHOT_TABLES})"),
    BackupTableSpec(
        "matching_invitations",
        f"sender_id IN ({_SNAPSHOT_TABLES}) AND recipient_id IN ({_SNAPSHOT_TABLES})",
    ),
    BackupTableSpec(
        "matches",
        f"semester_id = $1 "
        f"AND participant_one_user_id IN ({_SNAPSHOT_TABLES}) "
        f"AND participant_two_user_id IN ({_SNAPSHOT_TABLES})",
    ),
    BackupTableSpec(
        "buddy_conversations",
        f"semester_id = $1 AND match_id IN ({_SNAPSHOT_MATCHES})",
    ),
    BackupTableSpec(
        "buddy_messages",
        f"conversation_id IN ({_SNAPSHOT_CONVERSATIONS}) AND sender_id IN ({_SNAPSHOT_TABLES})",
    ),
    BackupTableSpec(
        "transactional_outbox",
        f"recipient_user_id IN ({_SNAPSHOT_TABLES})",
    ),
)


class _StrictManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatabaseBackupTableManifest(_StrictManifestModel):
    table_name: str = Field(min_length=1, max_length=63)
    archive_name: str = Field(min_length=1, max_length=128)
    columns: tuple[str, ...] = Field(min_length=1)
    row_count: int = Field(ge=0)
    byte_size: int = Field(gt=0, le=MAX_DATABASE_BACKUP_BYTES)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("Table checksum is invalid.")
        return value


class DatabaseBackupSharedReferences(_StrictManifestModel):
    source_semester_ids: tuple[UUID, ...]
    admin_user_ids: tuple[UUID, ...]
    interest_ids: tuple[UUID, ...]
    language_codes: tuple[str, ...]
    activity_ids: tuple[UUID, ...]
    event_ids: tuple[UUID, ...]


class DatabaseBackupCompatibility(_StrictManifestModel):
    source_postgresql_major: int = Field(ge=15, le=99)
    required_target_postgresql_major: int = Field(ge=15, le=99)
    required_alembic_head: str = Field(min_length=1, max_length=255)
    producer: Literal["asyncpg-postgresql-copy"] = "asyncpg-postgresql-copy"
    producer_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def require_same_postgresql_major(self) -> Self:
        if self.required_target_postgresql_major != self.source_postgresql_major:
            raise ValueError("PostgreSQL backup compatibility is invalid.")
        return self


class DatabaseBackupManifest(_StrictManifestModel):
    manifest_version: Literal[1] = DATABASE_BACKUP_MANIFEST_VERSION
    backup_id: UUID
    source_semester_id: UUID
    source_boundary_at: datetime
    created_at: datetime
    expires_at: None = None
    retention_policy_days: Literal[30] = SEMESTER_BACKUP_RETENTION_DAYS
    artifact_format: Literal["postgresql-binary-copy-tar-gzip"] = DATABASE_BACKUP_FORMAT
    artifact_format_version: Literal[1] = DATABASE_BACKUP_FORMAT_VERSION
    artifact_location: str = Field(min_length=1, max_length=1024)
    artifact_size_bytes: int = Field(gt=0, le=MAX_DATABASE_BACKUP_BYTES)
    artifact_sha256: str
    tables: tuple[DatabaseBackupTableManifest, ...] = Field(min_length=1)
    shared_references: DatabaseBackupSharedReferences
    compatibility: DatabaseBackupCompatibility

    @field_validator("source_boundary_at", "created_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Manifest timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("artifact_sha256")
    @classmethod
    def validate_artifact_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("Artifact checksum is invalid.")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        expected_names = tuple(spec.table_name for spec in BACKUP_TABLES)
        actual_names = tuple(item.table_name for item in self.tables)
        if actual_names != expected_names:
            raise ValueError("Backup table order is incompatible.")
        if self.shared_references.source_semester_ids != (self.source_semester_id,):
            raise ValueError("Source semester reference is incompatible.")
        return self

    @property
    def row_counts(self) -> dict[str, int]:
        return {table.table_name: table.row_count for table in self.tables}


@dataclass(frozen=True, slots=True)
class DatabaseBackupPackage:
    manifest: DatabaseBackupManifest
    manifest_path: Path
    artifact_path: Path
    manifest_checksum: str


@dataclass(frozen=True, slots=True)
class DatabaseBackupReport:
    backup_id: UUID
    table_count: int
    row_count: int
    artifact_size_bytes: int
    manifest_checksum: str
    state: SemesterBackupState


ConnectionFactory = Callable[[BackupDatabaseSettings], Awaitable[Any]]


def _database_dsn(settings: BackupDatabaseSettings) -> str:
    url = backup_database_url(settings)
    query = dict(url.query)
    ssl_mode = query.pop("ssl", None)
    if ssl_mode is not None:
        query["sslmode"] = ssl_mode
    return url.set(drivername="postgresql", query=query).render_as_string(hide_password=False)


async def _connect(settings: BackupDatabaseSettings) -> Any:
    try:
        return await asyncpg.connect(dsn=_database_dsn(settings))
    except Exception:
        raise DatabaseBackupError("Database backup connection failed.") from None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as reader:
            while chunk := reader.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_DATABASE_BACKUP_BYTES:
                    raise DatabaseBackupValidationError("Database backup artifact is oversized.")
                digest.update(chunk)
    except DatabaseBackupValidationError:
        raise
    except OSError as error:
        raise DatabaseBackupValidationError("Database backup artifact is unavailable.") from error
    if total == 0:
        raise DatabaseBackupValidationError("Database backup artifact is empty.")
    return digest.hexdigest()


def _manifest_bytes(manifest: DatabaseBackupManifest) -> bytes:
    payload = manifest.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _parse_manifest(content: bytes) -> DatabaseBackupManifest:
    try:
        return DatabaseBackupManifest.model_validate_json(content)
    except Exception:
        raise DatabaseBackupValidationError("Database backup manifest is invalid.") from None


def _table_columns(table_name: str) -> tuple[str, ...]:
    table = Base.metadata.tables[f"{APPLICATION_SCHEMA}.{table_name}"]
    return tuple(column.name for column in table.columns if column.computed is None)


def _quoted_columns(columns: Sequence[str]) -> str:
    if any(re.fullmatch(r"[a-z][a-z0-9_]*", column) is None for column in columns):
        raise DatabaseBackupValidationError("Database backup column identity is invalid.")
    return ", ".join(f'"{column}"' for column in columns)


def _order_columns(table_name: str) -> tuple[str, ...]:
    table = Base.metadata.tables[f"{APPLICATION_SCHEMA}.{table_name}"]
    primary_keys = tuple(column.name for column in table.primary_key.columns)
    return primary_keys or _table_columns(table_name)


def _table_query(spec: BackupTableSpec) -> str:
    columns = _table_columns(spec.table_name)
    order = _quoted_columns(_order_columns(spec.table_name))
    return (
        f'SELECT {_quoted_columns(columns)} FROM "{APPLICATION_SCHEMA}".'
        f'"{spec.table_name}" WHERE {spec.predicate} ORDER BY {order}'
    )


def _table_count_query(spec: BackupTableSpec) -> str:
    return f'SELECT count(*) FROM "{APPLICATION_SCHEMA}"."{spec.table_name}" WHERE {spec.predicate}'


async def _fetch_uuid_tuple(
    connection: Any, query: str, semester_id: UUID | None = None
) -> tuple[UUID, ...]:
    rows = await connection.fetch(query, *(()) if semester_id is None else (semester_id,))
    return tuple(UUID(str(row[0])) for row in rows)


async def _shared_references(connection: Any, semester_id: UUID) -> DatabaseBackupSharedReferences:
    admins = await _fetch_uuid_tuple(
        connection,
        "SELECT id FROM app_private.users WHERE role = 'ADMIN' ORDER BY id",
    )
    interests = await _fetch_uuid_tuple(
        connection,
        f"SELECT DISTINCT interest_id FROM app_private.profile_interests "
        f"WHERE profile_id IN ({_SNAPSHOT_PROFILES}) ORDER BY interest_id",
        semester_id,
    )
    language_rows = await connection.fetch(
        f"SELECT DISTINCT language_code FROM app_private.profile_languages "
        f"WHERE profile_id IN ({_SNAPSHOT_PROFILES}) ORDER BY language_code",
        semester_id,
    )
    activities = await _fetch_uuid_tuple(
        connection,
        f"SELECT DISTINCT activity_id FROM app_private.profile_activities "
        f"WHERE profile_id IN ({_SNAPSHOT_PROFILES}) ORDER BY activity_id",
        semester_id,
    )
    events = await _fetch_uuid_tuple(
        connection,
        f"SELECT DISTINCT event_id FROM app_private.event_registrations "
        f"WHERE user_id IN ({_SNAPSHOT_TABLES}) ORDER BY event_id",
        semester_id,
    )
    return DatabaseBackupSharedReferences(
        source_semester_ids=(semester_id,),
        admin_user_ids=admins,
        interest_ids=interests,
        language_codes=tuple(str(row[0]) for row in language_rows),
        activity_ids=activities,
        event_ids=events,
    )


def _build_archive(table_files: Sequence[tuple[str, Path]], target: Path) -> None:
    try:
        with target.open("xb") as raw:
            import gzip

            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    for archive_name, path in table_files:
                        info = tarfile.TarInfo(archive_name)
                        info.size = path.stat().st_size
                        info.mode = 0o600
                        info.mtime = 0
                        with path.open("rb") as reader:
                            archive.addfile(info, reader)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except FileExistsError as error:
        raise DatabaseBackupError("Database backup workspace is not empty.") from error
    except OSError as error:
        target.unlink(missing_ok=True)
        raise DatabaseBackupError("Database backup archive could not be created.") from error


def validate_database_backup_package(
    manifest_content: bytes,
    artifact_path: Path,
    *,
    expected_backup_id: UUID | None = None,
    expected_manifest_checksum: str | None = None,
) -> DatabaseBackupManifest:
    """Validate manifest, outer checksum, members, sizes, and per-table checksums."""
    if expected_manifest_checksum is not None:
        actual_manifest_checksum = hashlib.sha256(manifest_content).hexdigest()
        if actual_manifest_checksum != expected_manifest_checksum:
            raise DatabaseBackupValidationError("Database backup manifest checksum mismatched.")
    manifest = _parse_manifest(manifest_content)
    if expected_backup_id is not None and manifest.backup_id != expected_backup_id:
        raise DatabaseBackupValidationError("Database backup identity mismatched.")
    try:
        artifact_size = artifact_path.stat().st_size
    except OSError as error:
        raise DatabaseBackupValidationError("Database backup artifact is unavailable.") from error
    if artifact_size != manifest.artifact_size_bytes:
        raise DatabaseBackupValidationError("Database backup artifact size mismatched.")
    if _sha256_file(artifact_path) != manifest.artifact_sha256:
        raise DatabaseBackupValidationError("Database backup artifact checksum mismatched.")

    expected = {table.archive_name: table for table in manifest.tables}
    try:
        with tarfile.open(artifact_path, mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len(expected) or {member.name for member in members} != set(
                expected
            ):
                raise DatabaseBackupValidationError("Database backup archive members mismatched.")
            for member in members:
                table = expected[member.name]
                if not member.isfile() or member.size != table.byte_size:
                    raise DatabaseBackupValidationError(
                        "Database backup archive member is invalid."
                    )
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise DatabaseBackupValidationError(
                        "Database backup archive member is unavailable."
                    )
                digest = hashlib.sha256()
                size = 0
                while chunk := extracted.read(1024 * 1024):
                    size += len(chunk)
                    if size > table.byte_size:
                        raise DatabaseBackupValidationError(
                            "Database backup archive member is oversized."
                        )
                    digest.update(chunk)
                if size != table.byte_size or digest.hexdigest() != table.sha256:
                    raise DatabaseBackupValidationError(
                        "Database backup archive member checksum mismatched."
                    )
    except DatabaseBackupValidationError:
        raise
    except (OSError, tarfile.TarError, EOFError):
        raise DatabaseBackupValidationError("Database backup archive is invalid.") from None
    return manifest


def _extract_validated_tables(
    manifest: DatabaseBackupManifest, artifact_path: Path, target: Path
) -> dict[str, Path]:
    extracted: dict[str, Path] = {}
    try:
        with tarfile.open(artifact_path, mode="r:gz") as archive:
            for table in manifest.tables:
                member = archive.getmember(table.archive_name)
                reader = archive.extractfile(member)
                if reader is None:
                    raise DatabaseBackupValidationError(
                        "Database backup archive member is unavailable."
                    )
                output = target / f"{table.table_name}.copy"
                with output.open("xb") as writer:
                    remaining = table.byte_size
                    while remaining:
                        chunk = reader.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise DatabaseBackupValidationError(
                                "Database backup archive member is truncated."
                            )
                        writer.write(chunk)
                        remaining -= len(chunk)
                try:
                    os.chmod(output, 0o600)
                except OSError:
                    pass
                extracted[table.table_name] = output
    except DatabaseBackupValidationError:
        raise
    except (KeyError, OSError, tarfile.TarError):
        raise DatabaseBackupValidationError("Database backup archive is invalid.") from None
    return extracted


class PostgresBinaryCopyBackupAdapter:
    """PostgreSQL protocol adapter using native binary COPY, without shell commands."""

    def __init__(
        self,
        settings: BackupDatabaseSettings,
        *,
        connection_factory: ConnectionFactory = _connect,
    ) -> None:
        self._settings = settings
        self._connection_factory = connection_factory

    async def export(
        self,
        *,
        backup_id: UUID,
        source_semester_id: UUID,
        source_boundary_at: datetime,
        artifact_location: str,
        workspace: Path,
    ) -> DatabaseBackupPackage:
        if source_boundary_at.tzinfo is None or source_boundary_at.utcoffset() is None:
            raise DatabaseBackupError("Source semester boundary must be timezone-aware.")
        workspace.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(workspace, 0o700)
        except OSError:
            pass
        connection = await self._connection_factory(self._settings)
        table_manifests: list[DatabaseBackupTableManifest] = []
        table_files: list[tuple[str, Path]] = []
        try:
            async with connection.transaction(isolation="repeatable_read", readonly=True):
                server_major = connection.get_server_version().major
                alembic_head = await connection.fetchval("SELECT version_num FROM alembic_version")
                if not isinstance(alembic_head, str) or not alembic_head:
                    raise DatabaseBackupValidationError(
                        "Source database migration head is unavailable."
                    )
                created_at = await connection.fetchval("SELECT statement_timestamp()")
                if not isinstance(created_at, datetime):
                    raise DatabaseBackupValidationError("Source database clock is unavailable.")
                references = await _shared_references(connection, source_semester_id)
                for spec in BACKUP_TABLES:
                    path = workspace / f"{spec.table_name}.copy"
                    await connection.copy_from_query(
                        _table_query(spec),
                        source_semester_id,
                        output=str(path),
                        format="binary",
                    )
                    try:
                        os.chmod(path, 0o600)
                    except OSError:
                        pass
                    row_count = await connection.fetchval(
                        _table_count_query(spec), source_semester_id
                    )
                    if type(row_count) is not int or row_count < 0:
                        raise DatabaseBackupValidationError("Database backup row count is invalid.")
                    byte_size = path.stat().st_size
                    table_manifest = DatabaseBackupTableManifest(
                        table_name=spec.table_name,
                        archive_name=spec.archive_name,
                        columns=_table_columns(spec.table_name),
                        row_count=row_count,
                        byte_size=byte_size,
                        sha256=_sha256_file(path),
                    )
                    table_manifests.append(table_manifest)
                    table_files.append((spec.archive_name, path))
        except DatabaseBackupError:
            raise
        except Exception:
            raise DatabaseBackupError("Database backup export failed.") from None
        finally:
            await connection.close()

        artifact_path = workspace / DatabaseBackupObjectKind.ARTIFACT.value
        _build_archive(table_files, artifact_path)
        artifact_size = artifact_path.stat().st_size
        if artifact_size > MAX_DATABASE_BACKUP_BYTES:
            raise DatabaseBackupError("Database backup artifact is oversized.")
        manifest = DatabaseBackupManifest(
            backup_id=backup_id,
            source_semester_id=source_semester_id,
            source_boundary_at=source_boundary_at,
            created_at=created_at,
            artifact_location=artifact_location,
            artifact_size_bytes=artifact_size,
            artifact_sha256=_sha256_file(artifact_path),
            tables=tuple(table_manifests),
            shared_references=references,
            compatibility=DatabaseBackupCompatibility(
                source_postgresql_major=server_major,
                required_target_postgresql_major=server_major,
                required_alembic_head=alembic_head,
                producer_version=importlib.metadata.version("asyncpg"),
            ),
        )
        content = _manifest_bytes(manifest)
        manifest_path = workspace / DatabaseBackupObjectKind.MANIFEST.value
        try:
            manifest_path.write_bytes(content)
            os.chmod(manifest_path, 0o600)
        except OSError as error:
            raise DatabaseBackupError("Database backup manifest could not be created.") from error
        manifest_checksum = hashlib.sha256(content).hexdigest()
        validate_database_backup_package(
            content,
            artifact_path,
            expected_backup_id=backup_id,
            expected_manifest_checksum=manifest_checksum,
        )
        return DatabaseBackupPackage(
            manifest=manifest,
            manifest_path=manifest_path,
            artifact_path=artifact_path,
            manifest_checksum=manifest_checksum,
        )

    async def restore_for_rehearsal(
        self,
        *,
        manifest_content: bytes,
        artifact_path: Path,
        expected_manifest_checksum: str,
    ) -> DatabaseBackupManifest:
        """Restore into an empty compatible DB; SEM-006 still owns production orchestration."""
        manifest = validate_database_backup_package(
            manifest_content,
            artifact_path,
            expected_manifest_checksum=expected_manifest_checksum,
        )
        with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem002-restore-") as temporary:
            workspace = Path(temporary)
            try:
                os.chmod(workspace, 0o700)
            except OSError:
                pass
            extracted = _extract_validated_tables(manifest, artifact_path, workspace)
            connection = await self._connection_factory(self._settings)
            try:
                async with connection.transaction(isolation="serializable"):
                    await self._validate_restore_target(connection, manifest)
                    for table_manifest in manifest.tables:
                        await connection.copy_to_table(
                            table_manifest.table_name,
                            schema_name=APPLICATION_SCHEMA,
                            source=str(extracted[table_manifest.table_name]),
                            columns=list(table_manifest.columns),
                            format="binary",
                        )
                    for spec, table_manifest in zip(BACKUP_TABLES, manifest.tables, strict=True):
                        restored = await connection.fetchval(
                            _table_count_query(spec), manifest.source_semester_id
                        )
                        if restored != table_manifest.row_count:
                            raise DatabaseBackupValidationError(
                                "Restored database row count mismatched."
                            )
            except DatabaseBackupError:
                raise
            except Exception:
                raise DatabaseBackupError("Database backup rehearsal restore failed.") from None
            finally:
                await connection.close()
        return manifest

    async def _validate_restore_target(
        self,
        connection: Any,
        manifest: DatabaseBackupManifest,
    ) -> None:
        if connection.get_server_version().major != (
            manifest.compatibility.required_target_postgresql_major
        ):
            raise DatabaseBackupValidationError("Target PostgreSQL version is incompatible.")
        target_head = await connection.fetchval("SELECT version_num FROM alembic_version")
        if target_head != manifest.compatibility.required_alembic_head:
            raise DatabaseBackupValidationError("Target migration head is incompatible.")
        existing_students = await connection.fetchval(
            "SELECT count(*) FROM app_private.users WHERE role = 'USER'"
        )
        if existing_students != 0:
            raise DatabaseBackupValidationError("Restore target contains student data.")

        refs = manifest.shared_references
        checks: tuple[tuple[str, Sequence[object]], ...] = (
            (
                "SELECT id FROM app_private.semesters WHERE id = ANY($1::uuid[])",
                refs.source_semester_ids,
            ),
            (
                "SELECT id FROM app_private.users WHERE role = 'ADMIN' AND id = ANY($1::uuid[])",
                refs.admin_user_ids,
            ),
            ("SELECT id FROM app_private.interests WHERE id = ANY($1::uuid[])", refs.interest_ids),
            (
                "SELECT code FROM app_private.languages WHERE code = ANY($1::text[])",
                refs.language_codes,
            ),
            ("SELECT id FROM app_private.activities WHERE id = ANY($1::uuid[])", refs.activity_ids),
            ("SELECT id FROM app_private.events WHERE id = ANY($1::uuid[])", refs.event_ids),
        )
        for query, required in checks:
            if not required:
                continue
            rows = await connection.fetch(query, list(required))
            actual = {str(row[0]) for row in rows}
            if actual != {str(value) for value in required}:
                raise DatabaseBackupValidationError(
                    "Restore target is missing a required shared reference."
                )


async def _load_backup(session: AsyncSession, backup_id: UUID) -> SemesterBackup:
    backup = await session.scalar(select(SemesterBackup).where(SemesterBackup.id == backup_id))
    if backup is None:
        raise DatabaseBackupError("Semester backup does not exist.")
    return backup


async def _assert_pre_delete_backup_eligibility(
    session: AsyncSession, backup: SemesterBackup
) -> None:
    eligible = await session.scalar(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM app_private.semester_operations AS operation "
            "JOIN app_private.semesters AS semester "
            "ON semester.id = operation.semester_id "
            "WHERE operation.id = :operation_id "
            "AND operation.operation_type = 'RESET' "
            "AND operation.state = 'RUNNING' "
            "AND operation.semester_id = :semester_id "
            "AND semester.status = 'CURRENT' "
            "AND semester.started_at = :source_boundary_at)"
        ),
        {
            "operation_id": backup.created_by_operation_id,
            "semester_id": backup.source_semester_id,
            "source_boundary_at": backup.source_boundary_at,
        },
    )
    if eligible is not True:
        raise DatabaseBackupError("Semester backup is not eligible before reset.")


async def _mark_backup_failed(session: AsyncSession, backup_id: UUID, *, failure_code: str) -> None:
    async with session.begin():
        backup = await _load_backup(session, backup_id)
        if backup.state is SemesterBackupState.CREATING:
            backup.failure_code = failure_code
            backup.transition_to(SemesterBackupState.FAILED)


async def create_semester_database_backup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    backup_id: UUID,
    adapter: PostgresBinaryCopyBackupAdapter,
    storage: DatabaseBackupArtifactStore,
) -> DatabaseBackupReport:
    """Create, remotely re-verify, and atomically attach one DB artifact to SEM-001 metadata."""
    artifact_ref = DatabaseBackupObjectRef(backup_id, DatabaseBackupObjectKind.ARTIFACT)
    manifest_ref = DatabaseBackupObjectRef(backup_id, DatabaseBackupObjectKind.MANIFEST)
    uploaded: list[DatabaseBackupObjectRef] = []
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
                raise DatabaseBackupBusyError("Semester database backup is already running.")
            backup = await _load_backup(session, backup_id)
            if backup.state is not SemesterBackupState.CREATING:
                raise DatabaseBackupError("Semester backup is not in the creating state.")
            attachment_fields = (
                backup.database_manifest_location,
                backup.database_manifest_checksum,
                backup.database_row_counts,
            )
            if all(attachment_fields):
                raise DatabaseBackupAlreadyAttachedError(
                    "Semester database backup is already attached."
                )
            if any(attachment_fields):
                raise DatabaseBackupError("Semester database backup metadata is incomplete.")
            await _assert_pre_delete_backup_eligibility(session, backup)
            with tempfile.TemporaryDirectory(prefix="vgu-buddy-sem002-backup-") as temporary:
                workspace = Path(temporary)
                package = await adapter.export(
                    backup_id=backup.id,
                    source_semester_id=backup.source_semester_id,
                    source_boundary_at=backup.source_boundary_at,
                    artifact_location=storage.location(artifact_ref),
                    workspace=workspace,
                )
                await storage.put_file(artifact_ref, package.artifact_path)
                uploaded.append(artifact_ref)
                await storage.put_file(manifest_ref, package.manifest_path)
                uploaded.append(manifest_ref)

                downloaded_artifact = workspace / "remote-artifact.tar.gz"
                downloaded_manifest = workspace / "remote-manifest.json"
                await storage.get_file(artifact_ref, downloaded_artifact)
                await storage.get_file(manifest_ref, downloaded_manifest)
                remote_content = downloaded_manifest.read_bytes()
                remote_manifest = validate_database_backup_package(
                    remote_content,
                    downloaded_artifact,
                    expected_backup_id=backup_id,
                    expected_manifest_checksum=package.manifest_checksum,
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
                    or locked_backup.database_manifest_location is not None
                ):
                    raise DatabaseBackupError("Semester backup metadata changed concurrently.")
                locked_backup.database_manifest_location = storage.location(manifest_ref)
                locked_backup.database_manifest_checksum = package.manifest_checksum
                persisted_row_counts = cast(dict[str, object], remote_manifest.row_counts)
                locked_backup.database_row_counts = persisted_row_counts

                report = DatabaseBackupReport(
                    backup_id=backup_id,
                    table_count=len(remote_manifest.tables),
                    row_count=sum(remote_manifest.row_counts.values()),
                    artifact_size_bytes=remote_manifest.artifact_size_bytes,
                    manifest_checksum=package.manifest_checksum,
                    state=SemesterBackupState.CREATING,
                )
        return report
    except Exception as error:
        for reference in reversed(uploaded):
            try:
                await storage.delete(reference)
            except Exception:
                pass
        if not isinstance(error, (DatabaseBackupBusyError, DatabaseBackupAlreadyAttachedError)):
            try:
                async with session_factory() as failure_session:
                    await _mark_backup_failed(
                        failure_session,
                        backup_id,
                        failure_code=DATABASE_BACKUP_FAILURE_CODE,
                    )
            except Exception:
                pass
        if isinstance(error, DatabaseBackupError):
            raise
        raise DatabaseBackupError("Semester database backup failed.") from None


async def load_database_backup_from_storage(
    storage: DatabaseBackupArtifactStore,
    *,
    backup_id: UUID,
    manifest_checksum: str,
    workspace: Path,
) -> tuple[DatabaseBackupManifest, Path, bytes]:
    """Fetch and fail-closed validate stored objects before any restore connection is opened."""
    artifact_ref = DatabaseBackupObjectRef(backup_id, DatabaseBackupObjectKind.ARTIFACT)
    manifest_ref = DatabaseBackupObjectRef(backup_id, DatabaseBackupObjectKind.MANIFEST)
    artifact_path = workspace / DatabaseBackupObjectKind.ARTIFACT.value
    manifest_path = workspace / DatabaseBackupObjectKind.MANIFEST.value
    await asyncio.gather(
        storage.get_file(artifact_ref, artifact_path),
        storage.get_file(manifest_ref, manifest_path),
    )
    try:
        content = manifest_path.read_bytes()
    except OSError as error:
        raise DatabaseBackupValidationError("Database backup manifest is unavailable.") from error
    manifest = validate_database_backup_package(
        content,
        artifact_path,
        expected_backup_id=backup_id,
        expected_manifest_checksum=manifest_checksum,
    )
    return manifest, artifact_path, content
