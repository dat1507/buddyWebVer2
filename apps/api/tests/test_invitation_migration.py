"""Offline SQL contract checks for the INV-001 migration."""

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


def test_invitation_upgrade_renders_private_lifecycle_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0011_preference_persistence:0012_invitation_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "create type app_private.invitation_status as enum "
        "('pending', 'accepted', 'declined', 'cancelled', 'expired')" in rendered_sql
    )
    assert "create table app_private.matching_invitations" in rendered_sql
    assert "generated always as (least(sender_id, recipient_id)) stored" in rendered_sql
    assert "generated always as (greatest(sender_id, recipient_id)) stored" in rendered_sql
    assert "constraint ck_matching_invitations_distinct_participants" in rendered_sql
    assert "constraint ck_matching_invitations_status_timestamps" in rendered_sql
    assert "constraint ck_matching_invitations_expiry_interval" in rendered_sql
    assert "expires_at = created_at + interval '7 days'" in rendered_sql
    assert "create unique index uq_matching_invitations_pending_pair" in rendered_sql
    assert "where status = 'pending'" in rendered_sql
    assert "create index ix_matching_invitations_pending_expires_at" in rendered_sql
    assert "create index ix_matching_invitations_sender_status_created_at" in rendered_sql
    assert "create index ix_matching_invitations_recipient_status_created_at" in rendered_sql
    assert "revoke all on table app_private.matching_invitations from public" in rendered_sql
    assert (
        "revoke all on table app_private.matching_invitations from vgu_buddy_runtime"
        in rendered_sql
    )
    assert (
        "grant select, insert, update on table app_private.matching_invitations "
        "to vgu_buddy_runtime" in rendered_sql
    )
    assert (
        "grant select, insert, update, delete on table app_private.matching_invitations"
        not in rendered_sql
    )
    assert "alter table app_private.matching_invitations enable row level security" in rendered_sql
    assert "create policy matching_invitations_backend_access" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql


def test_invitation_downgrade_removes_only_inv001_objects(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0012_invitation_persistence:0011_preference_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "drop policy matching_invitations_backend_access "
        "on app_private.matching_invitations" in rendered_sql
    )
    assert "drop index app_private.uq_matching_invitations_pending_pair" in rendered_sql
    assert "drop index app_private.ix_matching_invitations_pending_expires_at" in rendered_sql
    assert "drop table app_private.matching_invitations" in rendered_sql
    assert "drop type app_private.invitation_status" in rendered_sql
    assert "drop table app_private.users" not in rendered_sql
