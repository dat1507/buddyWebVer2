"""Audience-safe Event list and detail queries with localized cover projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventPhase,
    EventStatus,
    EventVisibility,
    User,
    UserRole,
)
from app.schemas.event import (
    EventLocale,
    PublicEventCoverResponse,
    PublicEventListResponse,
    PublicEventResponse,
)
from app.services.image_storage import (
    MAX_SIGNED_URL_SECONDS,
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
)

MAX_PUBLIC_EVENT_RANGE = timedelta(days=93)


class EventQueryValidationError(ValueError):
    """Raised when a public Event query exceeds its bounded contract."""


@dataclass(frozen=True, slots=True)
class PublicEventFilters:
    """Validated filters shared by the public list service and API."""

    locale: EventLocale = "en"
    category: str | None = None
    phase: EventPhase | None = None
    from_instant: datetime | None = None
    to_instant: datetime | None = None
    page: int = 1
    page_size: int = 20


def _is_verified_member(viewer: User | None) -> bool:
    return bool(
        viewer is not None
        and viewer.role is UserRole.USER
        and viewer.is_active
        and viewer.deleted_at is None
        and viewer.is_current_email_verified
    )


def _audience_clause(viewer: User | None) -> ColumnElement[bool]:
    allowed_visibility = (
        (EventVisibility.PUBLIC, EventVisibility.MEMBERS)
        if _is_verified_member(viewer)
        else (EventVisibility.PUBLIC,)
    )
    return and_(
        Event.deleted_at.is_(None),
        Event.published_at.is_not(None),
        Event.status.in_((EventStatus.PUBLISHED, EventStatus.CANCELLED)),
        Event.visibility.in_(allowed_visibility),
    )


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventQueryValidationError(f"{field_name} must be timezone-aware.")
    return value


def _validated(filters: PublicEventFilters) -> PublicEventFilters:
    if filters.page < 1 or not 1 <= filters.page_size <= 100:
        raise EventQueryValidationError("Event pagination is out of bounds.")

    category = filters.category.strip() if filters.category is not None else None
    if filters.category is not None and (not category or len(category) > 80):
        raise EventQueryValidationError("Event category is invalid.")

    if (filters.from_instant is None) != (filters.to_instant is None):
        raise EventQueryValidationError("Event date range requires both from and to.")
    if filters.from_instant is not None and filters.to_instant is not None:
        start = _require_aware(filters.from_instant, field_name="Event range start")
        end = _require_aware(filters.to_instant, field_name="Event range end")
        if end <= start or end - start > MAX_PUBLIC_EVENT_RANGE:
            raise EventQueryValidationError("Event date range is invalid.")

    return PublicEventFilters(
        locale=filters.locale,
        category=category,
        phase=filters.phase,
        from_instant=filters.from_instant,
        to_instant=filters.to_instant,
        page=filters.page,
        page_size=filters.page_size,
    )


def _filter_clauses(
    filters: PublicEventFilters,
    *,
    viewer: User | None,
    now: datetime,
) -> tuple[ColumnElement[bool], ...]:
    clauses: list[ColumnElement[bool]] = [_audience_clause(viewer)]
    if filters.category is not None:
        clauses.append(Event.category == filters.category)
    if filters.phase is EventPhase.UPCOMING:
        clauses.append(Event.start_date > now)
    elif filters.phase is EventPhase.ONGOING:
        clauses.extend((Event.start_date <= now, Event.end_date > now))
    elif filters.phase is EventPhase.COMPLETED:
        clauses.append(Event.end_date <= now)
    if filters.from_instant is not None and filters.to_instant is not None:
        clauses.extend(
            (
                Event.start_date < filters.to_instant,
                Event.end_date > filters.from_instant,
            )
        )
    return tuple(clauses)


def _cover_join() -> ColumnElement[bool]:
    return and_(
        Event.cover_media_id == EventMedia.id,
        Event.id == EventMedia.event_id,
        EventMedia.deleted_at.is_(None),
        EventMedia.usage == EventMediaUsage.EVENT_COVER,
        EventMedia.processing_status == EventMediaProcessingStatus.READY,
    )


def _event_page_statement(
    clauses: tuple[ColumnElement[bool], ...],
    *,
    page: int,
    page_size: int,
) -> Select[tuple[Event, EventMedia]]:
    return (
        select(Event, EventMedia)
        .outerjoin(EventMedia, _cover_join())
        .where(*clauses)
        .order_by(Event.start_date.asc(), Event.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )


def _localized(primary: str | None, fallback: str | None) -> str:
    value = primary or fallback
    if value is None:
        raise RuntimeError("Published Event localization is incomplete.")
    return value


async def _project_event(
    storage: ImageStorageService,
    event: Event,
    media: EventMedia | None,
    *,
    locale: EventLocale,
    now: datetime,
) -> PublicEventResponse:
    if event.start_date is None or event.end_date is None:
        raise RuntimeError("Published Event schedule is incomplete.")
    phase = event.phase_at(now)
    if phase is None:
        raise RuntimeError("Published Event phase is unavailable.")

    if locale == "de":
        title = _localized(event.title_de, event.title_en)
        description = _localized(event.description_de, event.description_en)
        location = _localized(event.location_de, event.location_en)
        alt_text = _localized(media.alt_de, media.alt_en) if media is not None else None
    else:
        title = _localized(event.title_en, event.title_de)
        description = _localized(event.description_en, event.description_de)
        location = _localized(event.location_en, event.location_de)
        alt_text = _localized(media.alt_en, media.alt_de) if media is not None else None

    cover: PublicEventCoverResponse | None = None
    if media is not None and alt_text is not None:
        url = await storage.create_signed_url(
            StorageObjectRef(
                bucket=ImageBucket.EVENT_MEDIA,
                object_key=media.object_key,
            ),
            expires_in=MAX_SIGNED_URL_SECONDS,
        )
        cover = PublicEventCoverResponse(
            url=url,
            alt_text=alt_text,
            mime_type=media.mime_type,
            width=media.width,
            height=media.height,
            expires_in=MAX_SIGNED_URL_SECONDS,
        )

    return PublicEventResponse(
        id=event.id,
        locale=locale,
        title=title,
        description=description,
        start_date=event.start_date,
        end_date=event.end_date,
        timezone=event.timezone,
        location=location,
        category=event.category,
        organizer=event.organizer,
        registration_url=event.registration_url,
        registration_enabled=event.registration_enabled and event.status is EventStatus.PUBLISHED,
        registration_deadline=event.registration_deadline,
        status=event.status,
        visibility=event.visibility,
        phase=phase,
        cover=cover,
    )


async def list_public_events(
    session: AsyncSession,
    storage: ImageStorageService,
    *,
    viewer: User | None,
    filters: PublicEventFilters,
    now: datetime | None = None,
) -> PublicEventListResponse:
    """Return one bounded Event page using a constant two-query database plan."""
    checked = _validated(filters)
    reference_time = _require_aware(now or datetime.now(UTC), field_name="Query time")
    clauses = _filter_clauses(checked, viewer=viewer, now=reference_time)
    total = int(
        cast(
            int,
            await session.scalar(select(func.count()).select_from(Event).where(*clauses)),
        )
        or 0
    )
    rows = (
        await session.execute(
            _event_page_statement(
                clauses,
                page=checked.page,
                page_size=checked.page_size,
            )
        )
    ).all()
    items = [
        await _project_event(
            storage,
            cast(Event, event),
            cast(EventMedia | None, media),
            locale=checked.locale,
            now=reference_time,
        )
        for event, media in rows
    ]
    return PublicEventListResponse(
        items=items,
        page=checked.page,
        page_size=checked.page_size,
        total=total,
        total_pages=(total + checked.page_size - 1) // checked.page_size,
    )


async def get_public_event_detail(
    session: AsyncSession,
    storage: ImageStorageService,
    event_id: UUID,
    *,
    viewer: User | None,
    locale: EventLocale,
    now: datetime | None = None,
) -> PublicEventResponse | None:
    """Return one authorized Event, keeping hidden/deleted/unknown records indistinguishable."""
    reference_time = _require_aware(now or datetime.now(UTC), field_name="Query time")
    statement = (
        select(Event, EventMedia)
        .outerjoin(EventMedia, _cover_join())
        .where(Event.id == event_id, _audience_clause(viewer))
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    event, media = row
    return await _project_event(
        storage,
        cast(Event, event),
        cast(EventMedia | None, media),
        locale=locale,
        now=reference_time,
    )
