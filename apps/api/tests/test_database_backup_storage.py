"""Private storage tests for SEM-002 database artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError
from uuid import uuid4

import pytest
from pydantic import SecretStr

import app.services.database_backup_storage as backup_storage
from app.core.config import StorageSettings
from app.services.database_backup_storage import (
    DATABASE_BACKUP_BUCKET,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
    DatabaseBackupStorageError,
    PrivateFileDatabaseBackupStore,
    SupabaseDatabaseBackupStore,
)

TEST_SECRET = "sb_secret_sem002-test-only"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> StorageSettings:
    return StorageSettings(
        url="https://project.supabase.co",
        secret_key=SecretStr(TEST_SECRET),
    )


@pytest.mark.anyio
async def test_private_file_store_round_trips_without_exposing_host_path(tmp_path: Path) -> None:
    store = PrivateFileDatabaseBackupStore(tmp_path / "private")
    reference = DatabaseBackupObjectRef(uuid4(), DatabaseBackupObjectKind.MANIFEST)
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_bytes(b'{"manifest_version":1}')

    await store.put_file(reference, source)
    await store.get_file(reference, target)

    assert target.read_bytes() == source.read_bytes()
    assert store.location(reference) == (
        f"private-file://{DATABASE_BACKUP_BUCKET}/{reference.object_key}"
    )
    assert str(tmp_path) not in store.location(reference)
    with pytest.raises(DatabaseBackupStorageError, match="already exists"):
        await store.put_file(reference, source)
    await store.delete(reference)


@pytest.mark.anyio
async def test_supabase_bucket_is_always_private_and_mime_restricted() -> None:
    store = SupabaseDatabaseBackupStore(_settings())
    request = MagicMock(return_value=b"{}")
    store._request = request  # type: ignore[method-assign]

    await store.configure_bucket()

    assert request.call_count == 2
    update = request.call_args_list[1]
    assert update.args == (
        "PUT",
        f"https://project.supabase.co/storage/v1/bucket/{DATABASE_BACKUP_BUCKET}",
    )
    assert json.loads(update.kwargs["body"]) == {
        "public": False,
        "file_size_limit": 512 * 1024 * 1024,
        "allowed_mime_types": ["application/gzip", "application/json"],
    }


@pytest.mark.anyio
async def test_supabase_upload_is_authenticated_non_upsert_and_never_returns_public_url(
    tmp_path: Path,
) -> None:
    store = SupabaseDatabaseBackupStore(_settings())
    request = MagicMock(return_value=b"{}")
    store._request = request  # type: ignore[method-assign]
    reference = DatabaseBackupObjectRef(uuid4(), DatabaseBackupObjectKind.ARTIFACT)
    source = tmp_path / "artifact.tar.gz"
    source.write_bytes(b"postgresql-copy-artifact")

    await store.put_file(reference, source)

    call = request.call_args
    assert call.args == (
        "POST",
        f"https://project.supabase.co/storage/v1/object/{DATABASE_BACKUP_BUCKET}/"
        f"{reference.backup_id}/database/{DatabaseBackupObjectKind.ARTIFACT.value}",
    )
    assert call.kwargs["extra_headers"] == {
        "x-upsert": "false",
        "cache-control": "no-store",
    }
    assert TEST_SECRET not in call.args[1]
    assert "public" not in call.args[1]
    assert store.location(reference).startswith("supabase-storage://")


def test_supabase_errors_are_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    store = SupabaseDatabaseBackupStore(_settings())

    class FailingOpener:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise HTTPError(
                "https://project.supabase.co/storage/v1/object",
                503,
                f"upstream leaked {TEST_SECRET}",
                None,  # type: ignore[arg-type]
                None,
            )

    monkeypatch.setattr(backup_storage, "build_opener", lambda *_args: FailingOpener())

    with pytest.raises(DatabaseBackupStorageError) as raised:
        store._request("GET", "https://project.supabase.co/storage/v1/object")
    assert str(raised.value) == "Database backup storage request failed with HTTP status 503."
    assert TEST_SECRET not in str(raised.value)


def test_object_reference_rejects_untrusted_identity_types() -> None:
    with pytest.raises(DatabaseBackupStorageError):
        DatabaseBackupObjectRef(
            "../../escape",  # type: ignore[arg-type]
            DatabaseBackupObjectKind.MANIFEST,
        )
    with pytest.raises(DatabaseBackupStorageError):
        DatabaseBackupObjectRef(
            uuid4(),
            "manifest.json",  # type: ignore[arg-type]
        )
