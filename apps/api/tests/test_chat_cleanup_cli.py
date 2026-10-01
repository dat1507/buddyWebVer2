"""CHAT-005 operational command and sanitized failure contract."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.cli as cli
from app.core.config import DatabaseConfigurationError
from app.services.chat_cleanup import ChatCleanupReport


def test_cleanup_cli_runs_one_batch_and_reports_aggregate_counts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock(return_value=ChatCleanupReport(selected=3, deleted=3))
    monkeypatch.setattr(cli, "_chat_cleanup_command", command)

    exit_code = cli.main(["cleanup-expired-chat-messages", "--batch-size", "7"])

    assert exit_code == 0
    command.assert_awaited_once_with(batch_size=7)
    captured = capsys.readouterr()
    assert captured.out == "Chat message cleanup: selected=3, deleted=3\n"
    assert captured.err == ""


def test_cleanup_cli_sanitizes_configuration_and_database_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_error = DatabaseConfigurationError("database URL with password")
    monkeypatch.setattr(cli, "_chat_cleanup_command", AsyncMock(side_effect=private_error))

    assert cli.main(["cleanup-expired-chat-messages"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Error: {cli.CHAT_CLEANUP_ERROR_MESSAGE}\n"
    assert str(private_error) not in captured.err


@pytest.mark.anyio
async def test_cleanup_command_logs_aggregates_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = ChatCleanupReport(selected=2, deleted=2)
    process = AsyncMock(return_value=report)
    factory = object()
    dispose = AsyncMock()
    emit = MagicMock()
    monkeypatch.setattr(cli, "get_session_factory", lambda: factory)
    monkeypatch.setattr(cli, "process_chat_cleanup_batch", process)
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "emit_chat_cleanup_event", emit)

    assert await cli._chat_cleanup_command(batch_size=5) == report

    process.assert_awaited_once_with(factory, batch_size=5)
    dispose.assert_awaited_once_with()
    assert emit.call_count == 1
    assert emit.call_args.kwargs["batch_size"] == 5
    assert emit.call_args.kwargs["selected"] == 2
    assert emit.call_args.kwargs["deleted"] == 2
    assert emit.call_args.kwargs["error_type"] is None
    assert emit.call_args.kwargs["duration_ms"] >= 0


@pytest.mark.anyio
async def test_cleanup_command_logs_only_failure_type_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_error = RuntimeError("private message content")
    process = AsyncMock(side_effect=private_error)
    dispose = AsyncMock()
    emit = MagicMock()
    monkeypatch.setattr(cli, "get_session_factory", lambda: object())
    monkeypatch.setattr(cli, "process_chat_cleanup_batch", process)
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "emit_chat_cleanup_event", emit)

    with pytest.raises(RuntimeError) as raised:
        await cli._chat_cleanup_command(batch_size=20)

    assert raised.value is private_error
    dispose.assert_awaited_once_with()
    assert emit.call_args.kwargs["selected"] == 0
    assert emit.call_args.kwargs["deleted"] == 0
    assert emit.call_args.kwargs["error_type"] == "RuntimeError"
    assert private_error.args[0] not in str(emit.call_args.kwargs)
