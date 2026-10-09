"""Audience, filtering, projection, and query-count tests for EVT-005."""

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
    EventPhase,
    EventStatus,
    EventVisibility,
    User,
    UserRole,
)
from app.services.event_queries import (
    EventQueryValidationError,
    PublicEventFilters,
    get_public_event_detail,
    list_public_events,
)
from app.services.image_storage import ImageStorageService

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
MEDIA_ID = UUID("22222222-2222-4222-8222-222222222222")
ADMIN_ID = UUID("33333333-3333-4333-8333-333333333333")
USER_ID = UUID("44444444-4444-4444-8444-444444444444")
OBJECT_KEY = "55555555-5555-4555-8555-555555555555.webp"
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


def _event(*, visibility: EventVisibility = EventVisibility.PUBLIC) -> Event:
    return Event(
        id=EVENT_ID,
        title_en="Buddy Day",
        title_de="Buddy-Tag",
        description_en="Meet your Buddy community.",
        description_de="Triff deine Buddy-Community.",
        start_date=NOW + timedelta(days=1),
        end_date=NOW + timedelta(days=1, hours=2),
        timezone="Asia/Ho_Chi_Minh",
        location_en="VGU Campus",
        location_de="VGU-Campus",
        category="community",
        organizer="VGU Buddy",
        registration_url="https://example.com/register",
        cover_media_id=MEDIA_ID,
        status=EventStatus.PUBLISHED,
        visibility=visibility,
        registration_enabled=True,
        max_participants=100,
        registration_deadline=NOW + timedelta(hours=12),
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=NOW - timedelta(days=1),
        version=1,
        deleted_at=None,
    )


def _media() -> EventMedia:
    return EventMedia(
        id=MEDIA_ID,
        event_id=EVENT_ID,
        bucket="event-media",
        object_key=OBJECT_KEY,
        usage=EventMediaUsage.EVENT_COVER,
        alt_en="Students at Buddy Day",
        alt_de="Studierende beim Buddy-Tag",
        mime_type="image/webp",
        byte_size=1024,
        width=1600,
        height=900,
        sort_order=0,
        processing_status=EventMediaProcessingStatus.READY,
        created_by=ADMIN_ID,
        deleted_at=None,
    )


def _viewer(*, verified: bool = True) -> User:
    return User(
        id=USER_ID,
        email="member@example.com",
        password_hash="test-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
        deleted_at=None,
    )


def _storage() -> tuple[MagicMock, ImageStorageService]:
    mock = MagicMock(spec=ImageStorageService)
    mock.create_signed_url = AsyncMock(return_value="https://storage.example.test/signed-cover")
    return mock, cast(ImageStorageService, mock)


def _list_session(
    rows: list[tuple[Event, EventMedia | None]],
) -> tuple[MagicMock, AsyncSession]:
    result = MagicMock()
    result.all.return_value = rows
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=len(rows))
    mock.execute = AsyncMock(return_value=result)
    return mock, cast(AsyncSession, mock)


def _compiled(statement: object) -> str:
    return str(
        cast(Any, statement).compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


@pytest.mark.anyio
async def test_public_list_localizes_cover_and_uses_constant_query_count() -> None:
    event = _event()
    media = _media()
    session_mock, session = _list_session([(event, media), (event, media)])
    storage_mock, storage = _storage()

    result = await list_public_events(
        session,
        storage,
        viewer=None,
        filters=PublicEventFilters(locale="de", page=1, page_size=20),
        now=NOW,
    )

    assert result.total == 2
    assert result.total_pages == 1
    assert result.items[0].title == "Buddy-Tag"
    assert result.items[0].description == "Triff deine Buddy-Community."
    assert result.items[0].location == "VGU-Campus"
    assert result.items[0].phase is EventPhase.UPCOMING
    assert result.items[0].cover is not None
    assert result.items[0].cover.alt_text == "Studierende beim Buddy-Tag"
    assert result.items[0].cover.url == "https://storage.example.test/signed-cover"
    session_mock.scalar.assert_awaited_once()
    session_mock.execute.assert_awaited_once()
    assert storage_mock.create_signed_url.await_count == 2

    sql = _compiled(session_mock.execute.await_args.args[0])
    assert "event_visibility.public" not in sql
    assert "'public'" in sql
    assert "'members'" not in sql
    assert "order by app_private.events.start_date asc, app_private.events.id asc" in sql
    assert "event_media.object_key" in sql


@pytest.mark.anyio
async def test_verified_member_query_includes_members_but_unverified_user_does_not() -> None:
    for viewer, includes_members in ((_viewer(), True), (_viewer(verified=False), False)):
        session_mock, session = _list_session([])
        _, storage = _storage()
        await list_public_events(
            session,
            storage,
            viewer=viewer,
            filters=PublicEventFilters(),
            now=NOW,
        )
        sql = _compiled(session_mock.execute.await_args.args[0])
        assert ("'members'" in sql) is includes_members


@pytest.mark.anyio
async def test_half_open_range_and_phase_filters_are_applied_once() -> None:
    session_mock, session = _list_session([])
    _, storage = _storage()
    await list_public_events(
        session,
        storage,
        viewer=None,
        filters=PublicEventFilters(
            phase=EventPhase.ONGOING,
            from_instant=NOW,
            to_instant=NOW + timedelta(days=31),
            category=" community ",
        ),
        now=NOW,
    )

    sql = _compiled(session_mock.execute.await_args.args[0])
    assert "events.start_date <" in sql
    assert "events.end_date >" in sql
    assert "events.start_date <=" in sql
    assert "events.category = 'community'" in sql


@pytest.mark.anyio
@pytest.mark.parametrize(
    "filters",
    [
        PublicEventFilters(from_instant=NOW),
        PublicEventFilters(from_instant=NOW, to_instant=NOW),
        PublicEventFilters(from_instant=NOW, to_instant=NOW + timedelta(days=94)),
        PublicEventFilters(from_instant=NOW.replace(tzinfo=None), to_instant=NOW),
        PublicEventFilters(category="   "),
        PublicEventFilters(page_size=101),
    ],
)
async def test_invalid_queries_fail_before_database_or_storage(
    filters: PublicEventFilters,
) -> None:
    session_mock, session = _list_session([])
    storage_mock, storage = _storage()
    with pytest.raises(EventQueryValidationError):
        await list_public_events(
            session,
            storage,
            viewer=None,
            filters=filters,
            now=NOW,
        )
    session_mock.scalar.assert_not_awaited()
    session_mock.execute.assert_not_awaited()
    storage_mock.create_signed_url.assert_not_awaited()


@pytest.mark.anyio
async def test_detail_returns_none_for_hidden_or_unknown_row_without_storage_access() -> None:
    result = MagicMock()
    result.one_or_none.return_value = None
    session_mock = MagicMock(spec=AsyncSession)
    session_mock.execute = AsyncMock(return_value=result)
    storage_mock, storage = _storage()

    detail = await get_public_event_detail(
        cast(AsyncSession, session_mock),
        storage,
        EVENT_ID,
        viewer=None,
        locale="en",
        now=NOW,
    )

    assert detail is None
    session_mock.execute.assert_awaited_once()
    storage_mock.create_signed_url.assert_not_awaited()
    sql = _compiled(session_mock.execute.await_args.args[0])
    assert "events.id =" in sql
    assert "'public'" in sql
    assert "events.deleted_at is null" in sql
