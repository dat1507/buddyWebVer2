"""Offline SQL contract checks for the SEM-001 migration."""

from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _url() -> str:
    return "postgresql://migration-user:test-only@localhost/postgres?sslmode=disable"


def test_upgrade_renders_boundary_state_machine_and_private_access(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _config(),
            "0016_chat_message_cleanup:0017_semester_boundary_metadata",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "create type app_private.semester_status as enum ('current', 'closed')" in sql
    assert "create type app_private.semester_operation_type as enum ('reset', 'restore')" in sql
    assert "'requested', 'running', 'succeeded', 'failed'" in sql
    assert "'creating', 'ready', 'restore_blocked_new_data', 'expired', 'failed'" in sql
    assert "create table app_private.semesters" in sql
    assert "create table app_private.semester_operations" in sql
    assert "create table app_private.semester_backups" in sql
    assert "create unique index uq_semesters_current" in sql
    assert "where status = 'current'" in sql
    assert "create unique index uq_semester_operations_running" in sql
    assert "constraint ck_users_role_semester" in sql
    assert "references app_private.semesters (id) on delete restrict" in sql
    assert "alter table app_private.matches alter column semester_id set not null" in sql
    assert (
        "alter table app_private.buddy_conversations alter column semester_id set not null" in sql
    )
    assert "constraint ck_semester_operations_lifecycle" in sql
    assert "constraint ck_semester_backups_lifecycle" in sql
    assert "create trigger trg_semesters_immutable_boundary" in sql
    assert "create trigger trg_users_stamp_semester" in sql
    assert "create trigger trg_matches_stamp_semester" in sql
    assert "create trigger trg_buddy_conversations_stamp_semester" in sql
    assert "create trigger trg_semester_operations_integrity" in sql
    assert "create trigger trg_semester_backups_integrity" in sql
    assert "revoke all on table app_private.semesters from public" in sql
    assert "revoke all on table app_private.semester_operations from public" in sql
    assert "revoke all on table app_private.semester_backups from public" in sql
    assert "alter table app_private.semesters enable row level security" in sql
    assert "grant select on table app_private.semesters to vgu_buddy_runtime" in sql
    assert "grant select, insert, update on table app_private.semester_operations" in sql
    assert "grant select, insert, update on table app_private.semester_backups" in sql
    assert "grant delete" not in sql


def test_downgrade_removes_only_semester_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _config(),
            "0017_semester_boundary_metadata:0016_chat_message_cleanup",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop table app_private.semester_backups" in sql
    assert "drop table app_private.semester_operations" in sql
    assert "drop table app_private.semesters" in sql
    assert "alter table app_private.users drop column semester_id" in sql
    assert "alter table app_private.matches alter column semester_id drop not null" in sql
    assert (
        "alter table app_private.buddy_conversations alter column semester_id drop not null" in sql
    )
    assert "drop table app_private.users" not in sql
    assert "drop table app_private.matches" not in sql
    assert "drop table app_private.buddy_conversations" not in sql


def test_verification_upgrade_allows_pre_reset_proof_and_locks_retention(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _config(),
            "0017_semester_boundary_metadata:0018_backup_verification",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop constraint ck_semester_backups_lifecycle" in sql
    assert "state = 'creating' and expires_at is null and failure_code is null" in sql
    assert "old.verified_at is not null" in sql
    assert "new.verified_at is distinct from old.verified_at" in sql
    assert "old.expires_at is not null" in sql
    assert "new.expires_at is distinct from old.expires_at" in sql
    assert "create type app_private.semester_backup_state" not in sql


def test_verification_downgrade_fails_closed_for_active_verified_backup(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _config(),
            "0018_backup_verification:0017_semester_boundary_metadata",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "cannot downgrade with a verified creating backup" in sql
    assert "state = 'creating' and verified_at is null" in sql
    assert "drop table app_private.semester_backups" not in sql


def test_reset_upgrade_installs_private_fixed_scope_function_and_write_barrier(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _config(),
            "0018_backup_verification:0019_semester_reset_execution",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "create function app_private.acquire_semester_write_barrier()" in sql
    assert "pg_advisory_xact_lock_shared" in sql
    assert "vgu-buddy:semester-write-barrier:v1" in sql
    assert "create trigger trg_users_semester_write_barrier" in sql
    assert "create trigger trg_matching_invitations_semester_write_barrier" in sql
    assert "create trigger trg_buddy_messages_semester_write_barrier" in sql
    assert "create function app_private.execute_semester_reset(" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "pg_try_advisory_xact_lock" in sql
    assert "state = 'succeeded'" in sql
    assert "insert into app_private.semesters" in sql
    assert "delete from app_private.users" in sql
    assert "delete from app_private.buddy_messages" in sql
    assert "delete from app_private.transactional_outbox" in sql
    assert "grant execute on function app_private.execute_semester_reset" in sql
    assert "revoke all on function app_private.execute_semester_reset" in sql
    assert "grant delete" not in sql
    assert (
        "execute format"
        not in sql.split("create function app_private.execute_semester_reset", maxsplit=1)[1].split(
            "$$;", maxsplit=1
        )[0]
    )


def test_reset_downgrade_removes_only_execution_primitives(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _config(),
            "0019_semester_reset_execution:0018_backup_verification",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    sql = capsys.readouterr().out.lower()
    assert "drop function app_private.execute_semester_reset" in sql
    assert "drop trigger trg_users_semester_write_barrier" in sql
    assert "drop trigger trg_buddy_messages_semester_write_barrier" in sql
    assert "drop function app_private.acquire_semester_write_barrier" in sql
    assert "drop table app_private.users" not in sql
    assert "drop table app_private.semesters" not in sql
