"""Offline migration contract checks for EMAIL-001."""

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


def test_email_verification_upgrade_renders_evidence_only_private_schema(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0007_event_tables:0008_email_verification",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "alter table app_private.users add column email_verified_at "
        "timestamp with time zone" in rendered_sql
    )
    assert (
        "update app_private.users set email_verified_at = null where role = 'user'"
        in " ".join(rendered_sql.split())
    )
    assert "create table app_private.email_verification_tokens" in rendered_sql
    assert "token_digest bytea not null" in rendered_sql
    assert "constraint uq_email_verification_tokens_token_digest" in rendered_sql
    assert "constraint ck_email_verification_tokens_expiry_after_creation" in rendered_sql
    assert (
        "create unique index uq_email_verification_tokens_active_user_id "
        "on app_private.email_verification_tokens (user_id) "
        "where consumed_at is null and superseded_at is null and deleted_at is null"
        in " ".join(rendered_sql.split())
    )
    assert "revoke all on table app_private.email_verification_tokens from public" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql
    assert (
        "grant select, insert, update, delete "
        "on table app_private.email_verification_tokens to vgu_buddy_runtime"
        in " ".join(rendered_sql.split())
    )
    assert (
        "alter table app_private.email_verification_tokens enable row level security"
        in rendered_sql
    )
    assert "create policy email_verification_tokens_backend_access" in rendered_sql


def test_email_verification_downgrade_removes_only_new_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0008_email_verification:0007_event_tables",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "drop policy email_verification_tokens_backend_access "
        "on app_private.email_verification_tokens" in rendered_sql
    )
    assert "drop index app_private.uq_email_verification_tokens_active_user_id" in rendered_sql
    assert "drop index app_private.ix_email_verification_tokens_expires_at" in rendered_sql
    assert "drop index app_private.ix_email_verification_tokens_user_id" in rendered_sql
    assert "drop table app_private.email_verification_tokens" in rendered_sql
    assert "alter table app_private.users drop column email_verified_at" in rendered_sql
    assert "drop column email_verified;" not in rendered_sql
