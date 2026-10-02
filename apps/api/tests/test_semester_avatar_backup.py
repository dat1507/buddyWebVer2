"""Focused SEM-003 avatar manifest, integrity, scope, and restore tests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from PIL import Image

from app.services.database_backup_storage import BackupStorageObjectRef
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ListedStorageObject,
    StorageObjectRef,
    StorageOperationError,
    prepare_image,
)
from app.services.semester_avatar_backup import (
    AvatarBackupAdapter,
    AvatarBackupError,
    AvatarBackupPackage,
    AvatarBackupValidationError,
    restore_avatar_backup_for_rehearsal,
    restore_avatar_backup_idempotently,
    store_avatar_backup_package,
    validate_avatar_backup_manifest,
    validate_avatar_backup_package,
)
from app.services.semester_database_backup import DatabaseBackupAvatarReference

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
BACKUP_ID = UUID("40000000-0000-4000-8000-000000000001")
SEMESTER_ID = UUID("50000000-0000-4000-8000-000000000001")


def _png(color: tuple[int, int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGBA", (12, 8), color).save(output, format="PNG")
    return prepare_image(
        original_name="avatar.png",
        declared_content_type="image/png",
        content=output.getvalue(),
    ).content


class _MemoryTransport:
    def __init__(self) -> None:
        self.objects: dict[StorageObjectRef, tuple[bytes, str]] = {}
        self.upload_order: list[StorageObjectRef] = []
        self.deleted: list[StorageObjectRef] = []
        self.fail_on_upload: StorageObjectRef | None = None

    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None:
        if reference == self.fail_on_upload:
            raise StorageOperationError("injected storage failure")
        if reference in self.objects:
            raise StorageOperationError("object collision", status_code=409)
        self.objects[reference] = (content, content_type)
        self.upload_order.append(reference)

    async def download(self, reference: StorageObjectRef) -> bytes:
        try:
            return self.objects[reference][0]
        except KeyError:
            raise StorageOperationError("object missing", status_code=404) from None

    async def delete(self, reference: StorageObjectRef) -> None:
        self.deleted.append(reference)
        self.objects.pop(reference, None)

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]:
        del bucket, limit, offset
        return ()

    async def create_signed_url(self, reference: StorageObjectRef, expires_in: int) -> str:
        raise AssertionError((reference, expires_in))

    def public_url(self, reference: StorageObjectRef) -> str:
        raise AssertionError(reference)


class _FailManifestArtifactStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def location(self, reference: BackupStorageObjectRef) -> str:
        return f"private-test://{reference.object_key}"

    async def put_file(self, reference: BackupStorageObjectRef, source: Path) -> None:
        if reference.content_type == "application/json":
            raise OSError("injected private provider detail")
        self.objects[reference.object_key] = source.read_bytes()

    async def get_file(self, reference: BackupStorageObjectRef, target: Path) -> None:
        target.write_bytes(self.objects[reference.object_key])

    async def delete(self, reference: BackupStorageObjectRef) -> None:
        self.objects.pop(reference.object_key, None)


def _reference(index: int, content: bytes) -> DatabaseBackupAvatarReference:
    photo_id = UUID(f"00000000-0000-4000-8000-{index:012d}")
    profile_id = UUID(f"10000000-0000-4000-8000-{index:012d}")
    owner_id = UUID(f"20000000-0000-4000-8000-{index:012d}")
    object_id = UUID(f"30000000-0000-4000-8000-{index:012d}")
    return DatabaseBackupAvatarReference(
        photo_id=photo_id,
        profile_id=profile_id,
        owner_user_id=owner_id,
        bucket="profile-images",
        object_key=f"{object_id}.png",
        mime_type="image/png",
        byte_size=len(content),
        width=12,
        height=8,
    )


async def _package(
    tmp_path: Path,
    references: tuple[DatabaseBackupAvatarReference, ...],
    contents: tuple[bytes, ...],
) -> tuple[AvatarBackupPackage, _MemoryTransport, StorageObjectRef]:
    transport = _MemoryTransport()
    for reference, content in zip(references, contents, strict=True):
        transport.objects[StorageObjectRef(ImageBucket.PROFILE_IMAGES, reference.object_key)] = (
            content,
            reference.mime_type,
        )
    orphan = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "ffffffff-ffff-4fff-8fff-ffffffffffff.png",
    )
    transport.objects[orphan] = (_png((1, 2, 3, 255)), "image/png")
    package = await AvatarBackupAdapter(ImageStorageService(transport)).export(
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        source_boundary_at=NOW,
        created_at=NOW,
        database_manifest_checksum="a" * 64,
        references=references,
        workspace=tmp_path,
    )
    return package, transport, orphan


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_backup_is_deterministic_scoped_and_restores_exact_owner_mapping(
    tmp_path: Path,
) -> None:
    contents = (_png((10, 20, 30, 255)), _png((30, 20, 10, 255)))
    references = tuple(_reference(index, content) for index, content in enumerate(contents, 1))
    package, source, orphan = await _package(tmp_path / "first", references, contents)
    second, _, _ = await _package(tmp_path / "second", references, contents)

    assert package.manifest.object_count == 2
    assert package.manifest.total_bytes == sum(map(len, contents))
    assert tuple(item.photo_id for item in package.manifest.objects) == tuple(
        reference.photo_id for reference in references
    )
    assert tuple(item.owner_user_id for item in package.manifest.objects) == tuple(
        reference.owner_user_id for reference in references
    )
    assert orphan not in {
        StorageObjectRef(ImageBucket.PROFILE_IMAGES, item.source_object_key)
        for item in package.manifest.objects
    }
    assert package.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert source.upload_order == []

    target = _MemoryTransport()
    restored = await restore_avatar_backup_for_rehearsal(
        ImageStorageService(target),
        manifest_content=package.manifest_path.read_bytes(),
        object_paths={reference.object_key: path for reference, path in package.object_files},
        expected_manifest_checksum=package.manifest_checksum,
    )
    assert restored == package.manifest
    for reference, content in zip(references, contents, strict=True):
        assert target.objects[
            StorageObjectRef(ImageBucket.PROFILE_IMAGES, reference.object_key)
        ] == (content, reference.mime_type)


@pytest.mark.anyio
async def test_no_avatar_snapshot_produces_valid_empty_manifest(tmp_path: Path) -> None:
    package, _, _ = await _package(tmp_path, (), ())

    assert package.manifest.object_count == 0
    assert package.manifest.total_bytes == 0
    assert package.object_files == ()
    assert (
        validate_avatar_backup_package(
            package.manifest_path.read_bytes(),
            {},
            expected_backup_id=package.manifest.backup_id,
            expected_manifest_checksum=package.manifest_checksum,
        )
        == package.manifest
    )


@pytest.mark.anyio
async def test_restore_retry_accepts_only_byte_identical_existing_objects(tmp_path: Path) -> None:
    content = _png((10, 20, 30, 255))
    reference = _reference(1, content)
    package, _, _ = await _package(tmp_path / "package", (reference,), (content,))
    object_paths = {item.object_key: path for item, path in package.object_files}
    target = _MemoryTransport()
    key = StorageObjectRef(ImageBucket.PROFILE_IMAGES, reference.object_key)
    target.objects[key] = (content, reference.mime_type)

    retry = await restore_avatar_backup_idempotently(
        ImageStorageService(target),
        manifest_content=package.manifest_path.read_bytes(),
        object_paths=object_paths,
        expected_manifest_checksum=package.manifest_checksum,
    )

    assert retry.already_present == 1
    assert retry.newly_restored == ()
    assert target.deleted == []

    target.objects[key] = (_png((99, 88, 77, 255)), reference.mime_type)
    with pytest.raises(AvatarBackupError, match="collision"):
        await restore_avatar_backup_idempotently(
            ImageStorageService(target),
            manifest_content=package.manifest_path.read_bytes(),
            object_paths=object_paths,
            expected_manifest_checksum=package.manifest_checksum,
        )
    assert target.deleted == []


@pytest.mark.anyio
async def test_missing_or_metadata_inconsistent_source_object_fails_closed(
    tmp_path: Path,
) -> None:
    content = _png((10, 20, 30, 255))
    reference = _reference(1, content)
    adapter = AvatarBackupAdapter(ImageStorageService(_MemoryTransport()))

    with pytest.raises(AvatarBackupError, match="unavailable or invalid"):
        await adapter.export(
            backup_id=uuid4(),
            source_semester_id=uuid4(),
            source_boundary_at=NOW,
            created_at=NOW,
            database_manifest_checksum="a" * 64,
            references=(reference,),
            workspace=tmp_path / "missing",
        )

    wrong_size = reference.model_copy(update={"byte_size": len(content) - 1})
    transport = _MemoryTransport()
    transport.objects[StorageObjectRef(ImageBucket.PROFILE_IMAGES, reference.object_key)] = (
        content,
        reference.mime_type,
    )
    with pytest.raises(AvatarBackupError, match="unavailable or invalid"):
        await AvatarBackupAdapter(ImageStorageService(transport)).export(
            backup_id=uuid4(),
            source_semester_id=uuid4(),
            source_boundary_at=NOW,
            created_at=NOW,
            database_manifest_checksum="a" * 64,
            references=(wrong_size,),
            workspace=tmp_path / "inconsistent",
        )


@pytest.mark.anyio
async def test_tampered_truncated_or_extra_object_fails_integrity(tmp_path: Path) -> None:
    content = _png((10, 20, 30, 255))
    package, _, _ = await _package(tmp_path, (_reference(1, content),), (content,))
    mapping = {reference.object_key: path for reference, path in package.object_files}
    key, path = next(iter(mapping.items()))
    original = path.read_bytes()

    for damaged in (original[:-1], original[:-1] + b"X"):
        path.write_bytes(damaged)
        with pytest.raises(AvatarBackupValidationError):
            validate_avatar_backup_package(package.manifest_path.read_bytes(), mapping)
    path.write_bytes(original)
    with pytest.raises(AvatarBackupValidationError, match="membership"):
        validate_avatar_backup_package(
            package.manifest_path.read_bytes(),
            {**mapping, "unexpected": path},
        )
    assert hashlib.sha256(original).hexdigest() == package.manifest.objects[0].sha256
    assert key == package.manifest.objects[0].backup_object_key


@pytest.mark.anyio
async def test_manifest_rejects_path_traversal_duplicates_and_wrong_checksum(
    tmp_path: Path,
) -> None:
    content = _png((10, 20, 30, 255))
    package, _, _ = await _package(tmp_path, (_reference(1, content),), (content,))
    payload = json.loads(package.manifest_path.read_bytes())

    payload["objects"][0]["backup_object_key"] = "../../escape.png"
    malformed = json.dumps(payload).encode()
    with pytest.raises(AvatarBackupValidationError):
        validate_avatar_backup_manifest(malformed)

    payload = json.loads(package.manifest_path.read_bytes())
    payload["objects"].append(payload["objects"][0])
    payload["object_count"] = 2
    payload["total_bytes"] *= 2
    with pytest.raises(AvatarBackupValidationError):
        validate_avatar_backup_manifest(json.dumps(payload).encode())

    with pytest.raises(AvatarBackupValidationError, match="checksum"):
        validate_avatar_backup_manifest(
            package.manifest_path.read_bytes(),
            expected_manifest_checksum="0" * 64,
        )


@pytest.mark.anyio
async def test_restore_collision_never_overwrites_existing_object(tmp_path: Path) -> None:
    content = _png((10, 20, 30, 255))
    reference = _reference(1, content)
    package, _, _ = await _package(tmp_path, (reference,), (content,))
    target = _MemoryTransport()
    source_ref = StorageObjectRef(ImageBucket.PROFILE_IMAGES, reference.object_key)
    existing = b"existing-target-object"
    target.objects[source_ref] = (existing, reference.mime_type)

    with pytest.raises(AvatarBackupError, match="restore failed"):
        await restore_avatar_backup_for_rehearsal(
            ImageStorageService(target),
            manifest_content=package.manifest_path.read_bytes(),
            object_paths={item.object_key: path for item, path in package.object_files},
            expected_manifest_checksum=package.manifest_checksum,
        )
    assert target.objects[source_ref][0] == existing
    assert target.deleted == []


@pytest.mark.anyio
async def test_partial_restore_failure_cleans_only_objects_created_by_attempt(
    tmp_path: Path,
) -> None:
    contents = (_png((10, 20, 30, 255)), _png((30, 20, 10, 255)))
    references = tuple(_reference(index, content) for index, content in enumerate(contents, 1))
    package, _, _ = await _package(tmp_path, references, contents)
    target = _MemoryTransport()
    target.fail_on_upload = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        references[1].object_key,
    )

    with pytest.raises(AvatarBackupError):
        await restore_avatar_backup_for_rehearsal(
            ImageStorageService(target),
            manifest_content=package.manifest_path.read_bytes(),
            object_paths={item.object_key: path for item, path in package.object_files},
            expected_manifest_checksum=package.manifest_checksum,
        )
    first = StorageObjectRef(ImageBucket.PROFILE_IMAGES, references[0].object_key)
    assert first in target.deleted
    assert target.objects == {}


@pytest.mark.anyio
async def test_partial_backup_upload_removes_every_uploaded_avatar(tmp_path: Path) -> None:
    content = _png((10, 20, 30, 255))
    package, _, _ = await _package(tmp_path, (_reference(1, content),), (content,))
    store = _FailManifestArtifactStore()

    with pytest.raises(OSError, match="injected"):
        await store_avatar_backup_package(store, package)

    assert store.objects == {}
