"""Ownership, replacement, deletion, and audience tests for EVT-011 services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventStatus,
    EventVisibility,
    User,
    UserRole,
)
from app.schemas.event import EventMediaUpdate
from app.services.event_media import (
    EventMediaConflictError,
    EventMediaNotFoundError,
    cleanup_deleted_media,
    cleanup_replaced_cover,
    delete_event_media,
    get_authorized_event_media,
    stage_event_cover_replacement,
    update_event_media_metadata,
)
from app.services.events import EventVersionConflictError
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
    StoredImage,
)

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
MEDIA_ID = UUID("22222222-2222-4222-8222-222222222222")
ADMIN_ID = UUID("33333333-3333-4333-8333-333333333333")
USER_ID = UUID("44444444-4444-4444-8444-444444444444")
OLD_KEY = "55555555-5555-4555-8555-555555555555.webp"
NEW_KEY = "66666666-6666-4666-8666-666666666666.webp"
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


def _actor(*, role: UserRole = UserRole.ADMIN, verified: bool = True) -> User:
    return User(
        id=ADMIN_ID if role is UserRole.ADMIN else USER_ID,
        email="actor@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=verified,
        email_verified_at=NOW if role is UserRole.USER and verified else None,
        deleted_at=None,
    )


def _event(
    *,
    status: EventStatus = EventStatus.DRAFT,
    visibility: EventVisibility = EventVisibility.PUBLIC,
    version: int = 3,
) -> Event:
    return Event(
        id=EVENT_ID,
        title_en="Buddy Day",
        title_de="Buddy-Tag",
        description_en="Community event",
        description_de="Community-Veranstaltung",
        start_date=NOW + timedelta(days=1),
        end_date=NOW + timedelta(days=1, hours=2),
        timezone="Asia/Ho_Chi_Minh",
        location_en="VGU Campus",
        location_de="VGU-Campus",
        cover_media_id=MEDIA_ID,
        status=status,
        visibility=visibility,
        registration_enabled=False,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=NOW if status is not EventStatus.DRAFT else None,
        version=version,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _media(*, object_key: str = OLD_KEY) -> EventMedia:
    return EventMedia(
        id=MEDIA_ID,
        event_id=EVENT_ID,
        bucket="event-media",
        object_key=object_key,
        usage=EventMediaUsage.EVENT_COVER,
        alt_en="Event poster",
        alt_de="Veranstaltungsplakat",
        mime_type="image/webp",
        byte_size=1024,
        width=1600,
        height=900,
        sort_order=0,
        processing_status=EventMediaProcessingStatus.READY,
        created_by=ADMIN_ID,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _storage() -> tuple[MagicMock, ImageStorageService]:
    mock = MagicMock(spec=ImageStorageService)
    mock.upload_image = AsyncMock(
        return_value=StoredImage(
            reference=StorageObjectRef(ImageBucket.EVENT_MEDIA, NEW_KEY),
            mime_type="image/webp",
            byte_size=2048,
            width=1200,
            height=800,
        )
    )
    mock.delete_image = AsyncMock()
    mock.create_signed_url = AsyncMock(return_value="https://storage.example.test/signed")
    return mock, cast(ImageStorageService, mock)


def _session(*scalar_values: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=scalar_values)
    mock.execute = AsyncMock()
    mock.flush = AsyncMock()
    mock.delete = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_cover_replacement_is_same_event_versioned_and_defers_old_cleanup() -> None:
    event = _event()
    previous = _media()
    mock, session = _session(event, previous)
    storage_mock, storage = _storage()

    replacement = await stage_event_cover_replacement(
        session,
        storage,
        _actor(),
        EVENT_ID,
        version=3,
        original_name="cover.webp",
        declared_content_type="image/webp",
        content=b"validated-by-storage",
        alt_en="New poster",
        alt_de="Neues Plakat",
    )

    assert replacement.event is event
    assert replacement.media.event_id == EVENT_ID
    assert replacement.media.object_key == NEW_KEY
    assert replacement.media.created_by == ADMIN_ID
    assert event.cover_media_id == replacement.media.id
    assert event.version == 4
    mock.add.assert_called_once_with(replacement.media)
    mock.delete.assert_awaited_once_with(previous)
    assert mock.flush.await_count == 2
    storage_mock.delete_image.assert_not_awaited()
    assert replacement.previous_reference == StorageObjectRef(ImageBucket.EVENT_MEDIA, OLD_KEY)


@pytest.mark.anyio
async def test_failed_version_after_upload_compensates_new_object() -> None:
    event = _event(version=4)
    _, session = _session(event)
    storage_mock, storage = _storage()

    with pytest.raises(EventVersionConflictError):
        await stage_event_cover_replacement(
            session,
            storage,
            _actor(),
            EVENT_ID,
            version=3,
            original_name="cover.webp",
            declared_content_type="image/webp",
            content=b"validated-by-storage",
            alt_en="New poster",
            alt_de="Neues Plakat",
        )

    storage_mock.delete_image.assert_awaited_once_with(
        StorageObjectRef(ImageBucket.EVENT_MEDIA, NEW_KEY)
    )


@pytest.mark.anyio
async def test_metadata_update_rejects_cross_event_media() -> None:
    event = _event()
    mock, session = _session(event, None)

    with pytest.raises(EventMediaNotFoundError):
        await update_event_media_metadata(
            session,
            _actor(),
            EVENT_ID,
            MEDIA_ID,
            EventMediaUpdate(version=3, alt_en="Changed"),
        )

    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_metadata_update_increments_parent_version() -> None:
    event = _event()
    media = _media()
    mock, session = _session(event, media)

    updated_event, updated_media = await update_event_media_metadata(
        session,
        _actor(),
        EVENT_ID,
        MEDIA_ID,
        EventMediaUpdate(version=3, alt_en="Changed", sort_order=2),
    )

    assert updated_event.version == 4
    assert updated_media.alt_en == "Changed"
    assert updated_media.sort_order == 2
    mock.flush.assert_awaited_once_with()


@pytest.mark.anyio
async def test_active_cover_delete_is_draft_only_and_storage_runs_after_commit_boundary() -> None:
    published = _event(status=EventStatus.PUBLISHED)
    media = _media()
    published_mock, published_session = _session(published, media)
    with pytest.raises(EventMediaConflictError):
        await delete_event_media(
            published_session,
            _actor(),
            EVENT_ID,
            MEDIA_ID,
            version=3,
        )
    published_mock.delete.assert_not_awaited()

    draft = _event()
    mock, session = _session(draft, media)
    deletion = await delete_event_media(
        session,
        _actor(),
        EVENT_ID,
        MEDIA_ID,
        version=3,
    )
    assert draft.cover_media_id is None
    assert deletion.event_version == 4
    mock.delete.assert_awaited_once_with(media)

    storage_mock, storage = _storage()
    assert await cleanup_deleted_media(storage, deletion) is True
    storage_mock.delete_image.assert_awaited_once_with(deletion.reference)


@pytest.mark.anyio
async def test_cleanup_failure_is_reported_without_object_identity_leak() -> None:
    event = _event()
    previous = _media()
    _, session = _session(event, previous)
    storage_mock, storage = _storage()
    replacement = await stage_event_cover_replacement(
        session,
        storage,
        _actor(),
        EVENT_ID,
        version=3,
        original_name="cover.webp",
        declared_content_type="image/webp",
        content=b"validated-by-storage",
        alt_en="New poster",
        alt_de="Neues Plakat",
    )
    storage_mock.delete_image.side_effect = StorageOperationError("provider detail")
    assert await cleanup_replaced_cover(storage, replacement) is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("viewer", "event", "allowed"),
    [
        (None, _event(status=EventStatus.PUBLISHED), True),
        (None, _event(status=EventStatus.PUBLISHED, visibility=EventVisibility.MEMBERS), False),
        (
            _actor(role=UserRole.USER),
            _event(status=EventStatus.PUBLISHED, visibility=EventVisibility.MEMBERS),
            True,
        ),
        (
            _actor(role=UserRole.USER, verified=False),
            _event(status=EventStatus.PUBLISHED, visibility=EventVisibility.MEMBERS),
            False,
        ),
        (_actor(), _event(status=EventStatus.DRAFT), True),
        (None, _event(status=EventStatus.DRAFT), False),
    ],
)
async def test_media_delivery_follows_parent_event_audience(
    viewer: User | None,
    event: Event,
    allowed: bool,
) -> None:
    result = MagicMock()
    result.one_or_none.return_value = (event, _media())
    mock, session = _session()
    mock.execute.return_value = result

    authorized = await get_authorized_event_media(
        session,
        EVENT_ID,
        MEDIA_ID,
        viewer=viewer,
    )

    assert (authorized is not None) is allowed
    if authorized is not None:
        assert authorized.reference == StorageObjectRef(ImageBucket.EVENT_MEDIA, OLD_KEY)
