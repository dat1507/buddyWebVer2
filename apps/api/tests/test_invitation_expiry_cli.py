"""INV-002 bounded CLI entry point and sanitized operational output tests."""

from unittest.mock import AsyncMock, Mock

import pytest

import app.cli as cli
from app.core.config import DatabaseConfigurationError
from app.services.invitation_expiry import InvitationExpiryReport


def test_expiry_cli_runs_one_bounded_batch_and_reports_only_counts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(return_value=InvitationExpiryReport(selected=3, expired=3))
    monkeypatch.setattr(cli, "_invitation_expiry_command", command)

    exit_code = cli.main(["expire-invitations", "--batch-size", "7"])

    assert exit_code == 0
    command.assert_awaited_once_with(batch_size=7)
    captured = capsys.readouterr()
    assert captured.out == "Invitation expiry: selected=3, expired=3\n"
    assert captured.err == ""


def test_expiry_cli_sanitizes_configuration_and_database_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_error = DatabaseConfigurationError("database URL with password")
    monkeypatch.setattr(cli, "_invitation_expiry_command", AsyncMock(side_effect=private_error))

    assert cli.main(["expire-invitations"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.INVITATION_EXPIRY_ERROR_MESSAGE}\n"
    assert str(private_error) not in captured.err


@pytest.mark.anyio
async def test_expiry_command_processes_once_logs_aggregates_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = InvitationExpiryReport(selected=2, expired=2)
    process = AsyncMock(return_value=report)
    dispose = AsyncMock()
    emit = Mock()
    monkeypatch.setattr(cli, "process_invitation_expiry_batch", process)
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "emit_invitation_expiry_event", emit)
    monkeypatch.setattr(cli, "get_session_factory", Mock(return_value=object()))

    assert await cli._invitation_expiry_command(batch_size=7) == report

    process.assert_awaited_once()
    dispose.assert_awaited_once_with()
    emitted = emit.call_args.kwargs
    assert emitted["batch_size"] == 7
    assert emitted["selected"] == emitted["expired"] == 2
    assert emitted["duration_ms"] >= 0
    assert emitted["error_type"] is None


@pytest.mark.anyio
async def test_expiry_command_logs_only_failure_type_and_still_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = AsyncMock(side_effect=RuntimeError("recipient email and private SQL"))
    dispose = AsyncMock()
    emit = Mock()
    monkeypatch.setattr(cli, "process_invitation_expiry_batch", process)
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "emit_invitation_expiry_event", emit)
    monkeypatch.setattr(cli, "get_session_factory", Mock(return_value=object()))

    with pytest.raises(RuntimeError):
        await cli._invitation_expiry_command(batch_size=7)

    emitted = emit.call_args.kwargs
    assert emitted["selected"] == emitted["expired"] == 0
    assert emitted["error_type"] == "RuntimeError"
    assert "recipient" not in repr(emitted)
    dispose.assert_awaited_once_with()
