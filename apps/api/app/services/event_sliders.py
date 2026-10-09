"""Read-only Landing slider projection derived from canonical public Events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final, cast

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventStatus,
    EventVisibility,
)
from app.schemas.event import EventLocale, EventSliderCta, PublicEventSliderResponse
from app.services.image_storage import (
    MAX_SIGNED_URL_SECONDS,
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
)

MAX_EVENT_SLIDES: Final = 12
MAX_SLIDER_EXCERPT: Final = 500


def _localized(primary: str | None, fallback: str | None) -> str:
    value = primary or fallback
    if value is None:
        raise RuntimeError("Published Event localization is incomplete.")
    return value


def _excerpt(value: str) -> str:
    if len(value) <= MAX_SLIDER_EXCERPT:
        return value
    return value[: MAX_SLIDER_EXCERPT - 3].rstrip() + "..."


def _slider_statement(now: datetime) -> Select[tuple[Event, EventMedia]]:
    cover_join = and_(
        Event.cover_media_id == EventMedia.id,
        Event.id == EventMedia.event_id,
        EventMedia.deleted_at.is_(None),
        EventMedia.usage == EventMediaUsage.EVENT_COVER,
        EventMedia.processing_status == EventMediaProcessingStatus.READY,
    )
    return (
        select(Event, EventMedia)
        .join(EventMedia, cover_join)
        .where(
            Event.deleted_at.is_(None),
            Event.published_at.is_not(None),
            Event.status == EventStatus.PUBLISHED,
            Event.visibility == EventVisibility.PUBLIC,
            Event.start_date >= now,
        )
        .order_by(Event.start_date.asc(), Event.id.asc())
        .limit(MAX_EVENT_SLIDES)
    )


async def list_public_event_sliders(
    session: AsyncSession,
    storage: ImageStorageService,
    *,
    locale: EventLocale,
    now: datetime | None = None,
) -> list[PublicEventSliderResponse]:
    """Return at most twelve upcoming public Event covers using one database query."""
    reference_time = now or datetime.now(UTC)
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("Slider query time must be timezone-aware.")
    rows = (await session.execute(_slider_statement(reference_time))).all()
    slides: list[PublicEventSliderResponse] = []
    for sort_order, (raw_event, raw_media) in enumerate(rows[:MAX_EVENT_SLIDES]):
        event = cast(Event, raw_event)
        media = cast(EventMedia, raw_media)
        if event.start_date is None:
            raise RuntimeError("Published Event schedule is incomplete.")
        if locale == "de":
            title = _localized(event.title_de, event.title_en)
            description = _localized(event.description_de, event.description_en)
            location = _localized(event.location_de, event.location_en)
            image_alt = _localized(media.alt_de, media.alt_en)
            cta_label = "Event ansehen"
        else:
            title = _localized(event.title_en, event.title_de)
            description = _localized(event.description_en, event.description_de)
            location = _localized(event.location_en, event.location_de)
            image_alt = _localized(media.alt_en, media.alt_de)
            cta_label = "View event"
        image_url = await storage.create_signed_url(
            StorageObjectRef(ImageBucket.EVENT_MEDIA, media.object_key),
            expires_in=MAX_SIGNED_URL_SECONDS,
        )
        slides.append(
            PublicEventSliderResponse(
                id=event.id,
                title=title,
                description=_excerpt(description),
                image_url=image_url,
                image_alt=image_alt,
                event_start_at=event.start_date,
                event_end_at=event.end_date,
                location=location,
                cta=EventSliderCta(label=cta_label, href=f"/events/{event.id}"),
                sort_order=sort_order,
            )
        )
    return slides
