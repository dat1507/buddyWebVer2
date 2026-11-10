"""Filtering, locale, cap, mapping, and query-count tests for EVS-005."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime, timedelta
from sqlite3 import connect
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventStatus,
    EventVisibility,
)
from app.services.event_sliders import (
    MAX_EVENT_SLIDES,
    _slider_statement,
    list_public_event_sliders,
)
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
        registration_url="https://events.example.test/register",
        cover_media_id=_id(index + 100),
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.PUBLIC,
        registration_enabled=True,
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
    assert slides[0].cta is not None
    assert slides[0].cta.label == "Event ansehen"
    assert slides[0].cta.href == f"/events/{_id(1)}"
    assert slides[0].registration_url == "https://events.example.test/register"
    assert slides[0].registration_enabled is True
    assert slides[0].sort_order == 0
    session_mock.execute.assert_awaited_once()
    storage_mock.create_signed_url.assert_awaited_once()

    sql = _compiled(session_mock.execute.await_args.args[0])
    assert "join app_private.event_media" in sql
    assert "events.status = 'published'" in sql
    assert "events.visibility =" not in sql
    assert "events.visibility in" not in sql
    assert "event_media.processing_status = 'ready'" in sql
    assert "events.start_date is null" in sql
    assert "events.start_date >" in sql
    assert "events.end_date >" in sql
    assert "order by app_private.events.start_date asc nulls last, app_private.events.id asc" in sql
    assert f"limit {MAX_EVENT_SLIDES}" in sql


def test_slider_schedule_eligibility_and_end_date_extension() -> None:
    # SQLite fixtures store UTC instants in the format used by its SQLAlchemy dialect.
    def utc_value(value: str) -> str:
        return (
            datetime.fromisoformat(value)
            .astimezone(UTC)
            .replace(tzinfo=None)
            .isoformat(sep=" ", timespec="microseconds")
        )

    boundary = datetime.fromisoformat("2026-11-10T07:00:00+07:00").astimezone(UTC)
    started = utc_value("2026-11-09T07:00:00+07:00")
    ending = utc_value("2026-11-10T07:00:00+07:00")
    future = utc_value("2026-11-11T07:00:00+07:00")

    with closing(connect(":memory:")) as db:
        db.executescript("""
            ATTACH DATABASE ':memory:' AS app_private;
            CREATE TABLE app_private.events (
                id INTEGER, cover_media_id INTEGER, start_date TEXT, end_date TEXT,
                status TEXT, deleted_at TEXT, published_at TEXT
            );
            CREATE TABLE app_private.event_media (
                id INTEGER, event_id INTEGER, deleted_at TEXT, usage TEXT, processing_status TEXT
            );
        """)
        rows = [
            (1, future, None, "PUBLISHED"),
            (2, started, future, "PUBLISHED"),
            (3, started, ending, "PUBLISHED"),
            (4, started, None, "PUBLISHED"),
            (5, started, future, "DRAFT"),
            (6, started, future, "CANCELLED"),
            (7, None, ending, "PUBLISHED"),
            (8, None, None, "PUBLISHED"),
            (9, ending, None, "PUBLISHED"),
        ]
        for event_id, start, end, status in rows:
            db.execute(
                "INSERT INTO app_private.events VALUES (?, ?, ?, ?, ?, NULL, ?)",
                (event_id, event_id, start, end, status, started),
            )
            db.execute(
                "INSERT INTO app_private.event_media VALUES (?, ?, NULL, 'EVENT_COVER', 'READY')",
                (event_id, event_id),
            )

        def selected_ids(at: datetime) -> list[int]:
            statement = _slider_statement(at).with_only_columns(Event.id)
            compiled = statement.compile(
                dialect=sqlite.dialect(),
                compile_kwargs={"literal_binds": True},
            )
            return [event_id for (event_id,) in db.execute(str(compiled))]

        assert selected_ids(boundary - timedelta(microseconds=1)) == [2, 3, 9, 1, 7, 8]
        assert selected_ids(boundary) == [2, 1, 7, 8]
        assert selected_ids(boundary + timedelta(microseconds=1)) == [2, 1, 7, 8]

        db.execute("UPDATE app_private.events SET end_date = ? WHERE id = 3", (future,))
        assert selected_ids(boundary) == [2, 3, 1, 7, 8]
        db.execute("UPDATE app_private.events SET end_date = NULL WHERE id = 3")
        assert selected_ids(boundary) == [2, 1, 7, 8]


@pytest.mark.anyio
async def test_slider_api_caps_at_twelve_and_produces_bounded_english_excerpt() -> None:
    rows = [(_event(index), _media(index)) for index in range(1, MAX_EVENT_SLIDES + 2)]
    session_mock, session, storage_mock, storage = _dependencies(rows)

    slides = await list_public_event_sliders(session, storage, locale="en", now=NOW)

    assert len(slides) == MAX_EVENT_SLIDES
    assert [slide.sort_order for slide in slides] == list(range(MAX_EVENT_SLIDES))
    assert len(slides[0].description or "") == 500
    assert slides[0].description is not None and slides[0].description.endswith("...")
    assert slides[0].cta is not None
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


@pytest.mark.anyio
async def test_unscheduled_location_free_announcement_is_slider_eligible() -> None:
    event = _event()
    event.start_date = None
    event.end_date = None
    event.location_en = None
    event.location_de = None
    session_mock, session, storage_mock, storage = _dependencies([(event, _media())])

    slides = await list_public_event_sliders(session, storage, locale="en", now=NOW)

    assert len(slides) == 1
    assert slides[0].event_start_at is None
    assert slides[0].event_end_at is None
    assert slides[0].location is None
    session_mock.execute.assert_awaited_once()
    storage_mock.create_signed_url.assert_awaited_once()


@pytest.mark.anyio
async def test_slider_returns_scheduled_field_trip_and_unscheduled_buddy_recruitment() -> None:
    field_trip = _event(1)
    field_trip.title_en = "Field trip"
    field_trip.title_de = "Ausflug"
    recruitment = _event(2)
    recruitment.title_en = "Buddy Recruitment"
    recruitment.title_de = "Buddy-Rekrutierung"
    recruitment.start_date = None
    recruitment.end_date = None
    recruitment.location_en = None
    recruitment.location_de = None
    recruitment.visibility = EventVisibility.MEMBERS
    session_mock, session, storage_mock, storage = _dependencies(
        [(field_trip, _media(1)), (recruitment, _media(2))]
    )

    slides = await list_public_event_sliders(session, storage, locale="en", now=NOW)

    assert [slide.title for slide in slides] == ["Field trip", "Buddy Recruitment"]
    assert [slide.sort_order for slide in slides] == [0, 1]
    assert slides[1].event_start_at is None
    assert slides[1].location is None
    session_mock.execute.assert_awaited_once()
    assert storage_mock.create_signed_url.await_count == 2

    de_session_mock, de_session, de_storage_mock, de_storage = _dependencies(
        [(field_trip, _media(1)), (recruitment, _media(2))]
    )
    german_slides = await list_public_event_sliders(de_session, de_storage, locale="de", now=NOW)

    assert [slide.title for slide in german_slides] == ["Ausflug", "Buddy-Rekrutierung"]
    assert german_slides[1].event_start_at is None
    assert german_slides[1].location is None
    de_session_mock.execute.assert_awaited_once()
    assert de_storage_mock.create_signed_url.await_count == 2
