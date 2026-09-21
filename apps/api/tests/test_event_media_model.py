"""Contract tests for private Event-owned media metadata."""

from datetime import UTC, datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import EventMedia, EventMediaProcessingStatus, EventMediaUsage


def _check_names(table: Table) -> set[str]:
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _media(**overrides: object) -> EventMedia:
    values: dict[str, object] = {
        "event_id": uuid4(),
        "object_key": f"{uuid4()}.webp",
        "usage": EventMediaUsage.EVENT_COVER,
        "alt_en": "Event poster",
        "alt_de": "Veranstaltungsplakat",
        "mime_type": "image/webp",
        "byte_size": 1024,
        "width": 800,
        "height": 600,
        "created_by": uuid4(),
        "processing_status": EventMediaProcessingStatus.READY,
    }
    values.update(overrides)
    return EventMedia(**values)


def test_event_media_enums_cover_event_and_recap_lifecycle() -> None:
    assert tuple(EventMediaUsage) == (
        EventMediaUsage.EVENT_COVER,
        EventMediaUsage.RECAP_COVER,
        EventMediaUsage.RECAP_GALLERY,
    )
    assert tuple(EventMediaProcessingStatus) == (
        EventMediaProcessingStatus.READY,
        EventMediaProcessingStatus.FAILED,
    )


def test_event_media_belongs_to_one_event_and_records_creator() -> None:
    table = cast(Table, EventMedia.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "event_media"
    assert set(table.columns.keys()) == {
        "event_id",
        "bucket",
        "object_key",
        "usage",
        "alt_en",
        "alt_de",
        "mime_type",
        "byte_size",
        "width",
        "height",
        "sort_order",
        "processing_status",
        "created_by",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert {"url", "signed_url", "public_url"}.isdisjoint(table.columns.keys())
    assert isinstance(table.c.event_id.type, Uuid)
    assert isinstance(table.c.created_by.type, Uuid)

    foreign_keys = {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert set(foreign_keys) == {
        "fk_event_media_event_id_events",
        "fk_event_media_created_by_users",
    }
    assert foreign_keys["fk_event_media_event_id_events"].ondelete == "CASCADE"
    assert foreign_keys["fk_event_media_created_by_users"].ondelete == "RESTRICT"
    assert tuple(
        element.target_fullname
        for element in foreign_keys["fk_event_media_event_id_events"].elements
    ) == ("app_private.events.id",)
    assert tuple(
        element.target_fullname
        for element in foreign_keys["fk_event_media_created_by_users"].elements
    ) == ("app_private.users.id",)


def test_event_media_uses_fixed_private_bucket_and_unique_object_key() -> None:
    table = cast(Table, EventMedia.__table__)
    bucket = table.c.bucket
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert isinstance(bucket.type, Text)
    assert cast(ColumnDefault, bucket.default).arg == "event-media"
    assert str(cast(DefaultClause, bucket.server_default).arg) == "'event-media'"
    assert isinstance(table.c.object_key.type, Text)
    assert unique_columns == {("object_key",), ("id", "event_id")}
    assert {index.name for index in table.indexes} == {
        "ix_event_media_event_id_usage_sort_order"
    }


def test_event_media_metadata_is_bounded_for_shared_image_storage() -> None:
    table = cast(Table, EventMedia.__table__)

    assert all(
        isinstance(table.c[name].type, Text)
        for name in ("alt_en", "alt_de", "mime_type")
    )
    assert all(
        isinstance(table.c[name].type, Integer)
        for name in ("byte_size", "width", "height", "sort_order")
    )
    assert _check_names(table) == {
        "ck_event_media_event_bucket",
        "ck_event_media_alt_en_length",
        "ck_event_media_alt_de_length",
        "ck_event_media_mime_type",
        "ck_event_media_byte_size_range",
        "ck_event_media_dimensions",
        "ck_event_media_sort_order_nonnegative",
    }
    assert cast(ColumnDefault, table.c.sort_order.default).arg == 0
    assert str(cast(DefaultClause, table.c.sort_order.server_default).arg) == "0"


def test_event_media_usage_and_processing_state_are_explicit() -> None:
    table = cast(Table, EventMedia.__table__)
    usage = table.c.usage
    processing_status = table.c.processing_status

    assert isinstance(usage.type, Enum)
    assert usage.type.enum_class is EventMediaUsage
    assert usage.type.enums == ["EVENT_COVER", "RECAP_COVER", "RECAP_GALLERY"]
    assert usage.type.schema == APPLICATION_SCHEMA
    assert usage.default is None

    assert isinstance(processing_status.type, Enum)
    assert processing_status.type.enum_class is EventMediaProcessingStatus
    assert processing_status.type.enums == ["READY", "FAILED"]
    assert processing_status.type.schema == APPLICATION_SCHEMA
    assert cast(ColumnDefault, processing_status.default).arg is (
        EventMediaProcessingStatus.READY
    )
    assert str(cast(DefaultClause, processing_status.server_default).arg) == "READY"


def test_event_media_reference_roles_and_readiness_are_derived() -> None:
    event_cover = _media(usage=EventMediaUsage.EVENT_COVER)
    recap_cover = _media(usage=EventMediaUsage.RECAP_COVER)
    gallery = _media(usage=EventMediaUsage.RECAP_GALLERY)

    assert event_cover.is_cover is True
    assert recap_cover.is_cover is True
    assert gallery.is_cover is False
    assert event_cover.is_gallery is False
    assert gallery.is_gallery is True
    assert event_cover.is_ready is True
    assert _media(processing_status=EventMediaProcessingStatus.FAILED).is_ready is False
    assert _media(deleted_at=datetime(2026, 10, 1, tzinfo=UTC)).is_ready is False

    annotations = get_type_hints(EventMedia)
    assert get_args(annotations["event_id"]) == (UUID,)
    assert get_args(annotations["usage"]) == (EventMediaUsage,)
    assert get_args(annotations["processing_status"]) == (EventMediaProcessingStatus,)
    assert get_args(annotations["created_by"]) == (UUID,)


def test_postgresql_ddl_matches_event_media_contract() -> None:
    table = cast(Table, EventMedia.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    ddl = str(CreateTable(table).compile(dialect=dialect)).lower()

    assert "create table app_private.event_media" in ddl
    assert "bucket text default 'event-media' not null" in ddl
    assert "object_key text not null" in ddl
    assert "usage app_private.event_media_usage not null" in ddl
    assert "processing_status app_private.event_media_processing_status default 'ready' not null" in ddl
    assert "constraint uq_event_media_object_key unique (object_key)" in ddl
    assert "constraint uq_event_media_id_event_id unique (id, event_id)" in ddl
    assert "foreign key(event_id) references app_private.events (id) on delete cascade" in ddl
    assert "foreign key(created_by) references app_private.users (id) on delete restrict" in ddl
    assert "constraint ck_event_media_event_bucket" in ddl
    assert "constraint ck_event_media_dimensions" in ddl
