"""Offline SQL contract checks for the CHAT-002 idempotency migration."""

from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _migration_test_url() -> str:
    return "postgresql://migration-user:test-only@localhost/postgres?sslmode=disable"


def test_chat002_upgrade_adds_minimal_sender_scoped_idempotency(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0014_buddy_chat_persistence:0015_chat_send_idempotency",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "add column client_message_id uuid" in sql
    assert "set client_message_id = id where client_message_id is null" in sql
    assert "alter column client_message_id set not null" in sql
    assert "constraint uq_buddy_messages_sender_id_client_message_id" in sql
    assert "unique (sender_id, client_message_id)" in sql
    assert "grant insert (client_message_id)" in sql
    assert "drop table" not in sql


def test_chat002_downgrade_removes_only_idempotency_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0015_chat_send_idempotency:0014_buddy_chat_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop constraint uq_buddy_messages_sender_id_client_message_id" in sql
    assert "drop column client_message_id" in sql
    assert "drop table" not in sql
