"""Validated image processing and server-only Supabase Storage lifecycle helpers."""

from __future__ import annotations

import asyncio
import json
import re
import warnings
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import column, select, table, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import StorageSettings
from app.core.database import APPLICATION_SCHEMA

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096
MAX_DECODED_PIXELS = MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION
MAX_SIGNED_URL_SECONDS = 300
STORAGE_PAGE_SIZE = 100

_MANAGED_OBJECT_KEY = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    r"\.(?:jpg|png|webp)$"
)
_SAFE_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ImageBucket(StrEnum):
    """Server-owned bucket selection; request payloads never supply these values."""

    PROFILE_IMAGES = "profile-images"
    EVENT_MEDIA = "event-media"
    EVENT_SLIDER_IMAGES = "event-slider-images"

    @property
    def is_public(self) -> bool:
        return self is ImageBucket.EVENT_SLIDER_IMAGES


class ImageValidationError(ValueError):
    """Raised before storage is touched when an uploaded image is unsafe or invalid."""


class StorageOperationError(RuntimeError):
    """Sanitized failure from the external Storage boundary."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class StorageReconciliationError(RuntimeError):
    """Raised when orphan reconciliation cannot establish a safe reference boundary."""


@dataclass(frozen=True, slots=True)
class PreparedImage:
    content: bytes = field(repr=False)
    mime_type: str
    extension: str
    byte_size: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class StorageObjectRef:
    bucket: ImageBucket
    object_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.bucket, ImageBucket):
            raise ImageValidationError("Storage bucket must be selected by trusted server code.")
        if _MANAGED_OBJECT_KEY.fullmatch(self.object_key) is None:
            raise ImageValidationError("Storage object key is not a server-generated image key.")
        try:
            UUID(self.object_key.rsplit(".", maxsplit=1)[0], version=4)
        except ValueError as error:
            raise ImageValidationError("Storage object key is not a valid UUID key.") from error


@dataclass(frozen=True, slots=True)
class StoredImage:
    reference: StorageObjectRef
    mime_type: str
    byte_size: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ListedStorageObject:
    object_key: str
    created_at: datetime | None


@dataclass(frozen=True, slots=True)
class ImageReplacement:
    image: StoredImage
    cleanup_pending: bool


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    scanned: int
    protected: int
    too_new: int
    unmanaged: int
    candidates: int
    deleted: int
    failed: int


class StorageTransport(Protocol):
    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None: ...

    async def delete(self, reference: StorageObjectRef) -> None: ...

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]: ...

    async def create_signed_url(
        self,
        reference: StorageObjectRef,
        expires_in: int,
    ) -> str: ...

    def public_url(self, reference: StorageObjectRef) -> str: ...


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


class SupabaseStorageTransport:
    """Minimal server-only client for the Supabase Storage REST API."""

    def __init__(self, settings: StorageSettings, *, timeout_seconds: float = 10.0) -> None:
        self._base_url = settings.url.rstrip("/")
        self._secret_key = settings.secret_key.get_secret_value()
        self._timeout_seconds = timeout_seconds

    def _url(self, operation: str, *segments: str) -> str:
        encoded = "/".join(quote(segment, safe="") for segment in segments)
        suffix = f"/{encoded}" if encoded else ""
        return f"{self._base_url}/storage/v1/{operation}{suffix}"

    def _request_sync(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        headers = self._authentication_headers()
        if content_type is not None:
            headers["Content-Type"] = content_type
        if extra_headers is not None:
            headers.update(extra_headers)
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with build_opener(_RejectRedirects()).open(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                return cast(bytes, response.read())
        except HTTPError as error:
            raise StorageOperationError(
                f"Storage request failed with HTTP status {error.code}.",
                status_code=error.code,
            ) from None
        except (OSError, TimeoutError, URLError):
            raise StorageOperationError("Storage service is unavailable.") from None

    def _authentication_headers(self) -> dict[str, str]:
        headers = {
            "apikey": self._secret_key,
            "User-Agent": "vgu-buddy-api/0.1",
        }
        if self._secret_key.startswith("eyJ") and self._secret_key.count(".") == 2:
            headers["Authorization"] = f"Bearer {self._secret_key}"
        return headers

    async def _request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        return await asyncio.to_thread(
            self._request_sync,
            method,
            url,
            body=body,
            content_type=content_type,
            extra_headers=extra_headers,
        )

    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None:
        await self._request(
            "POST",
            self._url("object", reference.bucket.value, reference.object_key),
            body=content,
            content_type=content_type,
            extra_headers={"x-upsert": "false", "cache-control": "3600"},
        )

    async def configure_bucket(self, bucket: ImageBucket) -> None:
        """Create or converge one trusted bucket through the Storage API."""
        if not isinstance(bucket, ImageBucket):
            raise StorageOperationError("Storage bucket must be selected by trusted server code.")

        request_body = json.dumps(
            {
                "id": bucket.value,
                "name": bucket.value,
                "public": bucket.is_public,
                "file_size_limit": MAX_IMAGE_BYTES,
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
            },
            separators=(",", ":"),
        ).encode("utf-8")
        bucket_url = self._url("bucket", bucket.value)
        try:
            await self._request("GET", bucket_url)
        except StorageOperationError as error:
            if error.status_code != 404:
                raise
            try:
                await self._request(
                    "POST",
                    self._url("bucket"),
                    body=request_body,
                    content_type="application/json",
                )
                return
            except StorageOperationError as create_error:
                if create_error.status_code != 409:
                    raise

        await self._request(
            "PUT",
            bucket_url,
            body=request_body,
            content_type="application/json",
        )

    async def delete(self, reference: StorageObjectRef) -> None:
        await self._request(
            "DELETE",
            self._url("object", reference.bucket.value, reference.object_key),
        )

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]:
        request_body = json.dumps(
            {
                "prefix": "",
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._request(
            "POST",
            self._url("object/list", bucket.value),
            body=request_body,
            content_type="application/json",
        )
        try:
            payload = json.loads(response)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StorageOperationError("Storage service returned an invalid response.") from error
        if not isinstance(payload, list):
            raise StorageOperationError("Storage service returned an invalid response.")

        objects: list[ListedStorageObject] = []
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise StorageOperationError("Storage service returned an invalid response.")
            objects.append(
                ListedStorageObject(
                    object_key=item["name"],
                    created_at=_parse_storage_timestamp(item.get("created_at")),
                )
            )
        return tuple(objects)

    async def create_signed_url(
        self,
        reference: StorageObjectRef,
        expires_in: int,
    ) -> str:
        response = await self._request(
            "POST",
            self._url("object/sign", reference.bucket.value, reference.object_key),
            body=json.dumps({"expiresIn": expires_in}, separators=(",", ":")).encode("utf-8"),
            content_type="application/json",
        )
        try:
            payload = json.loads(response)
            signed_path = payload.get("signedURL", payload.get("signedUrl"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StorageOperationError("Storage service returned an invalid response.") from error
        if not isinstance(signed_path, str) or not signed_path:
            raise StorageOperationError("Storage service returned an invalid response.")

        if urlsplit(signed_path).scheme:
            signed_url = signed_path
        elif signed_path.startswith("/storage/v1/"):
            signed_url = urljoin(f"{self._base_url}/", signed_path.lstrip("/"))
        else:
            signed_url = f"{self._base_url}/storage/v1/{signed_path.lstrip('/')}"
        expected = urlsplit(self._base_url)
        actual = urlsplit(signed_url)
        if (
            actual.scheme != expected.scheme
            or actual.hostname != expected.hostname
            or actual.port != expected.port
            or actual.username is not None
            or actual.password is not None
            or not actual.path.startswith("/storage/v1/object/sign/")
            or ".." in actual.path.split("/")
        ):
            raise StorageOperationError("Storage service returned an invalid signed URL.")
        return signed_url

    def public_url(self, reference: StorageObjectRef) -> str:
        return self._url("object/public", reference.bucket.value, reference.object_key)


class ImageStorageService:
    """Process images and restrict all object operations to trusted bucket enums and UUID keys."""

    def __init__(self, transport: StorageTransport) -> None:
        self._transport = transport

    async def upload_image(
        self,
        bucket: ImageBucket,
        *,
        original_name: str,
        declared_content_type: str,
        content: bytes,
    ) -> StoredImage:
        if not isinstance(bucket, ImageBucket):
            raise ImageValidationError("Storage bucket must be selected by trusted server code.")
        prepared = prepare_image(
            original_name=original_name,
            declared_content_type=declared_content_type,
            content=content,
        )
        reference = StorageObjectRef(
            bucket=bucket,
            object_key=f"{uuid4()}.{prepared.extension}",
        )
        await self._transport.upload(
            reference,
            prepared.content,
            prepared.mime_type,
        )
        return StoredImage(
            reference=reference,
            mime_type=prepared.mime_type,
            byte_size=prepared.byte_size,
            width=prepared.width,
            height=prepared.height,
        )

    async def delete_image(self, reference: StorageObjectRef) -> None:
        await self._transport.delete(reference)

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]:
        return await self._transport.list_objects(bucket, limit=limit, offset=offset)

    async def create_signed_url(
        self,
        reference: StorageObjectRef,
        *,
        expires_in: int,
    ) -> str:
        if reference.bucket.is_public:
            raise StorageOperationError("Public promotional images do not use signed URLs.")
        if not 1 <= expires_in <= MAX_SIGNED_URL_SECONDS:
            raise StorageOperationError(
                "Private image URL lifetime must be between 1 and 300 seconds."
            )
        return await self._transport.create_signed_url(reference, expires_in)

    def public_url(self, reference: StorageObjectRef) -> str:
        if not reference.bucket.is_public:
            raise StorageOperationError("Private images do not have public URLs.")
        return self._transport.public_url(reference)


def prepare_image(
    *,
    original_name: str,
    declared_content_type: str,
    content: bytes,
) -> PreparedImage:
    """Verify, fully decode and metadata-free re-encode one supported image."""
    if not content:
        raise ImageValidationError("Image file is empty.")
    if len(content) > MAX_IMAGE_BYTES:
        raise ImageValidationError("Image file exceeds the 5 MiB limit.")

    extension = _validate_file_name(original_name)
    mime_type = declared_content_type.strip().casefold()
    expected_format = {
        "jpg": ("JPEG", "image/jpeg"),
        "png": ("PNG", "image/png"),
        "webp": ("WEBP", "image/webp"),
    }[extension]
    if mime_type != expected_format[1]:
        raise ImageValidationError("Image MIME type does not match its extension.")
    if _signature_format(content) != expected_format[0]:
        raise ImageValidationError("Image signature does not match its extension.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format != expected_format[0]:
                    raise ImageValidationError("Decoded image format does not match its signature.")
                if getattr(source, "is_animated", False) or getattr(source, "n_frames", 1) != 1:
                    raise ImageValidationError("Animated images are not accepted.")
                width, height = source.size
                _validate_dimensions(width, height)
                source.verify()

            with Image.open(BytesIO(content)) as decoded:
                decoded.load()
                normalized = ImageOps.exif_transpose(decoded)
                width, height = normalized.size
                _validate_dimensions(width, height)
                prepared_content = _encode_without_metadata(normalized, expected_format[0])
    except ImageValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageValidationError("Image exceeds the decoded-pixel limit.") from None
    except (OSError, SyntaxError, UnidentifiedImageError, ValueError):
        raise ImageValidationError("Image could not be decoded safely.") from None

    if len(prepared_content) > MAX_IMAGE_BYTES:
        raise ImageValidationError("Processed image exceeds the 5 MiB limit.")
    return PreparedImage(
        content=prepared_content,
        mime_type=expected_format[1],
        extension=extension,
        byte_size=len(prepared_content),
        width=width,
        height=height,
    )


def _validate_file_name(original_name: str) -> str:
    if (
        not original_name
        or original_name != original_name.strip()
        or "/" in original_name
        or "\\" in original_name
        or "\x00" in original_name
    ):
        raise ImageValidationError("Image filename must not contain a path or URL.")
    parsed = urlsplit(original_name)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ImageValidationError("External image URLs are not accepted.")
    suffix = Path(original_name).suffix.casefold()
    if suffix == ".jpeg":
        return "jpg"
    if suffix in {".jpg", ".png", ".webp"}:
        return suffix[1:]
    raise ImageValidationError("Image extension must be JPEG, PNG, or WebP.")


def _signature_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "WEBP"
    return None


def _validate_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ImageValidationError("Image dimensions must be positive.")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ImageValidationError("Image dimensions exceed 4096x4096.")
    if width * height > MAX_DECODED_PIXELS:
        raise ImageValidationError("Image exceeds the decoded-pixel limit.")


def _encode_without_metadata(image: Image.Image, image_format: str) -> bytes:
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    target_mode = "RGBA" if has_alpha and image_format != "JPEG" else "RGB"
    converted = image.convert(target_mode)
    clean = Image.new(target_mode, converted.size)
    clean.paste(converted)

    options: dict[str, object]
    if image_format == "JPEG":
        options = {"quality": 90, "optimize": True, "progressive": True}
    elif image_format == "PNG":
        options = {"optimize": True}
    else:
        options = {"quality": 90, "method": 6}

    output = BytesIO()
    clean.save(output, format=image_format, **options)
    return output.getvalue()


def _parse_storage_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


async def replace_image_reference(
    session: AsyncSession,
    storage: ImageStorageService,
    *,
    bucket: ImageBucket,
    original_name: str,
    declared_content_type: str,
    content: bytes,
    attach: Callable[[StoredImage], Awaitable[None]],
    previous: StorageObjectRef | None,
    is_referenced: Callable[[StorageObjectRef], Awaitable[bool]],
) -> ImageReplacement:
    """Upload new, commit its DB reference, then clean the unreferenced previous object."""
    image = await storage.upload_image(
        bucket,
        original_name=original_name,
        declared_content_type=declared_content_type,
        content=content,
    )
    try:
        await attach(image)
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        finally:
            try:
                await storage.delete_image(image.reference)
            except StorageOperationError:
                pass  # Reconciliation will find this unreferenced UUID object.
        raise

    cleanup_pending = False
    if previous is not None:
        try:
            if not await is_referenced(previous):
                await storage.delete_image(previous)
        except Exception:
            cleanup_pending = True
    return ImageReplacement(image=image, cleanup_pending=cleanup_pending)


async def discover_storage_references(
    session: AsyncSession,
) -> tuple[frozenset[StorageObjectRef], int]:
    """Read every app-private table that follows the shared bucket/object_key contract."""
    result = await session.execute(
        text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND column_name IN ('bucket', 'object_key') "
            "GROUP BY table_name HAVING COUNT(DISTINCT column_name) = 2 "
            "ORDER BY table_name"
        ),
        {"schema": APPLICATION_SCHEMA},
    )
    table_names = tuple(row[0] for row in result if isinstance(row[0], str))
    references: set[StorageObjectRef] = set()
    for table_name in table_names:
        if _SAFE_TABLE_NAME.fullmatch(table_name) is None:
            raise StorageReconciliationError("Storage reference table name is unsafe.")
        reference_table = table(
            table_name,
            column("bucket"),
            column("object_key"),
            schema=APPLICATION_SCHEMA,
        )
        rows = await session.execute(select(reference_table.c.bucket, reference_table.c.object_key))
        for bucket_value, object_key in rows:
            if not isinstance(bucket_value, str) or not isinstance(object_key, str):
                continue
            try:
                references.add(
                    StorageObjectRef(
                        bucket=ImageBucket(bucket_value),
                        object_key=object_key,
                    )
                )
            except (ValueError, ImageValidationError):
                continue
    return frozenset(references), len(table_names)


async def reconcile_orphaned_images(
    storage: ImageStorageService,
    referenced: Collection[StorageObjectRef],
    *,
    older_than: datetime,
    apply: bool,
) -> ReconciliationReport:
    """List managed UUID objects and optionally remove only old, unreferenced objects."""
    if older_than.tzinfo is None:
        raise StorageReconciliationError("Reconciliation cutoff must be timezone-aware.")
    protected_refs = frozenset(referenced)
    scanned = protected = too_new = unmanaged = candidates = deleted = failed = 0

    for bucket in ImageBucket:
        listed_objects: list[ListedStorageObject] = []
        offset = 0
        while True:
            page = await storage.list_objects(
                bucket,
                limit=STORAGE_PAGE_SIZE,
                offset=offset,
            )
            scanned += len(page)
            listed_objects.extend(page)
            if len(page) < STORAGE_PAGE_SIZE:
                break
            offset += len(page)

        for item in listed_objects:
            try:
                reference = StorageObjectRef(bucket=bucket, object_key=item.object_key)
            except ImageValidationError:
                unmanaged += 1
                continue
            if reference in protected_refs:
                protected += 1
                continue
            if item.created_at is None or item.created_at >= older_than:
                too_new += 1
                continue
            candidates += 1
            if apply:
                try:
                    await storage.delete_image(reference)
                    deleted += 1
                except StorageOperationError:
                    failed += 1

    return ReconciliationReport(
        scanned=scanned,
        protected=protected,
        too_new=too_new,
        unmanaged=unmanaged,
        candidates=candidates,
        deleted=deleted,
        failed=failed,
    )
