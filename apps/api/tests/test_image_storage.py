"""Image validation, Storage boundary and failure-safe lifecycle tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from PIL import Image, PngImagePlugin
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.image_storage as image_storage
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ImageValidationError,
    ListedStorageObject,
    StorageObjectRef,
    StorageOperationError,
    StorageReconciliationError,
    discover_storage_references,
    prepare_image,
    reconcile_orphaned_images,
    replace_image_reference,
)


def _image_bytes(
    image_format: str = "PNG",
    *,
    size: tuple[int, int] = (12, 8),
    animated: bool = False,
) -> bytes:
    first = Image.new("RGBA", size, (10, 20, 30, 180))
    output = BytesIO()
    options: dict[str, object] = {}
    if image_format == "JPEG":
        first = first.convert("RGB")
        exif = Image.Exif()
        exif[0x010E] = "private metadata"
        options["exif"] = exif
    elif image_format == "PNG":
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "private metadata")
        options["pnginfo"] = metadata
    elif image_format == "WEBP":
        exif = Image.Exif()
        exif[0x010E] = "private metadata"
        options["exif"] = exif
    if animated:
        second = Image.new("RGBA", size, (50, 60, 70, 255))
        options.update({"save_all": True, "append_images": [second], "duration": 100, "loop": 0})
    first.save(output, format=image_format, **options)
    return output.getvalue()


class FakeTransport:
    def __init__(self) -> None:
        self.uploads: list[tuple[StorageObjectRef, bytes, str]] = []
        self.deletes: list[StorageObjectRef] = []
        self.listed: dict[ImageBucket, tuple[ListedStorageObject, ...]] = {
            bucket: () for bucket in ImageBucket
        }
        self.upload_error: Exception | None = None
        self.delete_errors: set[StorageObjectRef] = set()

    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None:
        if self.upload_error is not None:
            raise self.upload_error
        self.uploads.append((reference, content, content_type))

    async def delete(self, reference: StorageObjectRef) -> None:
        self.deletes.append(reference)
        if reference in self.delete_errors:
            raise StorageOperationError("test storage failure")

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]:
        return self.listed[bucket][offset : offset + limit]

    async def create_signed_url(
        self,
        reference: StorageObjectRef,
        expires_in: int,
    ) -> str:
        return f"https://project.supabase.co/signed/{reference.object_key}?ttl={expires_in}"

    def public_url(self, reference: StorageObjectRef) -> str:
        return f"https://project.supabase.co/public/{reference.object_key}"


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.execute = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    ("image_format", "file_name", "mime_type", "expected_extension"),
    [
        ("JPEG", "photo.jpeg", "image/jpeg", "jpg"),
        ("PNG", "photo.png", "image/png", "png"),
        ("WEBP", "photo.webp", "image/webp", "webp"),
    ],
)
def test_prepare_image_decodes_reencodes_and_strips_metadata(
    image_format: str,
    file_name: str,
    mime_type: str,
    expected_extension: str,
) -> None:
    prepared = prepare_image(
        original_name=file_name,
        declared_content_type=mime_type,
        content=_image_bytes(image_format),
    )

    assert prepared.extension == expected_extension
    assert prepared.mime_type == mime_type
    assert prepared.byte_size == len(prepared.content)
    assert (prepared.width, prepared.height) == (12, 8)
    with Image.open(BytesIO(prepared.content)) as decoded:
        decoded.load()
        assert decoded.format == image_format
        assert not decoded.getexif()
        assert "Comment" not in decoded.info
        assert "exif" not in decoded.info
        assert "icc_profile" not in decoded.info


@pytest.mark.parametrize(
    ("file_name", "mime_type", "content", "message"),
    [
        ("photo.png", "image/jpeg", _image_bytes("PNG"), "MIME type"),
        ("photo.jpg", "image/jpeg", _image_bytes("PNG"), "signature"),
        ("photo.svg", "image/svg+xml", b"<svg></svg>", "extension"),
        ("https://example.test/photo.png", "image/png", _image_bytes(), "path or URL"),
        ("folder/photo.png", "image/png", _image_bytes(), "path or URL"),
    ],
)
def test_prepare_image_rejects_mismatches_svg_urls_and_paths(
    file_name: str,
    mime_type: str,
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(ImageValidationError, match=message):
        prepare_image(
            original_name=file_name,
            declared_content_type=mime_type,
            content=content,
        )


def test_prepare_image_rejects_animated_supported_format() -> None:
    with pytest.raises(ImageValidationError, match="Animated images"):
        prepare_image(
            original_name="animation.webp",
            declared_content_type="image/webp",
            content=_image_bytes("WEBP", animated=True),
        )


def test_prepare_image_enforces_encoded_dimension_and_decoded_pixel_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ImageValidationError, match="5 MiB"):
        prepare_image(
            original_name="photo.png",
            declared_content_type="image/png",
            content=b"x" * (image_storage.MAX_IMAGE_BYTES + 1),
        )

    too_wide = _image_bytes("PNG", size=(image_storage.MAX_IMAGE_DIMENSION + 1, 1))
    with pytest.raises(ImageValidationError, match="4096x4096"):
        prepare_image(
            original_name="photo.png",
            declared_content_type="image/png",
            content=too_wide,
        )

    monkeypatch.setattr(image_storage, "MAX_DECODED_PIXELS", 50)
    with pytest.raises(ImageValidationError, match="decoded-pixel"):
        prepare_image(
            original_name="photo.png",
            declared_content_type="image/png",
            content=_image_bytes("PNG", size=(10, 10)),
        )


@pytest.mark.anyio
async def test_upload_uses_server_generated_uuid_key_and_processed_bytes() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)

    stored = await storage.upload_image(
        ImageBucket.PROFILE_IMAGES,
        original_name="avatar.png",
        declared_content_type="image/png",
        content=_image_bytes(),
    )

    key_stem, extension = stored.reference.object_key.rsplit(".", maxsplit=1)
    assert stored.reference.bucket is ImageBucket.PROFILE_IMAGES
    assert str(UUID(key_stem, version=4)) == key_stem
    assert extension == "png"
    assert transport.uploads == [(stored.reference, transport.uploads[0][1], "image/png")]
    assert transport.uploads[0][1] != _image_bytes()


@pytest.mark.anyio
async def test_upload_rejects_arbitrary_client_bucket_before_transport() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)

    with pytest.raises(ImageValidationError, match="trusted server code"):
        await storage.upload_image(
            cast(ImageBucket, "client-chosen-bucket"),
            original_name="avatar.png",
            declared_content_type="image/png",
            content=_image_bytes(),
        )

    assert transport.uploads == []


@pytest.mark.anyio
async def test_private_urls_are_short_lived_and_public_urls_are_bucket_scoped() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    private = StorageObjectRef(
        ImageBucket.EVENT_MEDIA,
        "00000000-0000-4000-8000-000000000001.jpg",
    )
    public = StorageObjectRef(
        ImageBucket.EVENT_SLIDER_IMAGES,
        "00000000-0000-4000-8000-000000000002.jpg",
    )

    assert "ttl=300" in await storage.create_signed_url(private, expires_in=300)
    assert storage.public_url(public).startswith("https://project.supabase.co/public/")
    with pytest.raises(StorageOperationError, match="between 1 and 300"):
        await storage.create_signed_url(private, expires_in=301)
    with pytest.raises(StorageOperationError, match="do not use signed"):
        await storage.create_signed_url(public, expires_in=60)
    with pytest.raises(StorageOperationError, match="do not have public"):
        storage.public_url(private)


@pytest.mark.anyio
async def test_storage_failure_never_runs_database_attachment_or_changes_old_reference() -> None:
    transport = FakeTransport()
    transport.upload_error = StorageOperationError("upload failed")
    storage = ImageStorageService(transport)
    mock, session = _session()
    attach = AsyncMock()
    old = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "00000000-0000-4000-8000-000000000003.jpg",
    )

    with pytest.raises(StorageOperationError, match="upload failed"):
        await replace_image_reference(
            session,
            storage,
            bucket=ImageBucket.PROFILE_IMAGES,
            original_name="avatar.png",
            declared_content_type="image/png",
            content=_image_bytes(),
            attach=attach,
            previous=old,
            is_referenced=AsyncMock(return_value=False),
        )

    attach.assert_not_awaited()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()
    assert transport.deletes == []


@pytest.mark.anyio
async def test_failed_database_attachment_rolls_back_and_cleans_new_object() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    mock, session = _session()
    attach_error = RuntimeError("attachment failed")
    attach = AsyncMock(side_effect=attach_error)

    with pytest.raises(RuntimeError) as raised:
        await replace_image_reference(
            session,
            storage,
            bucket=ImageBucket.EVENT_MEDIA,
            original_name="cover.jpg",
            declared_content_type="image/jpeg",
            content=_image_bytes("JPEG"),
            attach=attach,
            previous=None,
            is_referenced=AsyncMock(return_value=False),
        )

    assert raised.value is attach_error
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    assert transport.deletes == [transport.uploads[0][0]]


@pytest.mark.anyio
async def test_failed_database_commit_rolls_back_and_cleanup_does_not_mask_failure() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    mock, session = _session()
    commit_error = RuntimeError("commit failed")
    mock.commit.side_effect = commit_error

    async def fail_compensation(reference: StorageObjectRef) -> None:
        transport.deletes.append(reference)
        raise StorageOperationError("compensating delete failed")

    transport.delete = fail_compensation  # type: ignore[method-assign]

    with pytest.raises(RuntimeError) as raised:
        await replace_image_reference(
            session,
            storage,
            bucket=ImageBucket.PROFILE_IMAGES,
            original_name="avatar.png",
            declared_content_type="image/png",
            content=_image_bytes(),
            attach=AsyncMock(),
            previous=None,
            is_referenced=AsyncMock(return_value=False),
        )

    assert raised.value is commit_error
    mock.rollback.assert_awaited_once_with()
    assert transport.deletes == [transport.uploads[0][0]]


@pytest.mark.anyio
async def test_rollback_failure_still_attempts_new_object_cleanup() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    mock, session = _session()
    mock.rollback.side_effect = RuntimeError("rollback failed")

    with pytest.raises(RuntimeError, match="rollback failed"):
        await replace_image_reference(
            session,
            storage,
            bucket=ImageBucket.EVENT_MEDIA,
            original_name="cover.png",
            declared_content_type="image/png",
            content=_image_bytes(),
            attach=AsyncMock(side_effect=RuntimeError("attachment failed")),
            previous=None,
            is_referenced=AsyncMock(return_value=False),
        )

    assert transport.deletes == [transport.uploads[0][0]]


@pytest.mark.anyio
async def test_post_commit_cleanup_protects_referenced_old_object() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    mock, session = _session()
    old = StorageObjectRef(
        ImageBucket.EVENT_MEDIA,
        "00000000-0000-4000-8000-000000000004.webp",
    )
    reference_check = AsyncMock(return_value=True)

    replacement = await replace_image_reference(
        session,
        storage,
        bucket=ImageBucket.EVENT_MEDIA,
        original_name="cover.webp",
        declared_content_type="image/webp",
        content=_image_bytes("WEBP"),
        attach=AsyncMock(),
        previous=old,
        is_referenced=reference_check,
    )

    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()
    reference_check.assert_awaited_once_with(old)
    assert transport.deletes == []
    assert replacement.cleanup_pending is False


@pytest.mark.anyio
async def test_post_commit_cleanup_failure_is_retryable() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    _, session = _session()
    old = StorageObjectRef(
        ImageBucket.EVENT_MEDIA,
        "00000000-0000-4000-8000-000000000005.png",
    )
    transport.delete_errors.add(old)

    replacement = await replace_image_reference(
        session,
        storage,
        bucket=ImageBucket.EVENT_MEDIA,
        original_name="cover.png",
        declared_content_type="image/png",
        content=_image_bytes(),
        attach=AsyncMock(),
        previous=old,
        is_referenced=AsyncMock(return_value=False),
    )

    assert transport.deletes == [old]
    assert replacement.cleanup_pending is True


@pytest.mark.anyio
async def test_reconciliation_protects_references_new_and_unmanaged_objects() -> None:
    transport = FakeTransport()
    storage = ImageStorageService(transport)
    now = datetime.now(UTC)
    protected = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "00000000-0000-4000-8000-000000000006.jpg",
    )
    orphan = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "00000000-0000-4000-8000-000000000007.jpg",
    )
    recent = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "00000000-0000-4000-8000-000000000008.jpg",
    )
    transport.listed[ImageBucket.PROFILE_IMAGES] = (
        ListedStorageObject(protected.object_key, now - timedelta(days=2)),
        ListedStorageObject(orphan.object_key, now - timedelta(days=2)),
        ListedStorageObject(recent.object_key, now),
        ListedStorageObject("legacy/banner.jpg", now - timedelta(days=2)),
    )

    report = await reconcile_orphaned_images(
        storage,
        {protected},
        older_than=now - timedelta(hours=24),
        apply=True,
    )

    assert transport.deletes == [orphan]
    assert report.scanned == 4
    assert report.protected == 1
    assert report.too_new == 1
    assert report.unmanaged == 1
    assert report.candidates == 1
    assert report.deleted == 1
    assert report.failed == 0


@pytest.mark.anyio
async def test_reconciliation_lists_complete_bucket_before_deleting() -> None:
    class MutatingTransport(FakeTransport):
        async def delete(self, reference: StorageObjectRef) -> None:
            await super().delete(reference)
            self.listed[reference.bucket] = tuple(
                item
                for item in self.listed[reference.bucket]
                if item.object_key != reference.object_key
            )

    transport = MutatingTransport()
    storage = ImageStorageService(transport)
    old = datetime.now(UTC) - timedelta(days=2)
    objects = tuple(
        ListedStorageObject(f"{UUID(int=index, version=4)}.png", old) for index in range(1, 102)
    )
    transport.listed[ImageBucket.EVENT_MEDIA] = objects

    report = await reconcile_orphaned_images(
        storage,
        set(),
        older_than=datetime.now(UTC) - timedelta(hours=24),
        apply=True,
    )

    assert report.scanned == 101
    assert report.candidates == 101
    assert report.deleted == 101
    assert len(transport.deletes) == 101


@pytest.mark.anyio
async def test_reconciliation_requires_timezone_aware_cutoff() -> None:
    with pytest.raises(StorageReconciliationError, match="timezone-aware"):
        await reconcile_orphaned_images(
            ImageStorageService(FakeTransport()),
            set(),
            older_than=datetime.now(),
            apply=False,
        )


@pytest.mark.anyio
async def test_reference_discovery_reads_only_bucket_object_key_tables() -> None:
    mock, session = _session()
    mock.execute.side_effect = [
        [("event_media",), ("profile_photos",)],
        [("event-media", "00000000-0000-4000-8000-000000000009.jpg")],
        [("profile-images", "00000000-0000-4000-8000-000000000010.png")],
    ]

    references, source_count = await discover_storage_references(session)

    assert source_count == 2
    assert references == {
        StorageObjectRef(
            ImageBucket.EVENT_MEDIA,
            "00000000-0000-4000-8000-000000000009.jpg",
        ),
        StorageObjectRef(
            ImageBucket.PROFILE_IMAGES,
            "00000000-0000-4000-8000-000000000010.png",
        ),
    }
    assert mock.execute.await_count == 3


@pytest.mark.anyio
async def test_reference_discovery_rejects_unsafe_discovered_identifier() -> None:
    mock, session = _session()
    mock.execute.return_value = [("unsafe;drop",)]

    with pytest.raises(StorageReconciliationError, match="unsafe"):
        await discover_storage_references(session)
