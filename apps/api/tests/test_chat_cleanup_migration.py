"""CHAT-005 least-privilege cleanup-function migration contract."""

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


def test_cleanup_upgrade_renders_bounded_atomic_least_privilege_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0015_chat_send_idempotency:0016_chat_message_cleanup",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "create function app_private.cleanup_expired_buddy_messages" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "p_batch_size integer default 20" in sql
    assert "p_batch_size not between 1 and 100" in sql
    assert "p_cleanup_now timestamp with time zone default statement_timestamp()" in sql
    assert "p_cleanup_now > statement_timestamp()" in sql
    assert "candidate.expires_at <= p_cleanup_now" in sql
    assert "order by candidate.expires_at, candidate.id" in sql
    assert "limit p_batch_size" in sql
    assert "for update of candidate skip locked" in sql
    assert "delete from app_private.buddy_messages" in sql
    assert "delete from app_private.buddy_conversations" not in sql
    assert "delete from app_private.matches" not in sql
    assert "revoke all on function" in sql
    assert "from public" in sql
    assert "'anon', 'authenticated', 'service_role'" in sql
    assert "grant execute on function" in sql
    assert "to vgu_buddy_runtime" in sql
    assert "grant delete" not in sql


def test_cleanup_downgrade_removes_only_the_cleanup_function(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0016_chat_message_cleanup:0015_chat_send_idempotency",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop function app_private.cleanup_expired_buddy_messages" in sql
    assert "drop table" not in sql
    assert "drop index" not in sql
