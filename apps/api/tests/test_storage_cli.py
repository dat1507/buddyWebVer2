"""Safety and output tests for the storage reconciliation command."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.cli as cli
from app.models import SemesterBackupState
from app.services.database_backup_storage import DatabaseBackupStorageError
from app.services.image_storage import (
    ImageBucket,
    ReconciliationReport,
    StorageOperationError,
    StorageReconciliationError,
)
from app.services.semester_avatar_backup import AvatarBackupError, AvatarBackupReport
from app.services.semester_backup_verification import (
    SemesterBackupExpiryError,
    SemesterBackupExpiryReport,
    SemesterBackupVerificationError,
    SemesterBackupVerificationReport,
)
from app.services.semester_database_backup import DatabaseBackupError, DatabaseBackupReport


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _report(*, failed: int = 0) -> ReconciliationReport:
    return ReconciliationReport(
        scanned=8,
        protected=3,
        too_new=2,
        unmanaged=1,
        candidates=2,
        deleted=2 - failed,
        failed=failed,
    )


def test_configure_storage_cli_converges_all_server_owned_buckets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transport = MagicMock()
    transport.configure_bucket = AsyncMock()
    transport_factory = MagicMock(return_value=transport)
    settings = MagicMock()
    monkeypatch.setattr(cli, "get_storage_settings", MagicMock(return_value=settings))
    monkeypatch.setattr(cli, "SupabaseStorageTransport", transport_factory)

    exit_code = cli.main(["configure-storage"])

    captured = capsys.readouterr()
    assert exit_code == 0
    transport_factory.assert_called_once_with(settings)
    assert [call.args[0] for call in transport.configure_bucket.await_args_list] == list(
        ImageBucket
    )
    assert captured.out == "Storage buckets configured: 3\n"
    assert captured.err == ""


def test_configure_storage_cli_sanitizes_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = StorageOperationError("provider returned a secret")
    monkeypatch.setattr(cli, "_configure_storage_command", AsyncMock(side_effect=error))

    exit_code = cli.main(["configure-storage"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: {cli.STORAGE_CONFIGURATION_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


def test_reconcile_cli_defaults_to_non_destructive_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(return_value=_report())
    monkeypatch.setattr(cli, "_reconcile_storage_command", command)

    exit_code = cli.main(["reconcile-storage"])

    captured = capsys.readouterr()
    assert exit_code == 0
    command.assert_awaited_once_with(apply=False, minimum_age_hours=24)
    assert "Storage reconciliation (dry-run)" in captured.out
    assert "candidates=2" in captured.out
    assert captured.err == ""


def test_reconcile_cli_requires_explicit_apply_and_accepts_age_guard(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(return_value=_report())
    monkeypatch.setattr(cli, "_reconcile_storage_command", command)

    exit_code = cli.main(["reconcile-storage", "--apply", "--minimum-age-hours", "72"])

    captured = capsys.readouterr()
    assert exit_code == 0
    command.assert_awaited_once_with(apply=True, minimum_age_hours=72)
    assert "Storage reconciliation (apply)" in captured.out


@pytest.mark.parametrize(
    "error",
    (
        StorageOperationError("secret storage response"),
        OSError("network details"),
    ),
)
def test_reconcile_cli_sanitizes_failures(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_reconcile_storage_command", AsyncMock(side_effect=error))

    exit_code = cli.main(["reconcile-storage"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: {cli.STORAGE_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


@pytest.mark.anyio
async def test_apply_refuses_cleanup_without_reference_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    context.__aexit__.return_value = False
    factory = MagicMock(return_value=context)
    monkeypatch.setattr(cli, "get_session_factory", lambda: factory)
    monkeypatch.setattr(cli, "get_storage_settings", MagicMock())
    monkeypatch.setattr(cli, "SupabaseStorageTransport", MagicMock())
    monkeypatch.setattr(
        cli, "discover_storage_references", AsyncMock(return_value=(frozenset(), 0))
    )
    dispose = AsyncMock()
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)

    with pytest.raises(StorageReconciliationError, match="refusing"):
        await cli._reconcile_storage_command(apply=True, minimum_age_hours=24)

    dispose.assert_awaited_once_with()


def test_configure_semester_backup_storage_is_separate_private_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock()
    monkeypatch.setattr(cli, "_configure_semester_backup_storage_command", command)

    assert cli.main(["configure-semester-backup-storage"]) == 0

    command.assert_awaited_once_with()
    assert capsys.readouterr().out == "Semester database backup storage configured.\n"


def test_database_backup_cli_uses_stable_id_and_only_reports_aggregates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backup_id = uuid4()
    command = AsyncMock(
        return_value=DatabaseBackupReport(
            backup_id=backup_id,
            table_count=15,
            row_count=42,
            artifact_size_bytes=1024,
            manifest_checksum="a" * 64,
            state=SemesterBackupState.CREATING,
        )
    )
    monkeypatch.setattr(cli, "_database_backup_command", command)

    assert cli.main(["backup-semester-database", "--backup-id", str(backup_id)]) == 0

    captured = capsys.readouterr()
    command.assert_awaited_once_with(backup_id=backup_id)
    assert "tables=15, rows=42, bytes=1024, state=CREATING" in captured.out
    assert "manifest_checksum" not in captured.out
    assert captured.err == ""


@pytest.mark.parametrize(
    "error",
    (
        DatabaseBackupError("secret database detail"),
        DatabaseBackupStorageError("secret storage detail"),
    ),
)
def test_database_backup_cli_sanitizes_failures(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_database_backup_command", AsyncMock(side_effect=error))

    assert cli.main(["backup-semester-database", "--backup-id", str(uuid4())]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.DATABASE_BACKUP_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


def test_avatar_backup_cli_uses_stable_id_and_only_reports_aggregates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backup_id = uuid4()
    command = AsyncMock(
        return_value=AvatarBackupReport(
            backup_id=backup_id,
            object_count=2,
            total_bytes=2048,
            manifest_checksum="b" * 64,
            state=SemesterBackupState.CREATING,
        )
    )
    monkeypatch.setattr(cli, "_avatar_backup_command", command)

    assert cli.main(["backup-semester-avatars", "--backup-id", str(backup_id)]) == 0

    captured = capsys.readouterr()
    command.assert_awaited_once_with(backup_id=backup_id)
    assert "objects=2, bytes=2048, state=CREATING" in captured.out
    assert "manifest_checksum" not in captured.out
    assert captured.err == ""


@pytest.mark.parametrize(
    "error",
    (
        AvatarBackupError("private object path"),
        StorageOperationError("secret storage detail"),
    ),
)
def test_avatar_backup_cli_sanitizes_failures(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_avatar_backup_command", AsyncMock(side_effect=error))

    assert cli.main(["backup-semester-avatars", "--backup-id", str(uuid4())]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.AVATAR_BACKUP_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


def test_combined_backup_verification_cli_reports_only_safe_aggregates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    backup_id = uuid4()
    now = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
    command = AsyncMock(
        return_value=SemesterBackupVerificationReport(
            backup_id=backup_id,
            persisted_state=SemesterBackupState.READY,
            effective_state=SemesterBackupState.READY,
            verified_at=now,
            expires_at=now,
            database_rows=42,
            avatar_objects=2,
            newly_verified=True,
            newly_ready=True,
        )
    )
    monkeypatch.setattr(cli, "_backup_verification_command", command)

    assert cli.main(["verify-semester-backup", "--backup-id", str(backup_id)]) == 0

    captured = capsys.readouterr()
    command.assert_awaited_once_with(backup_id=backup_id)
    assert "state=READY, effective_state=READY" in captured.out
    assert "database_rows=42, avatar_objects=2" in captured.out
    assert "newly_verified=true, newly_ready=true" in captured.out
    assert "manifest" not in captured.out
    assert "checksum" not in captured.out
    assert captured.err == ""


def test_combined_backup_verification_cli_sanitizes_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = SemesterBackupVerificationError("private path and checksum")
    monkeypatch.setattr(cli, "_backup_verification_command", AsyncMock(side_effect=error))

    assert cli.main(["verify-semester-backup", "--backup-id", str(uuid4())]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.BACKUP_VERIFICATION_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


@pytest.mark.parametrize("failed,expected_exit", ((0, 0), (1, 1)))
def test_backup_expiry_cli_is_bounded_and_observable(
    failed: int,
    expected_exit: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(
        return_value=SemesterBackupExpiryReport(
            selected=2,
            expired=2 - failed,
            cleaned=2 - failed,
            failed=failed,
        )
    )
    monkeypatch.setattr(cli, "_backup_expiry_command", command)

    assert cli.main(["expire-semester-backups", "--batch-size", "7"]) == expected_exit

    captured = capsys.readouterr()
    command.assert_awaited_once_with(batch_size=7)
    assert f"failed={failed}" in captured.out
    assert captured.err == ""


def test_backup_expiry_cli_sanitizes_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    error = SemesterBackupExpiryError("private object identity")
    monkeypatch.setattr(cli, "_backup_expiry_command", AsyncMock(side_effect=error))

    assert cli.main(["expire-semester-backups"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.BACKUP_EXPIRY_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err
