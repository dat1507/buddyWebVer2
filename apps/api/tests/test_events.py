"""Unit tests for transactional EVT-004 Event lifecycle services."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventStatus, EventVisibility, User, UserRole
from app.schemas.event import EventDraftCreate, EventDraftUpdate, EventStatusUpdate
from app.services.events import (
    EventAccessError,
    EventDeletionPlan,
    EventDependencyConflictError,
    EventRelations,
    EventValidationError,
    EventVersionConflictError,
    cleanup_deleted_event_media,
    create_event_draft,
    delete_event,
    get_event,
    set_event_status,
    update_event_draft,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
EVENT_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
COVER_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
PUBLISHED_AT = datetime(2026, 9, 1, tzinfo=UTC)
START = datetime(2026, 10, 1, 8, tzinfo=UTC)
END = datetime(2026, 10, 1, 10, tzinfo=UTC)


class StubRelations:
    def __init__(self, boundary: datetime | None = None) -> None:
        self.boundary = boundary
        self.detached: list[UUID] = []

    async def published_recap_boundary(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> datetime | None:
        del session, event_id
        return self.boundary

    async def detach_for_delete(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> None:
        del session
        self.detached.append(event_id)


def _admin(*, role: UserRole = UserRole.ADMIN, active: bool = True) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.invalid",
        password_hash="test-only-hash",
        role=role,
        is_active=active,
        email_verified=True,
    )


def _event(
    *,
    status: EventStatus = EventStatus.DRAFT,
    version: int = 2,
    complete: bool = True,
) -> Event:
    return Event(
        id=EVENT_ID,
        title_en="Welcome" if complete else None,
        title_de="Willkommen" if complete else None,
        description_en="Description" if complete else None,
        description_de="Beschreibung" if complete else None,
        start_date=START if complete else None,
        end_date=END if complete else None,
        location_en="Campus" if complete else None,
        location_de="Campus" if complete else None,
        cover_media_id=COVER_ID if complete else None,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        status=status,
        visibility=EventVisibility.MEMBERS,
        registration_enabled=False,
        published_at=PUBLISHED_AT if status is not EventStatus.DRAFT else None,
        version=version,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.scalars = AsyncMock()
    mock.flush = AsyncMock()
    mock.delete = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _compiled(statement: object) -> str:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    return str(statement.compile(dialect=dialect))  # type: ignore[attr-defined]


@pytest.mark.anyio
async def test_create_incomplete_draft_derives_actor_and_never_commits() -> None:
    mock, session = _session()

    event = await create_event_draft(session, _admin(), EventDraftCreate.model_validate({}))

    assert event.status is EventStatus.DRAFT
    assert event.title_en is None
    assert event.created_by == ADMIN_ID
    assert event.updated_by == ADMIN_ID
    assert event.version == 1
    mock.add.assert_called_once_with(event)
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_non_admin_is_rejected_before_database_access() -> None:
    mock, session = _session()

    with pytest.raises(EventAccessError, match="current active Admin"):
        await create_event_draft(
            session,
            _admin(role=UserRole.USER),
            EventDraftCreate.model_validate({}),
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_get_event_excludes_deleted_rows() -> None:
    event = _event()
    mock, session = _session()
    mock.scalar.return_value = event

    assert await get_event(session, EVENT_ID) is event

    sql = _compiled(mock.scalar.await_args.args[0])
    assert "events.deleted_at IS NULL" in sql
    assert "FOR UPDATE" not in sql.upper()


@pytest.mark.anyio
async def test_partial_draft_update_locks_checks_version_and_retains_omitted_fields() -> None:
    event = _event(complete=False, version=4)
    mock, session = _session()
    mock.scalar.return_value = event
    update = EventDraftUpdate.model_validate({"version": 4, "title_en": " Updated "})

    result = await update_event_draft(session, _admin(), EVENT_ID, update)

    assert result is event
    assert event.title_en == "Updated"
    assert event.title_de is None
    assert event.version == 5
    assert event.updated_by == ADMIN_ID
    assert "FOR UPDATE" in _compiled(mock.scalar.await_args.args[0]).upper()
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_stale_update_fails_before_mutation() -> None:
    event = _event(version=5)
    mock, session = _session()
    mock.scalar.return_value = event

    with pytest.raises(EventVersionConflictError, match="stale"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate({"version": 4, "title_en": "Changed"}),
        )

    assert event.title_en == "Welcome"
    assert event.version == 5
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_merged_schedule_and_registration_deadline_are_validated() -> None:
    event = _event(version=2)
    mock, session = _session()
    mock.scalar.return_value = event

    with pytest.raises(EventValidationError, match="later than start"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate({"version": 2, "start_date": "2026-10-01T11:00:00Z"}),
        )

    with pytest.raises(EventValidationError, match="deadline"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate(
                {"version": 2, "registration_deadline": "2026-10-01T09:00:00Z"}
            ),
        )
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_cover_update_requires_ready_event_cover_owned_by_event() -> None:
    event = _event(complete=False, version=2)
    mock, session = _session()
    mock.scalar.side_effect = [event, None]

    with pytest.raises(EventValidationError, match="cover is invalid"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate({"version": 2, "cover_media_id": str(COVER_ID)}),
        )

    cover_sql = _compiled(mock.scalar.await_args_list[1].args[0])
    assert "event_media.event_id" in cover_sql
    assert "event_media.usage" in cover_sql
    assert "event_media.processing_status" in cover_sql
    assert "event_media.deleted_at IS NULL" in cover_sql
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_publish_requires_complete_localized_content_times_location_and_ready_cover() -> None:
    incomplete = _event(complete=False, version=2)
    mock, session = _session()
    mock.scalar.return_value = incomplete

    with pytest.raises(EventValidationError, match="incomplete"):
        await set_event_status(
            session,
            _admin(),
            EVENT_ID,
            EventStatusUpdate(version=2, status=EventStatus.PUBLISHED),
        )

    complete = _event(complete=True, version=2)
    mock.scalar.side_effect = [complete, COVER_ID]
    published = await set_event_status(
        session,
        _admin(),
        EVENT_ID,
        EventStatusUpdate(version=2, status=EventStatus.PUBLISHED),
        now=datetime(2026, 9, 22, tzinfo=UTC),
    )

    assert published.status is EventStatus.PUBLISHED
    assert published.published_at == datetime(2026, 9, 22, tzinfo=UTC)
    assert published.version == 3
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_unpublish_and_cancel_keep_first_publication_history() -> None:
    event = _event(status=EventStatus.PUBLISHED, version=7)
    mock, session = _session()
    mock.scalar.return_value = event

    result = await set_event_status(
        session,
        _admin(),
        EVENT_ID,
        EventStatusUpdate(version=7, status=EventStatus.CANCELLED),
    )

    assert result.status is EventStatus.CANCELLED
    assert result.published_at is PUBLISHED_AT
    assert result.version == 8

    mock.scalar.return_value = event
    result = await set_event_status(
        session,
        _admin(),
        EVENT_ID,
        EventStatusUpdate(version=8, status=EventStatus.DRAFT),
    )
    assert result.status is EventStatus.DRAFT
    assert result.published_at is PUBLISHED_AT
    assert result.version == 9


@pytest.mark.anyio
async def test_published_event_update_cannot_clear_required_content() -> None:
    event = _event(status=EventStatus.PUBLISHED, version=2)
    mock, session = _session()
    mock.scalar.return_value = event

    with pytest.raises(EventValidationError, match="incomplete"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate({"version": 2, "title_en": None}),
        )

    assert event.title_en == "Welcome"
    assert event.version == 2


@pytest.mark.anyio
async def test_schedule_cannot_move_beyond_published_recap_boundary() -> None:
    event = _event(version=2)
    mock, session = _session()
    mock.scalar.return_value = event
    relations = StubRelations(boundary=END)

    with pytest.raises(EventDependencyConflictError, match="Unpublish"):
        await update_event_draft(
            session,
            _admin(),
            EVENT_ID,
            EventDraftUpdate.model_validate({"version": 2, "end_date": "2026-10-01T11:00:00Z"}),
            relations=cast(EventRelations, relations),
        )

    assert event.end_date == END
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_rejects_published_recap_or_active_registration() -> None:
    event = _event(version=3)
    mock, session = _session()
    mock.scalar.return_value = event

    with pytest.raises(EventDependencyConflictError, match="recap"):
        await delete_event(
            session,
            _admin(),
            EVENT_ID,
            version=3,
            relations=cast(EventRelations, StubRelations(boundary=PUBLISHED_AT)),
        )

    mock.scalar.side_effect = [event, uuid4()]
    with pytest.raises(EventDependencyConflictError, match="registrations"):
        await delete_event(session, _admin(), EVENT_ID, version=3)

    mock.delete.assert_not_awaited()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_eligible_delete_detaches_relations_and_returns_post_commit_media_plan() -> None:
    event = _event(version=3)
    first_key = f"{uuid4()}.webp"
    second_key = f"{uuid4()}.jpg"
    mock, session = _session()
    mock.scalar.side_effect = [event, None]
    media_result = MagicMock()
    media_result.all.return_value = [first_key, second_key]
    mock.scalars.return_value = media_result
    relations = StubRelations()

    plan = await delete_event(
        session,
        _admin(),
        EVENT_ID,
        version=3,
        relations=cast(EventRelations, relations),
    )

    assert event.cover_media_id is None
    assert relations.detached == [EVENT_ID]
    assert [reference.object_key for reference in plan.media] == [first_key, second_key]
    assert all(reference.bucket is ImageBucket.EVENT_MEDIA for reference in plan.media)
    mock.delete.assert_awaited_once_with(event)
    assert mock.flush.await_count == 2
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_post_commit_media_cleanup_returns_only_retryable_failures() -> None:
    first = StorageObjectRef(ImageBucket.EVENT_MEDIA, f"{uuid4()}.webp")
    second = StorageObjectRef(ImageBucket.EVENT_MEDIA, f"{uuid4()}.jpg")
    plan = EventDeletionPlan(event_id=EVENT_ID, media=(first, second))
    storage = MagicMock(spec=ImageStorageService)
    storage.delete_image = AsyncMock(
        side_effect=[None, StorageOperationError("temporary cleanup failure")]
    )

    failed = await cleanup_deleted_event_media(storage, plan)

    assert failed == (second,)
    assert storage.delete_image.await_count == 2
