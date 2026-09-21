"""Transactional Event draft, publication and deletion use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventRegistration,
    EventStatus,
    User,
    UserRole,
)
from app.schemas.event import (
    AdminEventResponse,
    EventDraftCreate,
    EventDraftUpdate,
    EventStatusUpdate,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)

_CONTENT_FIELDS: Final = frozenset(EventDraftCreate.model_fields)
_SCHEDULE_FIELDS: Final = frozenset({"start_date", "end_date"})


class EventAccessError(PermissionError):
    """Raised when a non-current Admin reaches an Event mutation service."""


class EventNotFoundError(LookupError):
    """Raised when an Event is missing or already deleted."""


class EventVersionConflictError(ValueError):
    """Raised when optimistic concurrency detects a stale Event version."""


class EventValidationError(ValueError):
    """Raised when merged Event content cannot satisfy a domain invariant."""


class EventDependencyConflictError(RuntimeError):
    """Raised when related records make a requested Event mutation unsafe."""


class EventRelations(Protocol):
    """Boundary implemented as recap and slider persistence becomes available."""

    async def published_recap_boundary(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> datetime | None: ...

    async def detach_for_delete(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> None: ...


class NoEventRelations:
    """Current no-op adapter while recap and slider tables do not yet exist."""

    async def published_recap_boundary(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> datetime | None:
        del session, event_id
        return None

    async def detach_for_delete(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> None:
        del session, event_id


NO_EVENT_RELATIONS: Final[EventRelations] = NoEventRelations()


@dataclass(frozen=True, slots=True)
class EventDeletionPlan:
    """Storage work that must run only after the owning transaction commits."""

    event_id: UUID
    media: tuple[StorageObjectRef, ...]


def _require_admin(actor: User) -> None:
    if (
        actor.role is not UserRole.ADMIN
        or not actor.is_active
        or actor.deleted_at is not None
        or not isinstance(actor.id, UUID)
    ):
        raise EventAccessError("Event mutation requires a current active Admin.")


async def get_event(session: AsyncSession, event_id: UUID) -> Event | None:
    """Read one active Event for internal admin/query services."""
    return cast(
        Event | None,
        await session.scalar(select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))),
    )


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


def _effective(event: Event, changes: dict[str, object | None], field: str) -> object | None:
    return changes[field] if field in changes else getattr(event, field)


def _validate_schedule(event: Event, changes: dict[str, object | None]) -> None:
    start_date = cast(datetime | None, _effective(event, changes, "start_date"))
    end_date = cast(datetime | None, _effective(event, changes, "end_date"))
    deadline = cast(
        datetime | None,
        _effective(event, changes, "registration_deadline"),
    )
    if start_date is not None and end_date is not None and end_date <= start_date:
        raise EventValidationError("Event end date must be later than start date.")
    if start_date is not None and deadline is not None and deadline > start_date:
        raise EventValidationError("Registration deadline cannot be after the event start date.")


async def _validate_cover(
    session: AsyncSession,
    event_id: UUID,
    cover_media_id: UUID,
) -> None:
    valid_cover = await session.scalar(
        select(EventMedia.id).where(
            EventMedia.id == cover_media_id,
            EventMedia.event_id == event_id,
            EventMedia.usage == EventMediaUsage.EVENT_COVER,
            EventMedia.processing_status == EventMediaProcessingStatus.READY,
            EventMedia.deleted_at.is_(None),
        )
    )
    if valid_cover is None:
        raise EventValidationError("Event cover is invalid or not ready.")


async def _validate_publishable(
    session: AsyncSession,
    event: Event,
    changes: dict[str, object | None],
) -> None:
    for field in (
        "title_en",
        "title_de",
        "description_en",
        "description_de",
        "location_en",
        "location_de",
    ):
        value = _effective(event, changes, field)
        if not isinstance(value, str) or not value.strip():
            raise EventValidationError("Event publication fields are incomplete.")

    start_date = cast(datetime | None, _effective(event, changes, "start_date"))
    end_date = cast(datetime | None, _effective(event, changes, "end_date"))
    if start_date is None or end_date is None or end_date <= start_date:
        raise EventValidationError("Event publication times are invalid.")

    cover_media_id = cast(UUID | None, _effective(event, changes, "cover_media_id"))
    if cover_media_id is None:
        raise EventValidationError("Event publication requires a cover.")
    await _validate_cover(session, event.id, cover_media_id)


async def _validate_recap_boundary(
    session: AsyncSession,
    event: Event,
    changes: dict[str, object | None],
    relations: EventRelations,
) -> None:
    if not _SCHEDULE_FIELDS.intersection(changes):
        return
    boundary = await relations.published_recap_boundary(session, event.id)
    if boundary is None:
        return
    if boundary.tzinfo is None or boundary.utcoffset() is None:
        raise RuntimeError("Published recap boundary must be timezone-aware.")
    end_date = cast(datetime | None, _effective(event, changes, "end_date"))
    if end_date is None or end_date > boundary:
        raise EventDependencyConflictError(
            "Unpublish the Event recap before moving the Event beyond its recap boundary."
        )


def _draft_changes(update: EventDraftUpdate) -> dict[str, object | None]:
    values = update.model_dump(exclude_unset=True)
    values.pop("version", None)
    return {
        field: cast(object | None, value)
        for field, value in values.items()
        if field in _CONTENT_FIELDS or field == "cover_media_id"
    }


async def create_event_draft(
    session: AsyncSession,
    actor: User,
    draft: EventDraftCreate,
) -> Event:
    """Stage one incomplete Event draft; the API owns commit and audit."""
    _require_admin(actor)
    values = draft.model_dump()
    event = Event(
        **values,
        created_by=actor.id,
        updated_by=actor.id,
        status=EventStatus.DRAFT,
        version=1,
    )
    _validate_schedule(event, {})
    session.add(event)
    await session.flush()
    return event


async def update_event_draft(
    session: AsyncSession,
    actor: User,
    event_id: UUID,
    update: EventDraftUpdate,
    *,
    relations: EventRelations = NO_EVENT_RELATIONS,
) -> Event:
    """Lock, validate and stage an optimistic Event content update."""
    _require_admin(actor)
    event = await _locked_event(session, event_id)
    _require_version(event, update.version)
    changes = _draft_changes(update)
    _validate_schedule(event, changes)
    await _validate_recap_boundary(session, event, changes, relations)

    cover_media_id = cast(UUID | None, changes.get("cover_media_id"))
    if "cover_media_id" in changes and cover_media_id is not None:
        await _validate_cover(session, event.id, cover_media_id)

    remains_publicly_published = event.status is EventStatus.PUBLISHED or (
        event.status is EventStatus.CANCELLED and event.published_at is not None
    )
    if remains_publicly_published:
        await _validate_publishable(session, event, changes)

    for field, value in changes.items():
        setattr(event, field, value)
    event.updated_by = actor.id
    event.version += 1
    await session.flush()
    return event


async def set_event_status(
    session: AsyncSession,
    actor: User,
    event_id: UUID,
    update: EventStatusUpdate,
    *,
    now: datetime | None = None,
) -> Event:
    """Publish, unpublish or cancel one locked Event without committing it."""
    _require_admin(actor)
    event = await _locked_event(session, event_id)
    _require_version(event, update.version)
    if event.status is update.status:
        return event

    if update.status is EventStatus.PUBLISHED:
        await _validate_publishable(session, event, {})
        published_at = now or datetime.now(UTC)
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise EventValidationError("Publication time must be timezone-aware.")
        if event.published_at is None:
            event.published_at = published_at

    event.status = update.status
    event.updated_by = actor.id
    event.version += 1
    await session.flush()
    return event


async def delete_event(
    session: AsyncSession,
    actor: User,
    event_id: UUID,
    *,
    version: int,
    relations: EventRelations = NO_EVENT_RELATIONS,
) -> EventDeletionPlan:
    """Stage an eligible hard delete and return post-commit storage cleanup work."""
    _require_admin(actor)
    event = await _locked_event(session, event_id)
    _require_version(event, version)

    recap_boundary = await relations.published_recap_boundary(session, event.id)
    if recap_boundary is not None:
        raise EventDependencyConflictError(
            "Published Event recap must be unpublished before deletion."
        )
    active_registration_id = await session.scalar(
        select(EventRegistration.id)
        .where(
            EventRegistration.event_id == event.id,
            EventRegistration.active_clause(),
        )
        .limit(1)
    )
    if active_registration_id is not None:
        raise EventDependencyConflictError(
            "Active Event registrations must be resolved before deletion."
        )

    media_result = await session.scalars(
        select(EventMedia.object_key).where(EventMedia.event_id == event.id)
    )
    media = tuple(
        StorageObjectRef(bucket=ImageBucket.EVENT_MEDIA, object_key=object_key)
        for object_key in media_result.all()
    )

    event.cover_media_id = None
    await relations.detach_for_delete(session, event.id)
    await session.flush()
    await session.delete(event)
    await session.flush()
    return EventDeletionPlan(event_id=event.id, media=media)


async def cleanup_deleted_event_media(
    storage: ImageStorageService,
    plan: EventDeletionPlan,
) -> tuple[StorageObjectRef, ...]:
    """Delete post-commit objects and return retryable failures without restoring DB rows."""
    failed: list[StorageObjectRef] = []
    for reference in plan.media:
        try:
            await storage.delete_image(reference)
        except StorageOperationError:
            failed.append(reference)
    return tuple(failed)


def project_admin_event(event: Event) -> AdminEventResponse:
    """Serialize only the allowlisted Admin API projection."""
    return AdminEventResponse.model_validate(event)
