"""Contract tests for Event editorial state, schedule and audience visibility."""

from datetime import UTC, datetime, timedelta
from typing import cast, get_args, get_type_hints
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    Table,
    Text,
    Uuid,
    select,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import (
    Event,
    EventPhase,
    EventStatus,
    EventVisibility,
    derive_event_phase,
)


def _constraint_names(table: Table) -> set[str]:
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _event(**overrides: object) -> Event:
    owner_id = uuid4()
    values: dict[str, object] = {
        "created_by": owner_id,
        "updated_by": owner_id,
        "status": EventStatus.DRAFT,
        "visibility": EventVisibility.MEMBERS,
    }
    values.update(overrides)
    return Event(**values)


def test_event_enums_separate_editorial_state_visibility_and_derived_phase() -> None:
    assert tuple(EventStatus) == (
        EventStatus.DRAFT,
        EventStatus.PUBLISHED,
        EventStatus.CANCELLED,
    )
    assert tuple(EventVisibility) == (EventVisibility.PUBLIC, EventVisibility.MEMBERS)
    assert tuple(EventPhase) == (
        EventPhase.UPCOMING,
        EventPhase.ONGOING,
        EventPhase.COMPLETED,
    )


def test_event_table_covers_part_7_without_persisting_phase() -> None:
    table = cast(Table, Event.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "events"
    assert set(table.columns.keys()) == {
        "title_en",
        "title_de",
        "description_en",
        "description_de",
        "start_date",
        "end_date",
        "timezone",
        "location_en",
        "location_de",
        "category",
        "organizer",
        "registration_url",
        "cover_media_id",
        "status",
        "visibility",
        "registration_enabled",
        "max_participants",
        "registration_deadline",
        "created_by",
        "updated_by",
        "published_at",
        "version",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert "phase" not in table.columns
    assert all(
        isinstance(table.c[name].type, Text)
        for name in (
            "title_en",
            "title_de",
            "description_en",
            "description_de",
            "timezone",
            "location_en",
            "location_de",
            "category",
            "organizer",
            "registration_url",
        )
    )
    assert isinstance(table.c.cover_media_id.type, Uuid)
    assert table.c.cover_media_id.nullable is True
    assert len(table.c.cover_media_id.foreign_keys) == 1


def test_event_draft_fields_are_nullable_but_supplied_content_is_bounded() -> None:
    table = cast(Table, Event.__table__)
    nullable_draft_fields = {
        "title_en",
        "title_de",
        "description_en",
        "description_de",
        "start_date",
        "end_date",
        "location_en",
        "location_de",
        "category",
        "organizer",
        "registration_url",
        "cover_media_id",
        "max_participants",
        "registration_deadline",
        "published_at",
    }

    assert all(table.c[name].nullable for name in nullable_draft_fields)
    assert _constraint_names(table) == {
        "ck_events_title_en_length",
        "ck_events_title_de_length",
        "ck_events_description_en_length",
        "ck_events_description_de_length",
        "ck_events_date_order",
        "ck_events_timezone_length",
        "ck_events_location_en_length",
        "ck_events_location_de_length",
        "ck_events_category_length",
        "ck_events_organizer_length",
        "ck_events_registration_url_https",
        "ck_events_max_participants_positive",
        "ck_events_version_positive",
    }


def test_event_state_defaults_are_private_and_registration_independent() -> None:
    table = cast(Table, Event.__table__)
    status = table.c.status
    visibility = table.c.visibility
    registration_enabled = table.c.registration_enabled
    version = table.c.version

    assert isinstance(status.type, Enum)
    assert status.type.enum_class is EventStatus
    assert status.type.enums == ["DRAFT", "PUBLISHED", "CANCELLED"]
    assert status.type.schema == APPLICATION_SCHEMA
    assert cast(ColumnDefault, status.default).arg is EventStatus.DRAFT
    assert str(cast(DefaultClause, status.server_default).arg) == "DRAFT"

    assert isinstance(visibility.type, Enum)
    assert visibility.type.enum_class is EventVisibility
    assert visibility.type.enums == ["PUBLIC", "MEMBERS"]
    assert visibility.type.schema == APPLICATION_SCHEMA
    assert cast(ColumnDefault, visibility.default).arg is EventVisibility.MEMBERS
    assert str(cast(DefaultClause, visibility.server_default).arg) == "MEMBERS"

    assert isinstance(registration_enabled.type, Boolean)
    assert cast(ColumnDefault, registration_enabled.default).arg is False
    assert str(cast(DefaultClause, registration_enabled.server_default).arg) == "false"
    assert isinstance(table.c.max_participants.type, Integer)
    assert cast(ColumnDefault, version.default).arg == 1
    assert str(cast(DefaultClause, version.server_default).arg) == "1"


def test_event_uses_aware_schedule_fields_text_locations_and_user_attribution() -> None:
    table = cast(Table, Event.__table__)

    for name in ("start_date", "end_date", "registration_deadline", "published_at"):
        column = table.c[name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True

    assert table.c.timezone.nullable is False
    assert cast(ColumnDefault, table.c.timezone.default).arg == "Asia/Ho_Chi_Minh"
    assert str(cast(DefaultClause, table.c.timezone.server_default).arg) == (
        "'Asia/Ho_Chi_Minh'"
    )

    foreign_keys = {
        tuple(column.name for column in constraint.columns): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert set(foreign_keys) == {
        ("cover_media_id", "id"),
        ("created_by",),
        ("updated_by",),
    }
    cover_reference = foreign_keys[("cover_media_id", "id")]
    assert cover_reference.ondelete == "RESTRICT"
    assert cover_reference.use_alter is True
    assert tuple(element.target_fullname for element in cover_reference.elements) == (
        "app_private.event_media.id",
        "app_private.event_media.event_id",
    )
    for columns in (("created_by",), ("updated_by",)):
        constraint = foreign_keys[columns]
        assert constraint.ondelete == "RESTRICT"
        assert tuple(element.target_fullname for element in constraint.elements) == (
            "app_private.users.id",
        )

    assert {index.name for index in table.indexes} == {
        "ix_events_start_date",
        "ix_events_status",
    }

    annotations = get_type_hints(Event)
    assert get_args(annotations["start_date"]) == (datetime | None,)
    assert get_args(annotations["created_by"]) == (UUID,)
    assert get_args(annotations["status"]) == (EventStatus,)
    assert get_args(annotations["visibility"]) == (EventVisibility,)


def test_event_field_validators_require_iana_timezone_aware_instants_and_https() -> None:
    event = _event(
        timezone="  Europe/Berlin  ",
        registration_url="  https://events.example/register?id=1  ",
    )
    assert event.timezone == "Europe/Berlin"
    assert event.registration_url == "https://events.example/register?id=1"

    with pytest.raises(ValueError, match="valid IANA timezone"):
        _event(timezone="Mars/Olympus")
    with pytest.raises(ValueError, match="timezone-aware"):
        _event(start_date=datetime(2026, 10, 1, 12, 0))
    with pytest.raises(ValueError, match="absolute HTTPS"):
        _event(registration_url="http://events.example/register")
    with pytest.raises(ValueError, match="absolute HTTPS"):
        _event(registration_url="/register")


def test_event_phase_is_derived_with_half_open_boundaries_and_offset_instants() -> None:
    start = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    end = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    event = _event(start_date=start, end_date=end)

    assert event.phase_at(start - timedelta(microseconds=1)) is EventPhase.UPCOMING
    assert event.phase_at(start) is EventPhase.ONGOING
    assert event.phase_at(end - timedelta(microseconds=1)) is EventPhase.ONGOING
    assert event.phase_at(end) is EventPhase.COMPLETED
    assert derive_event_phase(start, end, at=datetime(2026, 10, 1, 9, 0, tzinfo=UTC)) is (
        EventPhase.ONGOING
    )

    incomplete = _event(start_date=start)
    assert incomplete.phase_at(start) is None
    with pytest.raises(ValueError, match="later than start"):
        derive_event_phase(start, start, at=start)
    with pytest.raises(ValueError, match="timezone-aware"):
        derive_event_phase(start, end, at=datetime(2026, 10, 1, 9, 0))


def test_public_visibility_requires_published_history_public_audience_and_live_row() -> None:
    published_at = datetime(2026, 9, 1, tzinfo=UTC)
    visible = _event(
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.PUBLIC,
        published_at=published_at,
    )
    assert visible.is_publicly_visible() is True

    visible.status = EventStatus.CANCELLED
    assert visible.is_publicly_visible() is True
    visible.published_at = None
    assert visible.is_publicly_visible() is False
    visible.published_at = published_at
    visible.status = EventStatus.DRAFT
    assert visible.is_publicly_visible() is False
    visible.status = EventStatus.PUBLISHED
    visible.visibility = EventVisibility.MEMBERS
    assert visible.is_publicly_visible() is False
    visible.visibility = EventVisibility.PUBLIC
    visible.deleted_at = published_at
    assert visible.is_publicly_visible() is False

    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    statement = str(
        select(Event.id).where(Event.public_listing_clause()).compile(dialect=dialect)
    ).lower()
    assert "events.deleted_at is null" in statement
    assert "events.published_at is not null" in statement
    assert "events.visibility" in statement
    assert "events.status in" in statement


def test_postgresql_ddl_matches_event_contract() -> None:
    table = cast(Table, Event.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    ddl = str(CreateTable(table).compile(dialect=dialect)).lower()

    assert "create table app_private.events" in ddl
    assert "start_date timestamp with time zone" in ddl
    assert "end_date timestamp with time zone" in ddl
    assert "timezone text default 'asia/ho_chi_minh' not null" in ddl
    assert "status app_private.event_status default 'draft' not null" in ddl
    assert "visibility app_private.event_visibility default 'members' not null" in ddl
    assert "registration_enabled boolean default false not null" in ddl
    assert "constraint ck_events_date_order" in ddl
    assert "constraint ck_events_registration_url_https" in ddl
    assert ddl.count("references app_private.users (id) on delete restrict") == 2
    assert "phase" not in ddl
