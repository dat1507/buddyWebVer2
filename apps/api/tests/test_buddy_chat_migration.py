"""Offline SQL contract checks for the CHAT-001 migration."""

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


def test_chat_upgrade_renders_private_integrity_and_retention_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0013_active_match_persistence:0014_buddy_chat_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "create table app_private.buddy_conversations" in sql
    assert "constraint uq_buddy_conversations_match_id unique (match_id)" in sql
    assert "references app_private.matches (id) on delete cascade" in sql
    assert "semester_id uuid" in sql
    assert "references app_private.semesters" not in sql
    assert "create table app_private.buddy_messages" in sql
    assert "constraint ck_buddy_messages_body_length" in sql
    assert "body ~ '[^[:space:]]'" in sql
    assert "char_length(body) <= 10000" in sql
    assert "constraint ck_buddy_messages_retention_timestamps" in sql
    assert "interval '90 days'" in sql
    assert "interval '30 days'" in sql
    assert "references app_private.buddy_conversations (id) on delete cascade" in sql
    assert "references app_private.users (id) on delete cascade" in sql
    assert "create index ix_buddy_messages_conversation_created_at_id" in sql
    assert "create index ix_buddy_messages_expires_at" in sql
    assert "create index ix_buddy_messages_sender_id" in sql
    assert "create function app_private.enforce_buddy_message_sender()" in sql
    assert "security invoker" in sql
    assert "set search_path = ''" in sql
    assert "buddy_match.status = 'active'" in sql
    assert "buddy_match.deleted_at is null" in sql
    assert "trg_buddy_messages_sender_active_participant" in sql
    assert "revoke all on table app_private.buddy_conversations from public" in sql
    assert "revoke all on table app_private.buddy_messages from public" in sql
    assert "'anon', 'authenticated', 'service_role'" in sql
    assert "grant select on table app_private.buddy_conversations" in sql
    assert "grant insert (id, match_id, semester_id, created_at)" in sql
    assert "grant select on table app_private.buddy_messages" in sql
    assert "grant update (read_at, expires_at)" in sql
    assert "grant delete" not in sql
    assert "alter table app_private.buddy_conversations enable row level security" in sql
    assert "alter table app_private.buddy_messages enable row level security" in sql


def test_chat_downgrade_removes_only_chat001_objects(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0014_buddy_chat_persistence:0013_active_match_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop trigger trg_buddy_messages_sender_active_participant" in sql
    assert "drop function app_private.enforce_buddy_message_sender()" in sql
    assert "drop table app_private.buddy_messages" in sql
    assert "drop table app_private.buddy_conversations" in sql
    assert "drop table app_private.matches" not in sql
