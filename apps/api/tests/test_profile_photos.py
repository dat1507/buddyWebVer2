"""Ownership and replacement-lifecycle tests for profile-photo persistence."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProfilePhoto, StudentProfile, User, UserRole
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
    StoredImage,
)
from app.services.profile_photos import (
    ProfilePhotoNotFoundError,
    get_authorized_profile_photo,
    remove_own_avatar,
    replace_own_avatar,
)

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
OLD_PHOTO_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
NEW_OBJECT_KEY = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee.png"
OLD_OBJECT_KEY = "ffffffff-ffff-4fff-8fff-ffffffffffff.jpg"


def _owner(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _profile() -> StudentProfile:
    return StudentProfile(id=PROFILE_ID, user_id=USER_ID)


def _photo(*, object_key: str = OLD_OBJECT_KEY) -> ProfilePhoto:
    return ProfilePhoto(
        id=OLD_PHOTO_ID,
        profile_id=PROFILE_ID,
        bucket=ImageBucket.PROFILE_IMAGES.value,
        object_key=object_key,
        mime_type="image/jpeg",
        byte_size=100,
        width=10,
        height=10,
        is_avatar=True,
    )


def _stored_image() -> StoredImage:
    return StoredImage(
        reference=StorageObjectRef(ImageBucket.PROFILE_IMAGES, NEW_OBJECT_KEY),
        mime_type="image/png",
        byte_size=120,
        width=12,
        height=10,
    )


def _session(*scalar_values: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=scalar_values)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.delete = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _storage() -> tuple[MagicMock, ImageStorageService]:
    mock = MagicMock(spec=ImageStorageService)
    mock.upload_image = AsyncMock(return_value=_stored_image())
    mock.delete_image = AsyncMock()
    mock.create_signed_url = AsyncMock()
    return mock, cast(ImageStorageService, mock)


@pytest.mark.anyio
async def test_replacement_deletes_old_metadata_only_inside_committed_attachment() -> None:
    previous = _photo()
    mock, session = _session(_profile(), previous, 0)
    storage_mock, storage = _storage()

    result = await replace_own_avatar(
        session,
        storage,
        _owner(),
        original_name="avatar.png",
        declared_content_type="image/png",
        content=b"validated-by-storage-service",
    )

    storage_mock.upload_image.assert_awaited_once_with(
        ImageBucket.PROFILE_IMAGES,
        original_name="avatar.png",
        declared_content_type="image/png",
        content=b"validated-by-storage-service",
    )
    mock.delete.assert_awaited_once_with(previous)
    assert mock.flush.await_count == 2
    mock.commit.assert_awaited_once_with()
    new_photo = mock.add.call_args.args[0]
    assert result.photo is new_photo
    assert new_photo.profile_id == PROFILE_ID
    assert new_photo.object_key == NEW_OBJECT_KEY
    assert new_photo.is_avatar is True
    storage_mock.delete_image.assert_awaited_once_with(
        StorageObjectRef(ImageBucket.PROFILE_IMAGES, OLD_OBJECT_KEY)
    )
    assert result.cleanup_pending is False


@pytest.mark.anyio
async def test_upload_failure_preserves_previous_metadata_and_object() -> None:
    previous = _photo()
    mock, session = _session(_profile(), previous)
    storage_mock, storage = _storage()
    storage_mock.upload_image.side_effect = StorageOperationError("upload failed")

    with pytest.raises(StorageOperationError, match="upload failed"):
        await replace_own_avatar(
            session,
            storage,
            _owner(),
            original_name="avatar.png",
            declared_content_type="image/png",
            content=b"image",
        )

    mock.delete.assert_not_awaited()
    mock.commit.assert_not_awaited()
    storage_mock.delete_image.assert_not_awaited()


@pytest.mark.anyio
async def test_commit_failure_restores_old_metadata_and_compensates_new_object() -> None:
    previous = _photo()
    mock, session = _session(_profile(), previous)
    mock.commit.side_effect = RuntimeError("commit failed")
    storage_mock, storage = _storage()

    with pytest.raises(RuntimeError, match="commit failed"):
        await replace_own_avatar(
            session,
            storage,
            _owner(),
            original_name="avatar.png",
            declared_content_type="image/png",
            content=b"image",
        )

    mock.rollback.assert_awaited_once_with()
    storage_mock.delete_image.assert_awaited_once_with(
        StorageObjectRef(ImageBucket.PROFILE_IMAGES, NEW_OBJECT_KEY)
    )


@pytest.mark.anyio
async def test_removal_commits_owner_metadata_before_storage_delete() -> None:
    photo = _photo()
    mock, session = _session(photo)
    storage_mock, storage = _storage()

    cleanup_pending = await remove_own_avatar(session, storage, _owner(), OLD_PHOTO_ID)

    mock.delete.assert_awaited_once_with(photo)
    mock.commit.assert_awaited_once_with()
    storage_mock.delete_image.assert_awaited_once_with(
        StorageObjectRef(ImageBucket.PROFILE_IMAGES, OLD_OBJECT_KEY)
    )
    assert cleanup_pending is False


@pytest.mark.anyio
async def test_removal_keeps_orphan_retryable_when_storage_delete_fails() -> None:
    photo = _photo()
    _, session = _session(photo)
    storage_mock, storage = _storage()
    storage_mock.delete_image.side_effect = StorageOperationError("delete failed")

    assert await remove_own_avatar(session, storage, _owner(), OLD_PHOTO_ID) is True


@pytest.mark.anyio
async def test_other_user_photo_id_cannot_be_deleted() -> None:
    mock, session = _session(None)
    storage_mock, storage = _storage()

    with pytest.raises(ProfilePhotoNotFoundError):
        await remove_own_avatar(session, storage, _owner(), OLD_PHOTO_ID)

    mock.delete.assert_not_awaited()
    mock.commit.assert_not_awaited()
    storage_mock.delete_image.assert_not_awaited()
    statement = mock.scalar.await_args.args[0]
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    assert USER_ID in compiled.params.values()
    assert OLD_PHOTO_ID in compiled.params.values()


@pytest.mark.anyio
async def test_other_user_photo_id_cannot_be_resolved_for_delivery() -> None:
    mock, session = _session(None)

    with pytest.raises(ProfilePhotoNotFoundError):
        await get_authorized_profile_photo(session, _owner(), OLD_PHOTO_ID)

    statement = mock.scalar.await_args.args[0]
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    assert USER_ID in compiled.params.values()
    assert OTHER_USER_ID not in compiled.params.values()
    assert OLD_PHOTO_ID in compiled.params.values()


@pytest.mark.anyio
async def test_admin_delivery_query_is_not_scoped_to_admin_profile_owner() -> None:
    photo = _photo()
    mock, session = _session(photo)

    result = await get_authorized_profile_photo(
        session,
        _owner(role=UserRole.ADMIN),
        OLD_PHOTO_ID,
    )

    assert result is photo
    statement = mock.scalar.await_args.args[0]
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    assert OLD_PHOTO_ID in compiled.params.values()
    assert USER_ID not in compiled.params.values()
