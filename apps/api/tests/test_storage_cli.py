"""Safety and output tests for the storage reconciliation command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.cli as cli
from app.services.image_storage import (
    ImageBucket,
    ReconciliationReport,
    StorageOperationError,
    StorageReconciliationError,
)


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
