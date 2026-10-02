"""Focused SEM-002 manifest, integrity, scope, and restore-boundary tests."""

from __future__ import annotations

import hashlib
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from app.core.config import BackupDatabaseSettings
from app.services.semester_database_backup import (
    BACKUP_TABLES,
    DatabaseBackupError,
    DatabaseBackupValidationError,
    PostgresBinaryCopyBackupAdapter,
    validate_database_backup_package,
)

NOW = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)


class _Transaction(AbstractAsyncContextManager[None]):
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakePostgresConnection:
    def __init__(self, *, major: int = 17, target: bool = False) -> None:
        self.major = major
        self.target = target
        self.closed = False
        self.copied_to: list[str] = []
        self.restored_counts: dict[str, int] = {}

    def transaction(self, **_kwargs: object) -> _Transaction:
        return _Transaction()

    def get_server_version(self) -> SimpleNamespace:
        return SimpleNamespace(major=self.major)

    async def fetchval(self, query: str, *_arguments: object) -> object:
        if query == "SELECT version_num FROM alembic_version":
            return "0017_semester_boundary_metadata"
        if query == "SELECT statement_timestamp()":
            return NOW
        if query == "SELECT count(*) FROM app_private.users WHERE role = 'USER'":
            return 0
        for spec in BACKUP_TABLES:
            if f'"{spec.table_name}"' in query and query.startswith("SELECT count(*)"):
                if self.target:
                    return self.restored_counts.get(spec.table_name, 0)
                return 2 if spec.table_name == "users" else 0
        raise AssertionError(f"Unexpected scalar query: {query}")

    async def fetch(self, query: str, *arguments: object) -> list[tuple[object]]:
        if "FROM app_private.users WHERE role = 'ADMIN'" in query:
            return []
        if query.startswith("SELECT") and "ANY($1" in query:
            required = arguments[0] if arguments else []
            assert isinstance(required, list)
            return [(value,) for value in required]
        if query.startswith("SELECT DISTINCT"):
            return []
        raise AssertionError(f"Unexpected row query: {query}")

    async def copy_from_query(
        self,
        query: str,
        _semester_id: UUID,
        *,
        output: str,
        format: str,
    ) -> None:
        assert format == "binary"
        Path(output).write_bytes(b"PGCOPY\n\xff\r\n\x00" + query.encode())

    async def copy_to_table(
        self,
        table_name: str,
        *,
        schema_name: str,
        source: str,
        columns: list[str],
        format: str,
    ) -> None:
        assert schema_name == "app_private"
        assert Path(source).is_file()
        assert columns
        assert format == "binary"
        self.copied_to.append(table_name)
        self.restored_counts[table_name] = 2 if table_name == "users" else 0

    async def close(self) -> None:
        self.closed = True


def _settings() -> BackupDatabaseSettings:
    return BackupDatabaseSettings(url=SecretStr("postgresql://backup:secret@127.0.0.1:5432/sem002"))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_native_copy_export_has_exact_scope_manifest_and_deterministic_order(
    tmp_path: Path,
) -> None:
    connection = _FakePostgresConnection()

    async def connect(_settings: BackupDatabaseSettings) -> Any:
        return connection

    backup_id = uuid4()
    semester_id = uuid4()
    adapter = PostgresBinaryCopyBackupAdapter(_settings(), connection_factory=connect)

    package = await adapter.export(
        backup_id=backup_id,
        source_semester_id=semester_id,
        source_boundary_at=NOW,
        artifact_location=f"private://{backup_id}/artifact",
        workspace=tmp_path,
    )

    assert connection.closed is True
    assert package.manifest.backup_id == backup_id
    assert package.manifest.source_semester_id == semester_id
    assert package.manifest.expires_at is None
    assert package.manifest.retention_policy_days == 30
    assert package.manifest.compatibility.source_postgresql_major == 17
    assert package.manifest.compatibility.required_alembic_head == (
        "0017_semester_boundary_metadata"
    )
    assert tuple(table.table_name for table in package.manifest.tables) == tuple(
        spec.table_name for spec in BACKUP_TABLES
    )
    assert package.manifest.row_counts["users"] == 2
    assert package.manifest.row_counts["matching_invitations"] == 0
    assert "events" not in package.manifest.row_counts
    assert "interests" not in package.manifest.row_counts
    assert "semester_operations" not in package.manifest.row_counts
    assert package.manifest.shared_references.source_semester_ids == (semester_id,)
    assert (
        package.manifest_checksum == hashlib.sha256(package.manifest_path.read_bytes()).hexdigest()
    )
    assert (
        validate_database_backup_package(
            package.manifest_path.read_bytes(),
            package.artifact_path,
            expected_backup_id=backup_id,
            expected_manifest_checksum=package.manifest_checksum,
        )
        == package.manifest
    )


@pytest.mark.anyio
async def test_restore_replays_tables_in_dependency_order_after_full_validation(
    tmp_path: Path,
) -> None:
    source = _FakePostgresConnection()
    target = _FakePostgresConnection(target=True)
    connections = iter((source, target))

    async def connect(_settings: BackupDatabaseSettings) -> Any:
        return next(connections)

    adapter = PostgresBinaryCopyBackupAdapter(_settings(), connection_factory=connect)
    package = await adapter.export(
        backup_id=uuid4(),
        source_semester_id=uuid4(),
        source_boundary_at=NOW,
        artifact_location="private://artifact",
        workspace=tmp_path / "export",
    )

    restored = await adapter.restore_for_rehearsal(
        manifest_content=package.manifest_path.read_bytes(),
        artifact_path=package.artifact_path,
        expected_manifest_checksum=package.manifest_checksum,
    )

    assert restored == package.manifest
    assert target.copied_to == [spec.table_name for spec in BACKUP_TABLES]
    assert target.closed is True


@pytest.mark.anyio
async def test_tampered_or_truncated_artifact_fails_before_restore_connection(
    tmp_path: Path,
) -> None:
    source = _FakePostgresConnection()
    restore_connections = 0

    async def source_connect(_settings: BackupDatabaseSettings) -> Any:
        return source

    source_adapter = PostgresBinaryCopyBackupAdapter(_settings(), connection_factory=source_connect)
    package = await source_adapter.export(
        backup_id=uuid4(),
        source_semester_id=uuid4(),
        source_boundary_at=NOW,
        artifact_location="private://artifact",
        workspace=tmp_path / "export",
    )
    original = package.artifact_path.read_bytes()

    async def forbidden_connect(_settings: BackupDatabaseSettings) -> Any:
        nonlocal restore_connections
        restore_connections += 1
        raise AssertionError("restore connection must not open")

    restore_adapter = PostgresBinaryCopyBackupAdapter(
        _settings(), connection_factory=forbidden_connect
    )
    for index, content in enumerate((original[:-7], original[:-1] + b"X")):
        damaged = tmp_path / f"damaged-{index}.tar.gz"
        damaged.write_bytes(content)
        with pytest.raises(DatabaseBackupValidationError):
            await restore_adapter.restore_for_rehearsal(
                manifest_content=package.manifest_path.read_bytes(),
                artifact_path=damaged,
                expected_manifest_checksum=package.manifest_checksum,
            )
    assert restore_connections == 0


@pytest.mark.anyio
async def test_malformed_or_checksum_mismatched_manifest_fails_before_restore(
    tmp_path: Path,
) -> None:
    connection = _FakePostgresConnection()

    async def connect(_settings: BackupDatabaseSettings) -> Any:
        return connection

    adapter = PostgresBinaryCopyBackupAdapter(_settings(), connection_factory=connect)
    package = await adapter.export(
        backup_id=uuid4(),
        source_semester_id=uuid4(),
        source_boundary_at=NOW,
        artifact_location="private://artifact",
        workspace=tmp_path,
    )
    for manifest, checksum in (
        (b"not-json", hashlib.sha256(b"not-json").hexdigest()),
        (package.manifest_path.read_bytes(), "0" * 64),
    ):
        with pytest.raises(DatabaseBackupValidationError):
            validate_database_backup_package(
                manifest,
                package.artifact_path,
                expected_manifest_checksum=checksum,
            )


@pytest.mark.anyio
async def test_incompatible_target_fails_without_copying_any_table(tmp_path: Path) -> None:
    source = _FakePostgresConnection(major=17)
    target = _FakePostgresConnection(major=16, target=True)
    connections = iter((source, target))

    async def connect(_settings: BackupDatabaseSettings) -> Any:
        return next(connections)

    adapter = PostgresBinaryCopyBackupAdapter(_settings(), connection_factory=connect)
    package = await adapter.export(
        backup_id=uuid4(),
        source_semester_id=uuid4(),
        source_boundary_at=NOW,
        artifact_location="private://artifact",
        workspace=tmp_path,
    )

    with pytest.raises(DatabaseBackupValidationError, match="version is incompatible"):
        await adapter.restore_for_rehearsal(
            manifest_content=package.manifest_path.read_bytes(),
            artifact_path=package.artifact_path,
            expected_manifest_checksum=package.manifest_checksum,
        )
    assert target.copied_to == []


@pytest.mark.anyio
async def test_copy_adapter_sanitizes_connection_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "do-not-leak-this-password"

    async def fail(**_kwargs: object) -> Any:
        raise OSError(secret)

    monkeypatch.setattr("app.services.semester_database_backup.asyncpg.connect", fail)
    adapter = PostgresBinaryCopyBackupAdapter(_settings())
    with pytest.raises(DatabaseBackupError) as raised:
        await adapter.export(
            backup_id=uuid4(),
            source_semester_id=uuid4(),
            source_boundary_at=NOW,
            artifact_location="private://artifact",
            workspace=tmp_path,
        )
    assert str(raised.value) == "Database backup connection failed."
    assert secret not in str(raised.value)
