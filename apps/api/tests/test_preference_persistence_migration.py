"""Offline contract checks for the PREF-001 migration."""

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


def test_preference_upgrade_renders_constraints_migration_and_permissions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0010_edge_email_outbox_functions:0011_preference_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "create type app_private.preference_kind "
        "as enum ('interest', 'language', 'activity')" in rendered_sql
    )
    for table_name in (
        "activities",
        "profile_activities",
        "profile_custom_preferences",
    ):
        assert f"create table app_private.{table_name}" in rendered_sql
        assert f"revoke all on table app_private.{table_name} from public" in rendered_sql
        assert (
            f"revoke all on table app_private.{table_name} from vgu_buddy_runtime"
            in rendered_sql
        )
        assert f"alter table app_private.{table_name} enable row level security" in rendered_sql

    assert "constraint uq_activities_code unique (code)" in rendered_sql
    assert (
        "constraint pk_profile_activities primary key (profile_id, activity_id)"
        in rendered_sql
    )
    assert (
        "constraint uq_profile_custom_preferences_profile_kind_key "
        "unique (profile_id, kind, normalized_key)" in rendered_sql
    )
    assert "on delete cascade" in rendered_sql
    assert "on delete restrict" in rendered_sql
    assert "cannot migrate preferred activities" in rendered_sql
    assert "from app_private.interests as interest" in rendered_sql
    assert "on conflict (code) do update" in rendered_sql
    assert "is_active = excluded.is_active" not in rendered_sql
    assert "insert into app_private.profile_activities" in rendered_sql
    assert "on conflict (profile_id, activity_id) do nothing" in rendered_sql
    assert "grant select on table app_private.activities to vgu_buddy_runtime" in rendered_sql
    assert (
        "grant select, insert, delete on table app_private.profile_activities "
        "to vgu_buddy_runtime" in rendered_sql
    )
    assert (
        "grant select, insert, update, delete "
        "on table app_private.profile_custom_preferences to vgu_buddy_runtime"
        in rendered_sql
    )
    assert "grant usage on type app_private.preference_kind to vgu_buddy_runtime" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql


def test_preference_downgrade_removes_only_pref001_objects(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0011_preference_persistence:0010_edge_email_outbox_functions",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "drop policy activities_backend_read on app_private.activities" in rendered_sql
    assert (
        "drop policy profile_activities_backend_access "
        "on app_private.profile_activities" in rendered_sql
    )
    assert (
        "drop policy profile_custom_preferences_backend_access "
        "on app_private.profile_custom_preferences" in rendered_sql
    )
    assert "drop index app_private.ix_profile_activities_activity_id" in rendered_sql
    assert (
        "drop index app_private.ix_profile_custom_preferences_kind_normalized_key"
        in rendered_sql
    )
    assert "drop table app_private.profile_custom_preferences" in rendered_sql
    assert "drop table app_private.profile_activities" in rendered_sql
    assert "drop table app_private.activities" in rendered_sql
    assert "drop type app_private.preference_kind" in rendered_sql
    assert "drop table app_private.interests" not in rendered_sql
    assert "drop table app_private.languages" not in rendered_sql
