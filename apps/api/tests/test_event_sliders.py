"""Filtering, locale, cap, mapping, and query-count tests for EVS-005."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventStatus,
    EventVisibility,
)
from app.services.event_sliders import MAX_EVENT_SLIDES, list_public_event_sliders
from app.services.image_storage import ImageStorageService

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


def _id(index: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{index:012x}")


def _event(index: int = 1) -> Event:
    return Event(
        id=_id(index),
        title_en=f"Event {index}",
        title_de=f"Veranstaltung {index}",
        description_en="E" * 600,
        description_de=f"Beschreibung {index}",
        start_date=NOW + timedelta(days=index),
        end_date=NOW + timedelta(days=index, hours=2),
        timezone="Asia/Ho_Chi_Minh",
        location_en="VGU Campus",
        location_de="VGU-Campus",
        category="community",
        organizer="VGU Buddy",
        registration_url=None,
        cover_media_id=_id(index + 100),
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.PUBLIC,
        registration_enabled=False,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=NOW - timedelta(days=1),
        version=1,
        deleted_at=None,
    )


def _media(index: int = 1) -> EventMedia:
    return EventMedia(
        id=_id(index + 100),
        event_id=_id(index),
        bucket="event-media",
        object_key=f"00000000-0000-4000-8000-{index + 200:012x}.webp",
        usage=EventMediaUsage.EVENT_COVER,
        alt_en=f"Event {index} poster",
        alt_de=f"Plakat {index}",
        mime_type="image/webp",
        byte_size=1024,
        width=1600,
        height=900,
        sort_order=0,
        processing_status=EventMediaProcessingStatus.READY,
        created_by=ADMIN_ID,
        deleted_at=None,
    )


def _dependencies(
    rows: list[tuple[Event, EventMedia]],
) -> tuple[MagicMock, AsyncSession, MagicMock, ImageStorageService]:
    result = MagicMock()
    result.all.return_value = rows
    session_mock = MagicMock(spec=AsyncSession)
    session_mock.execute = AsyncMock(return_value=result)
    storage_mock = MagicMock(spec=ImageStorageService)
    storage_mock.create_signed_url = AsyncMock(
        return_value="https://storage.example.test/signed-cover"
    )
    return (
        session_mock,
        cast(AsyncSession, session_mock),
        storage_mock,
        cast(ImageStorageService, storage_mock),
    )


def _compiled(statement: object) -> str:
    return str(
        cast(Any, statement).compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


@pytest.mark.anyio
async def test_slider_projection_localizes_maps_cta_and_uses_one_bounded_query() -> None:
    session_mock, session, storage_mock, storage = _dependencies([(_event(), _media())])

    slides = await list_public_event_sliders(
        session,
        storage,
        locale="de",
        now=NOW,
    )

    assert len(slides) == 1
    assert slides[0].title == "Veranstaltung 1"
    assert slides[0].description == "Beschreibung 1"
    assert slides[0].image_alt == "Plakat 1"
    assert slides[0].location == "VGU-Campus"
    assert slides[0].cta.label == "Event ansehen"
    assert slides[0].cta.href == f"/events/{_id(1)}"
    assert slides[0].sort_order == 0
    session_mock.execute.assert_awaited_once()
    storage_mock.create_signed_url.assert_awaited_once()

    sql = _compiled(session_mock.execute.await_args.args[0])
    assert "join app_private.event_media" in sql
    assert "events.status = 'published'" in sql
    assert "events.visibility = 'public'" in sql
    assert "event_media.processing_status = 'ready'" in sql
    assert "events.start_date >=" in sql
    assert "order by app_private.events.start_date asc, app_private.events.id asc" in sql
    assert f"limit {MAX_EVENT_SLIDES}" in sql


@pytest.mark.anyio
async def test_slider_caps_at_twelve_and_produces_bounded_english_excerpt() -> None:
    rows = [(_event(index), _media(index)) for index in range(1, MAX_EVENT_SLIDES + 2)]
    session_mock, session, storage_mock, storage = _dependencies(rows)

    slides = await list_public_event_sliders(session, storage, locale="en", now=NOW)

    assert len(slides) == MAX_EVENT_SLIDES
    assert [slide.sort_order for slide in slides] == list(range(MAX_EVENT_SLIDES))
    assert len(slides[0].description or "") == 500
    assert slides[0].description is not None and slides[0].description.endswith("...")
    assert slides[0].cta.label == "View event"
    assert storage_mock.create_signed_url.await_count == MAX_EVENT_SLIDES
    session_mock.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_slider_empty_result_is_empty_without_storage_calls() -> None:
    session_mock, session, storage_mock, storage = _dependencies([])

    slides = await list_public_event_sliders(session, storage, locale="en", now=NOW)

    assert slides == []
    session_mock.execute.assert_awaited_once()
    storage_mock.create_signed_url.assert_not_awaited()
