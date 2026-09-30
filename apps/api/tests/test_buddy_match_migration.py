"""Offline SQL contract checks for the BUDDY-001 migration."""

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


def test_match_upgrade_renders_private_active_pair_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0012_invitation_persistence:0013_active_match_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "create type app_private.match_status as enum ('active')" in rendered_sql
    assert "create table app_private.matches" in rendered_sql
    assert "generated always as (least(participant_one_user_id" in rendered_sql
    assert "generated always as (greatest(participant_one_user_id" in rendered_sql
    assert "constraint ck_matches_distinct_users" in rendered_sql
    assert "constraint ck_matches_distinct_profiles" in rendered_sql
    assert "constraint ck_matches_score_range" in rendered_sql
    assert "constraint uq_matches_accepted_invitation_id" in rendered_sql
    assert "create unique index uq_matches_active_pair" in rendered_sql
    assert "where status = 'active'" in rendered_sql
    assert "create index ix_matches_participant_one_status_activated_at" in rendered_sql
    assert "create index ix_matches_participant_two_status_activated_at" in rendered_sql
    assert "create index ix_matches_participant_one_profile_id" in rendered_sql
    assert "create index ix_matches_participant_two_profile_id" in rendered_sql
    assert "references app_private.users (id) on delete cascade" in rendered_sql
    assert "references app_private.student_profiles (id) on delete cascade" in rendered_sql
    assert "references app_private.matching_invitations (id) on delete cascade" in rendered_sql
    assert "semester_id uuid" in rendered_sql
    assert "references app_private.semesters" not in rendered_sql
    assert "revoke all on table app_private.matches from public" in rendered_sql
    assert "revoke all on table app_private.matches from vgu_buddy_runtime" in rendered_sql
    assert "grant select, insert on table app_private.matches to vgu_buddy_runtime" in rendered_sql
    assert "grant select, insert, update" not in rendered_sql
    assert "alter table app_private.matches enable row level security" in rendered_sql
    assert "create policy matches_backend_access" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql


def test_match_downgrade_removes_only_buddy001_objects(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0013_active_match_persistence:0012_invitation_persistence",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    assert "drop policy matches_backend_access on app_private.matches" in rendered_sql
    assert "drop index app_private.uq_matches_active_pair" in rendered_sql
    assert "drop index app_private.ix_matches_participant_one_status_activated_at" in rendered_sql
    assert "drop table app_private.matches" in rendered_sql
    assert "drop type app_private.match_status" in rendered_sql
    assert "drop table app_private.matching_invitations" not in rendered_sql
