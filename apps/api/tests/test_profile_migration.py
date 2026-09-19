"""Offline contract checks for the BE-010 profile migration."""

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


def test_profile_upgrade_renders_schema_constraints_seeds_and_privacy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.upgrade(
            _migration_config(),
            "0005_storage_buckets:0006_profile_catalogs",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    for enum_name in (
        "student_type",
        "language_proficiency",
        "profile_photo_processing_status",
    ):
        assert f"create type app_private.{enum_name}" in rendered_sql
        assert f"revoke all on type app_private.{enum_name} from public" in rendered_sql
        assert (
            f"grant usage on type app_private.{enum_name} to vgu_buddy_runtime"
            in rendered_sql
        )

    for table_name in (
        "student_profiles",
        "interests",
        "languages",
        "profile_interests",
        "profile_languages",
        "profile_photos",
    ):
        assert f"create table app_private.{table_name}" in rendered_sql
        assert f"revoke all on table app_private.{table_name} from public" in rendered_sql
        assert f"alter table app_private.{table_name} enable row level security" in rendered_sql
        assert f"create policy {table_name}_backend_access" in rendered_sql

    assert "constraint uq_student_profiles_user_id unique (user_id)" in rendered_sql
    assert "constraint uq_interests_code unique (code)" in rendered_sql
    assert "constraint pk_languages primary key (code)" in rendered_sql
    assert (
        "constraint pk_profile_interests primary key (profile_id, interest_id)"
        in rendered_sql
    )
    assert (
        "constraint pk_profile_languages primary key (profile_id, language_code)"
        in rendered_sql
    )
    assert (
        "create unique index uq_profile_photos_one_avatar_per_profile "
        "on app_private.profile_photos (profile_id) "
        "where is_avatar and deleted_at is null" in rendered_sql
    )
    assert (
        "create index ix_profile_interests_interest_id "
        "on app_private.profile_interests (interest_id)" in rendered_sql
    )
    assert (
        "create index ix_profile_languages_language_code "
        "on app_private.profile_languages (language_code)" in rendered_sql
    )

    for interest_code in (
        "art",
        "cooking",
        "gaming",
        "hiking",
        "language-exchange",
        "movies",
        "music",
        "photography",
        "reading",
        "sports",
        "technology",
        "travel",
        "volunteering",
    ):
        assert f"('{interest_code}'," in rendered_sql
    for language_code in ("de", "en", "es", "fr", "ja", "ko", "vi", "zh"):
        assert f"('{language_code}'," in rendered_sql
    assert rendered_sql.count("on conflict (code) do update") == 2
    assert "is_active = excluded.is_active" not in rendered_sql
    assert "interests.label_en is distinct from excluded.label_en" in rendered_sql
    assert "languages.label_en is distinct from excluded.label_en" in rendered_sql
    assert "'anon', 'authenticated', 'service_role'" in rendered_sql


def test_profile_downgrade_removes_policies_indexes_tables_and_types(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, _migration_test_url())
    get_migration_database_settings.cache_clear()
    try:
        command.downgrade(
            _migration_config(),
            "0006_profile_catalogs:0005_storage_buckets",
            sql=True,
        )
    finally:
        get_migration_database_settings.cache_clear()

    rendered_sql = capsys.readouterr().out.lower()
    for table_name in (
        "student_profiles",
        "interests",
        "languages",
        "profile_interests",
        "profile_languages",
        "profile_photos",
    ):
        assert (
            f"drop policy {table_name}_backend_access on app_private.{table_name}"
            in rendered_sql
        )
        assert f"drop table app_private.{table_name}" in rendered_sql
    assert "drop index app_private.uq_profile_photos_one_avatar_per_profile" in rendered_sql
    assert "drop index app_private.ix_profile_interests_interest_id" in rendered_sql
    assert "drop index app_private.ix_profile_languages_language_code" in rendered_sql
    assert "drop type app_private.profile_photo_processing_status" in rendered_sql
    assert "drop type app_private.language_proficiency" in rendered_sql
    assert "drop type app_private.student_type" in rendered_sql
