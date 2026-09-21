"""Offline contract checks for the EVT-003 Event persistence migration."""

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


def test_event_upgrade_renders_tables_constraints_indexes_and_privacy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0006_profile_catalogs:0007_event_tables",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    for enum_name in (
        "event_status",
        "event_visibility",
        "event_media_usage",
        "event_media_processing_status",
        "event_registration_status",
    ):
        assert f"create type app_private.{enum_name}" in rendered_sql
        assert f"revoke all on type app_private.{enum_name} from public" in rendered_sql
        assert f"grant usage on type app_private.{enum_name} to vgu_buddy_runtime" in rendered_sql

    for table_name in ("events", "event_media", "event_registrations"):
        assert f"create table app_private.{table_name}" in rendered_sql
        assert f"revoke all on table app_private.{table_name} from public" in rendered_sql
        assert (
            "grant select, insert, update, delete on table "
            f"app_private.{table_name} to vgu_buddy_runtime" in rendered_sql
        )
        assert f"alter table app_private.{table_name} enable row level security" in rendered_sql
        assert f"create policy {table_name}_backend_access" in rendered_sql

    assert rendered_sql.index("create table app_private.events") < rendered_sql.index(
        "create table app_private.event_media"
    )
    assert rendered_sql.index("create table app_private.event_media") < rendered_sql.index(
        "constraint fk_events_cover_media_owner_event_media"
    )
    assert rendered_sql.index(
        "constraint fk_events_cover_media_owner_event_media"
    ) < rendered_sql.index("create table app_private.event_registrations")

    assert (
        "create type app_private.event_status as enum ('draft', 'published', 'cancelled')"
        in rendered_sql
    )
    assert "create type app_private.event_visibility as enum ('public', 'members')" in rendered_sql
    assert "constraint ck_events_date_order" in rendered_sql
    assert "constraint ck_events_registration_url_https" in rendered_sql
    assert "constraint fk_events_created_by_users" in rendered_sql
    assert "constraint fk_events_updated_by_users" in rendered_sql
    assert rendered_sql.count("references app_private.users (id) on delete restrict") >= 3

    assert "constraint uq_event_media_object_key unique (object_key)" in rendered_sql
    assert "constraint uq_event_media_id_event_id unique (id, event_id)" in rendered_sql
    assert "constraint fk_event_media_event_id_events" in rendered_sql
    assert "references app_private.events (id) on delete cascade" in rendered_sql
    assert "constraint fk_events_cover_media_owner_event_media" in rendered_sql
    assert "foreign key(cover_media_id, id)" in rendered_sql
    assert "references app_private.event_media (id, event_id) on delete restrict" in rendered_sql

    assert (
        "constraint uq_event_registrations_event_id_user_id "
        "unique (event_id, user_id)" in rendered_sql
    )
    assert "constraint fk_event_registrations_user_id_users" in rendered_sql
    assert "create index ix_events_status on app_private.events (status)" in rendered_sql
    assert "create index ix_events_start_date on app_private.events (start_date)" in rendered_sql
    assert (
        "create index ix_event_media_event_id_usage_sort_order "
        "on app_private.event_media (event_id, usage, sort_order)" in rendered_sql
    )
    assert (
        "create index ix_event_registrations_user_id "
        "on app_private.event_registrations (user_id)" in rendered_sql
    )
    assert {"url", "signed_url", "public_url"}.isdisjoint(
        line.strip().split()[0] for line in rendered_sql.splitlines() if line.strip()
    )
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql


def test_event_downgrade_removes_policies_fk_indexes_tables_and_types(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0007_event_tables:0006_profile_catalogs",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    for table_name in ("events", "event_media", "event_registrations"):
        assert (
            f"drop policy {table_name}_backend_access on app_private.{table_name}" in rendered_sql
        )
        assert f"drop table app_private.{table_name}" in rendered_sql

    assert "drop constraint fk_events_cover_media_owner_event_media" in rendered_sql
    assert "drop index app_private.ix_events_status" in rendered_sql
    assert "drop index app_private.ix_events_start_date" in rendered_sql
    assert "drop index app_private.ix_event_media_event_id_usage_sort_order" in rendered_sql
    assert "drop index app_private.ix_event_registrations_user_id" in rendered_sql
    for enum_name in (
        "event_status",
        "event_visibility",
        "event_media_usage",
        "event_media_processing_status",
        "event_registration_status",
    ):
        assert f"drop type app_private.{enum_name}" in rendered_sql
