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

    assert Path(script_directory.dir).resolve() == PROJECT_ROOT / "alembic"
    assert script_directory.get_heads() == ["0001_private_app_schema"]


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
