"""Bounded worker command and sanitized output tests for MAIL-001."""

from unittest.mock import AsyncMock, Mock

import pytest

import app.cli as cli
from app.core.config import DatabaseConfigurationError, EmailConfigurationError
from app.services.email_outbox import OutboxWorkerReport


def _report(*, failed: int = 0) -> OutboxWorkerReport:
    return OutboxWorkerReport(
        claimed=2,
        sent=1,
        retry_scheduled=1 - failed,
        terminal_failed=failed,
        skipped=0,
    )


def test_email_worker_once_uses_bounded_arguments_and_reports_counts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(return_value=_report())
    monkeypatch.setattr(cli, "_email_worker_command", command)

    exit_code = cli.main(["email-worker", "--once", "--batch-size", "7", "--poll-seconds", "1.5"])

    assert exit_code == 0
    command.assert_awaited_once_with(once=True, batch_size=7, poll_seconds=1.5)
    captured = capsys.readouterr()
    assert "claimed=2, sent=1, retry_scheduled=1" in captured.out
    assert captured.err == ""


def test_email_worker_returns_nonzero_for_terminal_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_email_worker_command", AsyncMock(return_value=_report(failed=1)))

    exit_code = cli.main(["email-worker", "--once"])

    assert exit_code == 1
    assert "terminal_failed=1" in capsys.readouterr().out


def test_email_worker_sanitizes_configuration_and_database_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_error = EmailConfigurationError("provider key leaked")
    monkeypatch.setattr(cli, "_email_worker_command", AsyncMock(side_effect=private_error))

    exit_code = cli.main(["email-worker", "--once"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: {cli.EMAIL_WORKER_ERROR_MESSAGE}\n"
    assert str(private_error) not in captured.err


@pytest.mark.anyio
async def test_worker_smoke_processes_one_leased_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _report()
    process = AsyncMock(return_value=report)
    dispose = AsyncMock()
    monkeypatch.setattr(cli, "process_transactional_outbox_batch", process)
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "get_email_provider_settings", Mock(return_value=object()))
    monkeypatch.setattr(
        cli, "get_email_verification_delivery_settings", Mock(return_value=object())
    )
    monkeypatch.setattr(cli, "ResendEmailProvider", Mock(return_value=object()))
    monkeypatch.setattr(cli, "default_email_template_registry", Mock(return_value={}))
    monkeypatch.setattr(cli, "get_session_factory", Mock(return_value=object()))

    assert await cli._email_worker_command(once=True, batch_size=7, poll_seconds=1.5) == report
    process.assert_awaited_once()
    dispose.assert_awaited_once()


def test_local_runtime_role_command_has_sanitized_cli_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_error = DatabaseConfigurationError("private role password")
    monkeypatch.setattr(
        cli, "_configure_local_runtime_role_command", AsyncMock(side_effect=private_error)
    )

    assert cli.main(["configure-local-runtime-role"]) == 1
    captured = capsys.readouterr()
    assert captured.err == f"Error: {cli.LOCAL_RUNTIME_ROLE_ERROR_MESSAGE}\n"
    assert "password" not in captured.err
