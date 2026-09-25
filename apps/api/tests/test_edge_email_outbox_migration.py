"""Offline migration contract checks for the Supabase Edge email worker."""

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


def test_edge_outbox_upgrade_renders_atomic_least_privilege_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0009_transactional_outbox:0010_edge_email_outbox_functions",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = " ".join(capsys.readouterr().out.lower().split())
    assert "create function app_private.claim_transactional_email_outbox" in sql
    assert "create function app_private.complete_transactional_email_outbox" in sql
    assert "create function app_private.fail_transactional_email_outbox" in sql
    assert sql.count("security invoker") == 3
    assert "for update skip locked" in sql
    assert "limit p_batch_size" in sql
    assert "lease_expires_at = statement_timestamp() + interval '5 minutes'" in sql
    assert "outbox.lease_owner = btrim(p_worker_id)" in sql
    assert "outbox.attempts + 1 < 5" in sql
    assert "power(2, greatest(outbox.attempts, 0))" in sql
    assert "revoke all on function %s from %i" in sql
    assert "'anon', 'authenticated', 'service_role'" in sql
    assert sql.count("to vgu_buddy_runtime") == 3
    assert "security definer" not in sql


def test_edge_outbox_downgrade_removes_only_worker_functions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0010_edge_email_outbox_functions:0009_transactional_outbox",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop function app_private.claim_transactional_email_outbox(text, integer)" in sql
    assert "drop function app_private.complete_transactional_email_outbox(uuid, text, text)" in sql
    assert (
        "drop function app_private.fail_transactional_email_outbox(uuid, text, boolean, text)"
        in sql
    )
    assert "drop table app_private.transactional_outbox" not in sql
