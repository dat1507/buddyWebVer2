"""Filter, pagination, and projection tests for the Admin Event inventory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventPhase, EventStatus, EventVisibility
from app.services.admin_event_queries import (
    AdminEventFilters,
    AdminEventQueryValidationError,
    get_admin_event_detail,
    list_admin_events,
)

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
ADMIN_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)


def _event() -> Event:
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
        category="community",
        organizer="VGU Buddy",
        registration_url=None,
        cover_media_id=None,
        status=EventStatus.DRAFT,
        visibility=EventVisibility.MEMBERS,
        registration_enabled=False,
        max_participants=None,
        registration_deadline=None,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=None,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _compiled(statement: object) -> str:
    return str(
        cast(Any, statement).compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


@pytest.mark.anyio
async def test_admin_list_includes_drafts_with_stable_filters_and_two_queries() -> None:
    scalars_result = MagicMock()
    scalars_result.all.return_value = [_event()]
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=1)
    mock.scalars = AsyncMock(return_value=scalars_result)

    result = await list_admin_events(
        cast(AsyncSession, mock),
        filters=AdminEventFilters(
            page=2,
            page_size=5,
            search=" Buddy ",
            status=EventStatus.DRAFT,
            visibility=EventVisibility.MEMBERS,
            phase=EventPhase.UPCOMING,
            from_instant=NOW,
            to_instant=NOW + timedelta(days=31),
        ),
        now=NOW,
    )

    assert result.total == 1
    assert result.page == 2
    assert result.items[0].status is EventStatus.DRAFT
    assert result.items[0].phase is EventPhase.UPCOMING
    assert not hasattr(result.items[0], "created_by")
    mock.scalar.assert_awaited_once()
    mock.scalars.assert_awaited_once()
    sql = _compiled(mock.scalars.await_args.args[0])
    assert "events.status = 'draft'" in sql
    assert "events.visibility = 'members'" in sql
    assert "app_private.events.title_en" in sql
    assert "%%buddy%%" in sql or "%buddy%" in sql
    assert "events.start_date <" in sql
    assert "events.end_date >" in sql
    assert "order by app_private.events.updated_at desc, app_private.events.id asc" in sql


@pytest.mark.anyio
@pytest.mark.parametrize(
    "filters",
    [
        AdminEventFilters(page=0),
        AdminEventFilters(page_size=101),
        AdminEventFilters(search="   "),
        AdminEventFilters(from_instant=NOW),
        AdminEventFilters(from_instant=NOW, to_instant=NOW),
        AdminEventFilters(from_instant=NOW.replace(tzinfo=None), to_instant=NOW),
    ],
)
async def test_invalid_admin_filters_fail_before_database(filters: AdminEventFilters) -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.scalars = AsyncMock()
    with pytest.raises(AdminEventQueryValidationError):
        await list_admin_events(cast(AsyncSession, mock), filters=filters, now=NOW)
    mock.scalar.assert_not_awaited()
    mock.scalars.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_detail_returns_allowlisted_projection_or_none() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=[_event(), None])
    session = cast(AsyncSession, mock)

    detail = await get_admin_event_detail(session, EVENT_ID)
    missing = await get_admin_event_detail(session, EVENT_ID)

    assert detail is not None
    assert detail.id == EVENT_ID
    assert detail.title_en == "Buddy Day"
    assert missing is None
    assert mock.scalar.await_count == 2
