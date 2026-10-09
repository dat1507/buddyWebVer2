"""Failure-safe Event cover persistence, metadata, deletion, and authorized delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast
from uuid import UUID, uuid4

from sqlalchemy import select
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
from app.schemas.event import AdminEventMediaResponse, EventMediaUpdate
from app.services.events import (
    EventAccessError,
    EventNotFoundError,
    EventVersionConflictError,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)


class EventMediaNotFoundError(LookupError):
    """Raised for missing, cross-Event, deleted, or unauthorized media."""


class EventMediaConflictError(RuntimeError):
    """Raised when editorial state prevents a media mutation."""


@dataclass(frozen=True, slots=True)
class EventCoverReplacement:
    """Staged database replacement plus object cleanup identities."""

    event: Event
    media: EventMedia
    new_reference: StorageObjectRef
    previous_reference: StorageObjectRef | None


@dataclass(frozen=True, slots=True)
class EventMediaDeletion:
    """Staged media deletion plus its post-commit object cleanup identity."""

    event_id: UUID
    media_id: UUID
    event_version: int
    reference: StorageObjectRef


@dataclass(frozen=True, slots=True)
class AuthorizedEventMedia:
    """Authorized active media ready for short-lived delivery."""

    media: EventMedia
    reference: StorageObjectRef


EVENT_COVER_SORT_ORDER: Final = 0


def _require_admin(actor: User) -> None:
    if (
        actor.role is not UserRole.ADMIN
        or not actor.is_active
        or actor.deleted_at is not None
        or not isinstance(actor.id, UUID)
    ):
        raise EventAccessError("Event media mutation requires a current active Admin.")


async def _locked_event(session: AsyncSession, event_id: UUID) -> Event:
    event = cast(
        Event | None,
        await session.scalar(
            select(Event).where(Event.id == event_id, Event.deleted_at.is_(None)).with_for_update()
        ),
    )
    if event is None:
        raise EventNotFoundError("Event was not found.")
    return event


def _require_version(event: Event, version: int) -> None:
    if event.version != version:
        raise EventVersionConflictError("Event version is stale.")


async def _active_media(
    session: AsyncSession,
    *,
    event_id: UUID,
    media_id: UUID,
    lock: bool,
) -> EventMedia | None:
    statement = select(EventMedia).where(
        EventMedia.id == media_id,
        EventMedia.event_id == event_id,
        EventMedia.deleted_at.is_(None),
    )
    if lock:
        statement = statement.with_for_update()
    return cast(EventMedia | None, await session.scalar(statement))


def event_media_reference(media: EventMedia) -> StorageObjectRef:
    """Build a trusted private reference from constrained EventMedia metadata."""
    return StorageObjectRef(bucket=ImageBucket.EVENT_MEDIA, object_key=media.object_key)


async def _delete_object_safely(
    storage: ImageStorageService,
    reference: StorageObjectRef,
) -> bool:
    try:
        await storage.delete_image(reference)
    except StorageOperationError:
        return False
    return True


async def stage_event_cover_replacement(
    session: AsyncSession,
    storage: ImageStorageService,
    actor: User,
    event_id: UUID,
    *,
    version: int,
    original_name: str,
    declared_content_type: str,
    content: bytes,
    alt_en: str,
    alt_de: str,
) -> EventCoverReplacement:
    """Upload and stage one cover replacement without committing the owning transaction."""
    _require_admin(actor)
    stored = await storage.upload_image(
        ImageBucket.EVENT_MEDIA,
        original_name=original_name,
        declared_content_type=declared_content_type,
        content=content,
    )
    try:
        event = await _locked_event(session, event_id)
        _require_version(event, version)
        previous = (
            await _active_media(
                session,
                event_id=event.id,
                media_id=event.cover_media_id,
                lock=True,
            )
            if event.cover_media_id is not None
            else None
        )
        media = EventMedia(
            id=uuid4(),
            event_id=event.id,
            bucket=ImageBucket.EVENT_MEDIA.value,
            object_key=stored.reference.object_key,
            usage=EventMediaUsage.EVENT_COVER,
            alt_en=alt_en,
            alt_de=alt_de,
            mime_type=stored.mime_type,
            byte_size=stored.byte_size,
            width=stored.width,
            height=stored.height,
            sort_order=EVENT_COVER_SORT_ORDER,
            processing_status=EventMediaProcessingStatus.READY,
            created_by=actor.id,
        )
        session.add(media)
        await session.flush()
        event.cover_media_id = media.id
        event.updated_by = actor.id
        event.version += 1
        if previous is not None:
            await session.delete(previous)
        await session.flush()
    except Exception:
        await _delete_object_safely(storage, stored.reference)
        raise

    return EventCoverReplacement(
        event=event,
        media=media,
        new_reference=stored.reference,
        previous_reference=event_media_reference(previous) if previous is not None else None,
    )


async def compensate_cover_replacement(
    storage: ImageStorageService,
    replacement: EventCoverReplacement,
) -> bool:
    """Best-effort cleanup for a new object after transaction rollback."""
    return await _delete_object_safely(storage, replacement.new_reference)


async def cleanup_replaced_cover(
    storage: ImageStorageService,
    replacement: EventCoverReplacement,
) -> bool:
    """Remove the previous object after commit; false leaves reconciliation work pending."""
    if replacement.previous_reference is None:
        return True
    return await _delete_object_safely(storage, replacement.previous_reference)


async def update_event_media_metadata(
    session: AsyncSession,
    actor: User,
    event_id: UUID,
    media_id: UUID,
    update: EventMediaUpdate,
) -> tuple[Event, EventMedia]:
    """Update one same-Event cover metadata row under parent optimistic concurrency."""
    _require_admin(actor)
    event = await _locked_event(session, event_id)
    _require_version(event, update.version)
    media = await _active_media(session, event_id=event.id, media_id=media_id, lock=True)
    if media is None or media.usage is not EventMediaUsage.EVENT_COVER:
        raise EventMediaNotFoundError("Event media was not found.")
    changes = update.model_dump(exclude={"version"}, exclude_unset=True)
    for field, value in changes.items():
        setattr(media, field, value)
    event.updated_by = actor.id
    event.version += 1
    await session.flush()
    return event, media


async def delete_event_media(
    session: AsyncSession,
    actor: User,
    event_id: UUID,
    media_id: UUID,
    *,
    version: int,
) -> EventMediaDeletion:
    """Stage deletion of one Event cover and detach it only from a draft Event."""
    _require_admin(actor)
    event = await _locked_event(session, event_id)
    _require_version(event, version)
    media = await _active_media(session, event_id=event.id, media_id=media_id, lock=True)
    if media is None or media.usage is not EventMediaUsage.EVENT_COVER:
        raise EventMediaNotFoundError("Event media was not found.")
    if event.cover_media_id == media.id:
        if event.status is not EventStatus.DRAFT:
            raise EventMediaConflictError("Published or cancelled Event cover cannot be removed.")
        event.cover_media_id = None
    event.updated_by = actor.id
    event.version += 1
    reference = event_media_reference(media)
    await session.delete(media)
    await session.flush()
    return EventMediaDeletion(
        event_id=event.id,
        media_id=media.id,
        event_version=event.version,
        reference=reference,
    )


async def cleanup_deleted_media(
    storage: ImageStorageService,
    deletion: EventMediaDeletion,
) -> bool:
    """Remove deleted media bytes after commit; false leaves reconciliation work pending."""
    return await _delete_object_safely(storage, deletion.reference)


def _viewer_can_read_event(event: Event, viewer: User | None) -> bool:
    if event.deleted_at is not None:
        return False
    if (
        viewer is not None
        and viewer.role is UserRole.ADMIN
        and viewer.is_active
        and viewer.deleted_at is None
    ):
        return True
    if event.published_at is None or event.status not in {
        EventStatus.PUBLISHED,
        EventStatus.CANCELLED,
    }:
        return False
    if event.visibility is EventVisibility.PUBLIC:
        return True
    return bool(
        viewer is not None
        and viewer.role is UserRole.USER
        and viewer.is_active
        and viewer.deleted_at is None
        and viewer.is_current_email_verified
        and event.visibility is EventVisibility.MEMBERS
    )


async def get_authorized_event_media(
    session: AsyncSession,
    event_id: UUID,
    media_id: UUID,
    *,
    viewer: User | None,
) -> AuthorizedEventMedia | None:
    """Authorize media by its parent Event without distinguishing hidden from missing rows."""
    row = (
        await session.execute(
            select(Event, EventMedia)
            .join(EventMedia, EventMedia.event_id == Event.id)
            .where(
                Event.id == event_id,
                EventMedia.id == media_id,
                EventMedia.deleted_at.is_(None),
                EventMedia.processing_status == EventMediaProcessingStatus.READY,
                EventMedia.usage == EventMediaUsage.EVENT_COVER,
            )
        )
    ).one_or_none()
    if row is None:
        return None
    event, media = cast(tuple[Event, EventMedia], row)
    if not _viewer_can_read_event(event, viewer):
        return None
    return AuthorizedEventMedia(media=media, reference=event_media_reference(media))


def project_admin_event_media(media: EventMedia) -> AdminEventMediaResponse:
    """Serialize allowlisted media metadata without bucket or key."""
    return AdminEventMediaResponse.model_validate(media)
