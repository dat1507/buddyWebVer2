"""Private artifact storage boundary for semester database backups."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from app.core.config import StorageSettings

DATABASE_BACKUP_BUCKET = "semester-database-backups"
MAX_DATABASE_BACKUP_BYTES = 512 * 1024 * 1024
_COPY_BUFFER_BYTES = 1024 * 1024


class DatabaseBackupStorageError(RuntimeError):
    """Sanitized private-storage failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DatabaseBackupObjectKind(StrEnum):
    ARTIFACT = "database-artifact-v1.tar.gz"
    MANIFEST = "database-manifest-v1.json"

    @property
    def content_type(self) -> str:
        if self is DatabaseBackupObjectKind.ARTIFACT:
            return "application/gzip"
        return "application/json"


@dataclass(frozen=True, slots=True)
class DatabaseBackupObjectRef:
    """Server-generated object identity; callers cannot provide bucket paths."""

    backup_id: UUID
    kind: DatabaseBackupObjectKind

    def __post_init__(self) -> None:
        if not isinstance(self.backup_id, UUID) or not isinstance(
            self.kind, DatabaseBackupObjectKind
        ):
            raise DatabaseBackupStorageError("Database backup object identity is invalid.")

    @property
    def object_key(self) -> str:
        return f"{self.backup_id}/database/{self.kind.value}"

    @property
    def content_type(self) -> str:
        return self.kind.content_type


class BackupStorageObjectRef(Protocol):
    """Trusted server-generated reference accepted by the shared private store."""

    @property
    def object_key(self) -> str: ...

    @property
    def content_type(self) -> str: ...


class DatabaseBackupArtifactStore(Protocol):
    """Minimal private object-store contract used by backup orchestration."""

    def location(self, reference: BackupStorageObjectRef) -> str: ...

    async def put_file(self, reference: BackupStorageObjectRef, source: Path) -> None: ...

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None: ...

    async def delete(self, reference: BackupStorageObjectRef) -> None: ...


def _assert_bounded_file(path: Path) -> int:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise DatabaseBackupStorageError("Database backup artifact is unavailable.") from error
    if not 1 <= size <= MAX_DATABASE_BACKUP_BYTES:
        raise DatabaseBackupStorageError("Database backup artifact size is invalid.")
    return size


class PrivateFileDatabaseBackupStore:
    """Filesystem-backed private store for disposable/local acceptance only."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(self._root, 0o700)
        except OSError:
            pass

    def _path(self, reference: BackupStorageObjectRef) -> Path:
        candidate = (self._root / reference.object_key).resolve()
        if self._root not in candidate.parents:
            raise DatabaseBackupStorageError("Database backup object identity is invalid.")
        return candidate

    def location(self, reference: BackupStorageObjectRef) -> str:
        return f"private-file://{DATABASE_BACKUP_BUCKET}/{reference.object_key}"

    @staticmethod
    def _copy_exclusive(source: Path, target: Path) -> None:
        _assert_bounded_file(source)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(target.parent, 0o700)
        except OSError:
            pass
        try:
            with source.open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=_COPY_BUFFER_BYTES)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        except FileExistsError as error:
            raise DatabaseBackupStorageError("Database backup object already exists.") from error
        except OSError as error:
            target.unlink(missing_ok=True)
            raise DatabaseBackupStorageError("Database backup storage is unavailable.") from error

    async def put_file(self, reference: BackupStorageObjectRef, source: Path) -> None:
        await asyncio.to_thread(self._copy_exclusive, source, self._path(reference))

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None:
        source = self._path(reference)
        await asyncio.to_thread(self._copy_exclusive, source, target)

    async def delete(self, reference: BackupStorageObjectRef) -> None:
        try:
            await asyncio.to_thread(self._path(reference).unlink, missing_ok=True)
        except OSError as error:
            raise DatabaseBackupStorageError("Database backup cleanup failed.") from error


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        return None


class SupabaseDatabaseBackupStore:
    """Server-only adapter for one dedicated private Supabase Storage bucket."""

    def __init__(self, settings: StorageSettings, *, timeout_seconds: float = 60.0) -> None:
        self._base_url = settings.url.rstrip("/")
        self._secret_key = settings.secret_key.get_secret_value()
        self._timeout_seconds = timeout_seconds

    def _url(self, operation: str, reference: BackupStorageObjectRef | None = None) -> str:
        suffix = ""
        if reference is not None:
            key = "/".join(quote(part, safe="") for part in reference.object_key.split("/"))
            suffix = f"/{quote(DATABASE_BACKUP_BUCKET, safe='')}/{key}"
        return f"{self._base_url}/storage/v1/{operation}{suffix}"

    def _headers(self, *, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._secret_key,
            "User-Agent": "vgu-buddy-api/0.1",
        }
        if self._secret_key.startswith("eyJ") and self._secret_key.count(".") == 2:
            headers["Authorization"] = f"Bearer {self._secret_key}"
        if content_type is not None:
            headers["Content-Type"] = content_type
        return headers

    @staticmethod
    def _provider_status_code(error: HTTPError) -> int:
        try:
            payload = json.loads(error.read(4096))
        except (AttributeError, OSError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return error.code
        if not isinstance(payload, dict):
            return error.code
        status = payload.get("statusCode")
        if isinstance(status, str) and status.isdecimal():
            status = int(status)
        return status if type(status) is int and 400 <= status <= 599 else error.code

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
        maximum_response_bytes: int = 64 * 1024,
    ) -> bytes:
        headers = self._headers(content_type=content_type)
        if extra_headers:
            headers.update(extra_headers)
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with build_opener(_RejectRedirects()).open(
                request, timeout=self._timeout_seconds
            ) as response:
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > maximum_response_bytes:
                    raise DatabaseBackupStorageError(
                        "Database backup storage returned an oversized object."
                    )
                result = cast(bytes, response.read(maximum_response_bytes + 1))
                if len(result) > maximum_response_bytes:
                    raise DatabaseBackupStorageError(
                        "Database backup storage returned an oversized object."
                    )
                return result
        except DatabaseBackupStorageError:
            raise
        except HTTPError as error:
            raise DatabaseBackupStorageError(
                f"Database backup storage request failed with HTTP status {error.code}.",
                status_code=self._provider_status_code(error),
            ) from None
        except (OSError, TimeoutError, URLError, ValueError):
            raise DatabaseBackupStorageError("Database backup storage is unavailable.") from None

    def location(self, reference: BackupStorageObjectRef) -> str:
        return f"supabase-storage://{DATABASE_BACKUP_BUCKET}/{reference.object_key}"

    def _put_file_sync(self, reference: BackupStorageObjectRef, source: Path) -> None:
        size = _assert_bounded_file(source)
        try:
            content = source.read_bytes()
        except OSError as error:
            raise DatabaseBackupStorageError("Database backup artifact is unavailable.") from error
        if len(content) != size:
            raise DatabaseBackupStorageError("Database backup artifact changed during upload.")
        self._request(
            "POST",
            self._url("object", reference),
            body=content,
            content_type=reference.content_type,
            extra_headers={"x-upsert": "false", "cache-control": "no-store"},
        )

    async def put_file(self, reference: BackupStorageObjectRef, source: Path) -> None:
        await asyncio.to_thread(self._put_file_sync, reference, source)

    def _get_file_sync(self, reference: BackupStorageObjectRef, target: Path) -> None:
        content = self._request(
            "GET",
            self._url("object/authenticated", reference),
            maximum_response_bytes=MAX_DATABASE_BACKUP_BYTES,
        )
        if not content:
            raise DatabaseBackupStorageError("Database backup storage returned an empty object.")
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            with target.open("xb") as writer:
                writer.write(content)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        except FileExistsError as error:
            raise DatabaseBackupStorageError(
                "Database backup download target already exists."
            ) from error
        except OSError as error:
            target.unlink(missing_ok=True)
            raise DatabaseBackupStorageError("Database backup download failed.") from error

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None:
        await asyncio.to_thread(self._get_file_sync, reference, target)

    async def delete(self, reference: BackupStorageObjectRef) -> None:
        await asyncio.to_thread(
            self._request,
            "DELETE",
            self._url("object", reference),
        )

    async def configure_bucket(self) -> None:
        """Create or converge the dedicated bucket as private and MIME-restricted."""
        bucket_url = f"{self._base_url}/storage/v1/bucket/{quote(DATABASE_BACKUP_BUCKET, safe='')}"
        policy = {
            "public": False,
            "file_size_limit": MAX_DATABASE_BACKUP_BYTES,
            "allowed_mime_types": [
                "application/gzip",
                "application/json",
                "image/jpeg",
                "image/png",
                "image/webp",
            ],
        }
        try:
            await asyncio.to_thread(self._request, "GET", bucket_url)
        except DatabaseBackupStorageError as error:
            if error.status_code != 404:
                raise
            create = json.dumps(
                {"id": DATABASE_BACKUP_BUCKET, "name": DATABASE_BACKUP_BUCKET, **policy},
                separators=(",", ":"),
            ).encode()
            try:
                await asyncio.to_thread(
                    self._request,
                    "POST",
                    f"{self._base_url}/storage/v1/bucket",
                    body=create,
                    content_type="application/json",
                )
                return
            except DatabaseBackupStorageError as create_error:
                if create_error.status_code != 409:
                    raise
        await asyncio.to_thread(
            self._request,
            "PUT",
            bucket_url,
            body=json.dumps(policy, separators=(",", ":")).encode(),
            content_type="application/json",
        )
