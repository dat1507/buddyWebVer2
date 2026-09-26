"""Tests for the SQLAlchemy and Alembic foundation introduced by BE-003."""

import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def migration_test_url() -> str:
    parts = (
        "postgresql://",
        "migration-user",
        ":",
        "test-only-credential",
        "@",
        "localhost:5432/postgres?sslmode=disable",
    )
    return "".join(parts)


def test_sqlalchemy_major_version_is_two() -> None:
    assert version("SQLAlchemy").split(".", maxsplit=1)[0] == "2"


def test_alembic_script_directory_is_loadable() -> None:
    script_directory = ScriptDirectory.from_config(migration_config())
    user_revision = script_directory.get_revision("0002_users")
    refresh_revision = script_directory.get_revision("0003_refresh_sessions")
    audit_revision = script_directory.get_revision("0004_audit_logs")
    storage_revision = script_directory.get_revision("0005_storage_buckets")
    profile_revision = script_directory.get_revision("0006_profile_catalogs")
    event_revision = script_directory.get_revision("0007_event_tables")
    email_revision = script_directory.get_revision("0008_email_verification")
    outbox_revision = script_directory.get_revision("0009_transactional_outbox")
    edge_outbox_revision = script_directory.get_revision("0010_edge_email_outbox_functions")
    preference_revision = script_directory.get_revision("0011_preference_persistence")

    assert Path(script_directory.dir).resolve() == PROJECT_ROOT / "alembic"
    assert script_directory.get_heads() == ["0011_preference_persistence"]
    assert user_revision is not None
    assert user_revision.down_revision == "0001_private_app_schema"
    assert refresh_revision is not None
    assert refresh_revision.down_revision == "0002_users"
    assert audit_revision is not None
    assert audit_revision.down_revision == "0003_refresh_sessions"
    assert storage_revision is not None
    assert storage_revision.down_revision == "0004_audit_logs"
    assert profile_revision is not None
    assert profile_revision.down_revision == "0005_storage_buckets"
    assert event_revision is not None
    assert event_revision.down_revision == "0006_profile_catalogs"
    assert email_revision is not None
    assert email_revision.down_revision == "0007_event_tables"
    assert outbox_revision is not None
    assert outbox_revision.down_revision == "0008_email_verification"
    assert edge_outbox_revision is not None
    assert edge_outbox_revision.down_revision == "0009_transactional_outbox"
    assert preference_revision is not None
    assert preference_revision.down_revision == "0010_edge_email_outbox_functions"


def test_database_configuration_is_deferred() -> None:
    config = migration_config()

    assert config.get_alembic_option("sqlalchemy.url") is None


def test_offline_upgrade_renders_private_schema_boundary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, migration_test_url())
    get_migration_database_settings.cache_clear()

    try:
        command.upgrade(migration_config(), "head", sql=True)
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "create schema if not exists app_private" in rendered_sql
    assert "revoke all on schema app_private from public" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql
    assert "grant usage on schema app_private to vgu_buddy_runtime" in rendered_sql
    assert "create type app_private.user_role as enum ('user', 'admin')" in rendered_sql
    assert "create table app_private.users" in rendered_sql
    assert "constraint pk_users primary key (id)" in rendered_sql
    assert "constraint uq_users_email unique (email)" in rendered_sql
    assert "constraint ck_users_email_not_blank" in rendered_sql
    assert "constraint ck_users_password_hash_not_empty" in rendered_sql
    assert "create index ix_users_role on app_private.users (role)" in rendered_sql
    assert "create index ix_users_is_active on app_private.users (is_active)" in rendered_sql
    assert "revoke all on table app_private.users from public" in rendered_sql
    assert "revoke all on type app_private.user_role from public" in rendered_sql
    assert (
        "grant select, insert, update, delete on table app_private.users "
        "to vgu_buddy_runtime" in rendered_sql
    )
    assert "grant usage on type app_private.user_role to vgu_buddy_runtime" in rendered_sql
    assert "alter table app_private.users enable row level security" in rendered_sql
    assert "create policy users_backend_access" in rendered_sql
    assert "to vgu_buddy_runtime" in rendered_sql
    assert "using (true)" in rendered_sql
    assert "with check (true)" in rendered_sql
    assert "create table app_private.refresh_sessions" in rendered_sql
    assert "constraint pk_refresh_sessions primary key (id)" in rendered_sql
    assert (
        "constraint uq_refresh_sessions_refresh_token_id unique (refresh_token_id)" in rendered_sql
    )
    assert "constraint fk_refresh_sessions_user_id_users" in rendered_sql
    assert "references app_private.users (id) on delete cascade" in rendered_sql
    assert (
        "create index ix_refresh_sessions_user_id "
        "on app_private.refresh_sessions (user_id)" in rendered_sql
    )
    assert (
        "create index ix_refresh_sessions_expires_at "
        "on app_private.refresh_sessions (expires_at)" in rendered_sql
    )
    assert "revoke all on table app_private.refresh_sessions from public" in rendered_sql
    assert (
        "grant select, insert, update, delete on table app_private.refresh_sessions "
        "to vgu_buddy_runtime" in rendered_sql
    )
    assert "alter table app_private.refresh_sessions enable row level security" in rendered_sql
    assert "create policy refresh_sessions_backend_access" in rendered_sql
    assert "create table app_private.audit_logs" in rendered_sql
    assert "constraint pk_audit_logs primary key (id)" in rendered_sql
    assert "constraint fk_audit_logs_admin_id_users" in rendered_sql
    assert "references app_private.users (id) on delete restrict" in rendered_sql
    assert "constraint ck_audit_logs_action_length" in rendered_sql
    assert "constraint ck_audit_logs_resource_type_length" in rendered_sql
    assert (
        "create index ix_audit_logs_admin_id_created_at "
        "on app_private.audit_logs (admin_id, created_at)" in rendered_sql
    )
    assert (
        "create index ix_audit_logs_resource_type_resource_id "
        "on app_private.audit_logs (resource_type, resource_id)" in rendered_sql
    )
    assert "revoke all on table app_private.audit_logs from public" in rendered_sql
    assert "revoke all on table app_private.audit_logs from vgu_buddy_runtime" in rendered_sql
    assert (
        "grant select, insert on table app_private.audit_logs to vgu_buddy_runtime" in rendered_sql
    )
    assert "alter table app_private.audit_logs enable row level security" in rendered_sql
    assert "create policy audit_logs_backend_read" in rendered_sql
    assert "for select" in rendered_sql
    assert "create policy audit_logs_backend_insert" in rendered_sql
    assert "for insert" in rendered_sql
    assert "to_regclass('storage.objects')" in rendered_sql
    assert "'profile-images'" in rendered_sql
    assert "'event-media'" in rendered_sql
    assert "'event-slider-images'" in rendered_sql
    assert "insert into storage.buckets" not in rendered_sql
    assert "create policy vgu_buddy_clients_no_image_select" in rendered_sql
    assert "create policy vgu_buddy_clients_no_image_insert" in rendered_sql
    assert "create policy vgu_buddy_clients_no_image_update" in rendered_sql
    assert "create policy vgu_buddy_clients_no_image_delete" in rendered_sql
    assert rendered_sql.count("as restrictive") >= 4
    assert rendered_sql.count("to anon, authenticated") >= 4
    assert (
        "bucket_id not in ('profile-images', 'event-media', 'event-slider-images')" in rendered_sql
    )


def test_offline_user_downgrade_removes_table_and_enum(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, migration_test_url())
    get_migration_database_settings.cache_clear()

    try:
        command.downgrade(
            migration_config(),
            "0002_users:0001_private_app_schema",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "drop policy users_backend_access on app_private.users" in rendered_sql
    assert "drop index app_private.ix_users_role" in rendered_sql
    assert "drop index app_private.ix_users_is_active" in rendered_sql
    assert "drop table app_private.users" in rendered_sql
    assert "drop type app_private.user_role" in rendered_sql


def test_offline_refresh_session_downgrade_removes_policy_indexes_and_table(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, migration_test_url())
    get_migration_database_settings.cache_clear()

    try:
        command.downgrade(
            migration_config(),
            "0003_refresh_sessions:0002_users",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert (
        "drop policy refresh_sessions_backend_access on app_private.refresh_sessions"
        in rendered_sql
    )
    assert "drop index app_private.ix_refresh_sessions_expires_at" in rendered_sql
    assert "drop index app_private.ix_refresh_sessions_user_id" in rendered_sql
    assert "drop table app_private.refresh_sessions" in rendered_sql


def test_offline_audit_log_downgrade_removes_policies_indexes_and_table(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, migration_test_url())
    get_migration_database_settings.cache_clear()

    try:
        command.downgrade(
            migration_config(),
            "0004_audit_logs:0003_refresh_sessions",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "drop policy audit_logs_backend_insert on app_private.audit_logs" in rendered_sql
    assert "drop policy audit_logs_backend_read on app_private.audit_logs" in rendered_sql
    assert "drop index app_private.ix_audit_logs_resource_type_resource_id" in rendered_sql
    assert "drop index app_private.ix_audit_logs_admin_id_created_at" in rendered_sql
    assert "drop table app_private.audit_logs" in rendered_sql


def test_offline_storage_downgrade_removes_only_policies(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, migration_test_url())
    get_migration_database_settings.cache_clear()

    try:
        command.downgrade(
            migration_config(),
            "0005_storage_buckets:0004_audit_logs",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "drop policy if exists vgu_buddy_clients_no_image_delete" in rendered_sql
    assert "drop policy if exists vgu_buddy_clients_no_image_update" in rendered_sql
    assert "drop policy if exists vgu_buddy_clients_no_image_insert" in rendered_sql
    assert "drop policy if exists vgu_buddy_clients_no_image_select" in rendered_sql
    assert "delete from storage.buckets" not in rendered_sql


def test_alembic_cli_reads_pyproject_configuration() -> None:
    environment = os.environ.copy()
    environment[MIGRATION_URL_VARIABLE] = migration_test_url()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "pyproject.toml",
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "create schema if not exists app_private" in result.stdout.lower()
