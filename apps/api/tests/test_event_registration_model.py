"""Contract tests for optional internal Event registrations."""

from datetime import UTC, datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID, uuid4

import pytest
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Table,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import EventRegistration, EventRegistrationStatus


def _registration(**overrides: object) -> EventRegistration:
    values: dict[str, object] = {
        "event_id": uuid4(),
        "user_id": uuid4(),
        "status": EventRegistrationStatus.REGISTERED,
    }
    values.update(overrides)
    return EventRegistration(**values)


def test_registration_status_is_separate_from_event_editorial_state() -> None:
    assert tuple(EventRegistrationStatus) == (
        EventRegistrationStatus.REGISTERED,
        EventRegistrationStatus.CANCELLED,
        EventRegistrationStatus.ATTENDED,
    )
    assert [status.value for status in EventRegistrationStatus] == [
        "registered",
        "cancelled",
        "attended",
    ]


def test_registration_belongs_to_exactly_one_event_and_user() -> None:
    table = cast(Table, EventRegistration.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "event_registrations"
    assert set(table.columns.keys()) == {
        "event_id",
        "user_id",
        "registered_at",
        "status",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert isinstance(table.c.event_id.type, Uuid)
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.event_id.nullable is False
    assert table.c.user_id.nullable is False

    foreign_keys = {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert set(foreign_keys) == {
        "fk_event_registrations_event_id_events",
        "fk_event_registrations_user_id_users",
    }
    assert foreign_keys["fk_event_registrations_event_id_events"].ondelete == "CASCADE"
    assert foreign_keys["fk_event_registrations_user_id_users"].ondelete == "CASCADE"
    assert tuple(
        element.target_fullname
        for element in foreign_keys["fk_event_registrations_event_id_events"].elements
    ) == ("app_private.events.id",)
    assert tuple(
        element.target_fullname
        for element in foreign_keys["fk_event_registrations_user_id_users"].elements
    ) == ("app_private.users.id",)


def test_registration_pair_is_unique_and_status_defaults_to_registered() -> None:
    table = cast(Table, EventRegistration.__table__)
    unique_pairs = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    status = table.c.status

    assert unique_pairs == {("event_id", "user_id")}
    assert isinstance(status.type, Enum)
    assert status.type.enum_class is EventRegistrationStatus
    assert status.type.enums == ["registered", "cancelled", "attended"]
    assert status.type.schema == APPLICATION_SCHEMA
    assert status.type.validate_strings is True
    assert cast(ColumnDefault, status.default).arg is EventRegistrationStatus.REGISTERED
    assert str(cast(DefaultClause, status.server_default).arg) == "registered"


def test_registration_timestamp_is_aware_and_immutable_by_default() -> None:
    table = cast(Table, EventRegistration.__table__)
    registered_at = table.c.registered_at

    assert isinstance(registered_at.type, DateTime)
    assert registered_at.type.timezone is True
    assert registered_at.nullable is False
    assert registered_at.default is None
    assert str(cast(DefaultClause, registered_at.server_default).arg) == "now()"
    assert registered_at.onupdate is None

    aware = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    registration = _registration(registered_at=aware)
    assert registration.registered_at is aware
    with pytest.raises(ValueError, match="timezone-aware"):
        _registration(registered_at=datetime(2026, 10, 1, 8, 0))

    annotations = get_type_hints(EventRegistration)
    assert get_args(annotations["event_id"]) == (UUID,)
    assert get_args(annotations["user_id"]) == (UUID,)
    assert get_args(annotations["registered_at"]) == (datetime,)
    assert get_args(annotations["status"]) == (EventRegistrationStatus,)


def test_active_registration_rule_excludes_cancelled_attended_and_deleted_rows() -> None:
    assert _registration().is_active is True
    assert _registration(status=EventRegistrationStatus.CANCELLED).is_active is False
    assert _registration(status=EventRegistrationStatus.ATTENDED).is_active is False
    deleted_registration = _registration(
        deleted_at=datetime(2026, 10, 1, tzinfo=UTC)
    )
    assert deleted_registration.is_active is False

    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    statement = str(
        select(EventRegistration.id)
        .where(EventRegistration.active_clause())
        .compile(dialect=dialect)
    ).lower()
    assert "event_registrations.deleted_at is null" in statement
    assert "event_registrations.status" in statement


def test_postgresql_ddl_matches_registration_contract() -> None:
    table = cast(Table, EventRegistration.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    ddl = str(CreateTable(table).compile(dialect=dialect)).lower()

    assert "create table app_private.event_registrations" in ddl
    assert "event_id uuid not null" in ddl
    assert "user_id uuid not null" in ddl
    assert "registered_at timestamp with time zone default now() not null" in ddl
    assert (
        "status app_private.event_registration_status default 'registered' not null" in ddl
    )
    assert "constraint uq_event_registrations_event_id_user_id unique (event_id, user_id)" in ddl
    assert "foreign key(event_id) references app_private.events (id) on delete cascade" in ddl
    assert "foreign key(user_id) references app_private.users (id) on delete cascade" in ddl
