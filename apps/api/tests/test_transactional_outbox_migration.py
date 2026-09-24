"""Offline migration contract checks for MAIL-001."""

from pathlib import Path
from secrets import token_urlsafe

import pytest
from alembic.config import Config
from sqlalchemy import URL

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _migration_test_url() -> str:
    return URL.create(
        "postgresql",
        username="migration-user",
        password=token_urlsafe(24),
        host="localhost",
        database="postgres",
        query={"sslmode": "disable"},
    ).render_as_string(hide_password=False)


def test_outbox_upgrade_renders_private_runtime_only_schema(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0008_email_verification:0009_transactional_outbox",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = " ".join(capsys.readouterr().out.lower().split())
    assert "create table app_private.transactional_outbox" in sql
    assert "payload jsonb not null" in sql
    assert "constraint uq_transactional_outbox_idempotency_key unique" in sql
    assert "constraint ck_transactional_outbox_lease_pair check" in sql
    assert "for update" not in sql
    assert "revoke all on table app_private.transactional_outbox from public" in sql
    assert "'anon', 'authenticated', 'service_role'" in sql
    assert (
        "grant select, insert, update, delete on table app_private.transactional_outbox "
        "to vgu_buddy_runtime" in sql
    )
    assert "alter table app_private.transactional_outbox enable row level security" in sql
    assert "create policy transactional_outbox_backend_access" in sql


def test_outbox_downgrade_removes_only_mail_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0009_transactional_outbox:0008_email_verification",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop policy transactional_outbox_backend_access" in sql
    assert "drop table app_private.transactional_outbox" in sql
    assert "drop table app_private.email_verification_tokens" not in sql
