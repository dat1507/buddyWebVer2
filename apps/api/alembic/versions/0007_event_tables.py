"""Create Event, EventMedia and EventRegistration persistence.

Revision ID: 0007_event_tables
Revises: 0006_profile_catalogs
Create Date: 2026-09-21
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_event_tables"
down_revision: str | Sequence[str] | None = "0006_profile_catalogs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_TABLES = ("events", "event_media", "event_registrations")
_ENUM_TYPES = (
    "event_status",
    "event_visibility",
    "event_media_usage",
    "event_media_processing_status",
    "event_registration_status",
)

_EVENT_STATUS_ENUM = postgresql.ENUM(
    "DRAFT",
    "PUBLISHED",
    "CANCELLED",
    name="event_status",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)
_EVENT_VISIBILITY_ENUM = postgresql.ENUM(
    "PUBLIC",
    "MEMBERS",
    name="event_visibility",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)
_EVENT_MEDIA_USAGE_ENUM = postgresql.ENUM(
    "EVENT_COVER",
    "RECAP_COVER",
    "RECAP_GALLERY",
    name="event_media_usage",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)
_EVENT_MEDIA_PROCESSING_STATUS_ENUM = postgresql.ENUM(
    "READY",
    "FAILED",
    name="event_media_processing_status",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)
_EVENT_REGISTRATION_STATUS_ENUM = postgresql.ENUM(
    "registered",
    "cancelled",
    "attended",
    name="event_registration_status",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
    table_name text;
    type_name text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            FOREACH table_name IN ARRAY ARRAY[
                'events',
                'event_media',
                'event_registrations'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON TABLE app_private.%I FROM %I',
                    table_name,
                    api_role
                );
            END LOOP;
            FOREACH type_name IN ARRAY ARRAY[
                'event_status',
                'event_visibility',
                'event_media_usage',
                'event_media_processing_status',
                'event_registration_status'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON TYPE app_private.%I FROM %I',
                    type_name,
                    api_role
                );
            END LOOP;
        END IF;
    END LOOP;
END
$$
"""


def _create_enum_types() -> None:
    op.execute(
        sa.text("CREATE TYPE app_private.event_status AS ENUM ('DRAFT', 'PUBLISHED', 'CANCELLED')")
    )
    op.execute(sa.text("CREATE TYPE app_private.event_visibility AS ENUM ('PUBLIC', 'MEMBERS')"))
    op.execute(
        sa.text(
            "CREATE TYPE app_private.event_media_usage "
            "AS ENUM ('EVENT_COVER', 'RECAP_COVER', 'RECAP_GALLERY')"
        )
    )
    op.execute(
        sa.text("CREATE TYPE app_private.event_media_processing_status AS ENUM ('READY', 'FAILED')")
    )
    op.execute(
        sa.text(
            "CREATE TYPE app_private.event_registration_status "
            "AS ENUM ('registered', 'cancelled', 'attended')"
        )
    )


def _base_columns() -> tuple[sa.Column[Any], ...]:
    return (
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def _create_events() -> None:
    op.create_table(
        "events",
        sa.Column("title_en", sa.Text(), nullable=True),
        sa.Column("title_de", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_de", sa.Text(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "timezone",
            sa.Text(),
            server_default=sa.text("'Asia/Ho_Chi_Minh'"),
            nullable=False,
        ),
        sa.Column("location_en", sa.Text(), nullable=True),
        sa.Column("location_de", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("organizer", sa.Text(), nullable=True),
        sa.Column("registration_url", sa.Text(), nullable=True),
        sa.Column("cover_media_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            _EVENT_STATUS_ENUM,
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column(
            "visibility",
            _EVENT_VISIBILITY_ENUM,
            server_default="MEMBERS",
            nullable=False,
        ),
        sa.Column(
            "registration_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column(
            "registration_deadline",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        *_base_columns(),
        sa.CheckConstraint(
            "title_en IS NULL OR char_length(btrim(title_en)) BETWEEN 1 AND 120",
            name="ck_events_title_en_length",
        ),
        sa.CheckConstraint(
            "title_de IS NULL OR char_length(btrim(title_de)) BETWEEN 1 AND 120",
            name="ck_events_title_de_length",
        ),
        sa.CheckConstraint(
            "description_en IS NULL OR char_length(btrim(description_en)) BETWEEN 1 AND 10000",
            name="ck_events_description_en_length",
        ),
        sa.CheckConstraint(
            "description_de IS NULL OR char_length(btrim(description_de)) BETWEEN 1 AND 10000",
            name="ck_events_description_de_length",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date > start_date",
            name="ck_events_date_order",
        ),
        sa.CheckConstraint(
            "char_length(btrim(timezone)) BETWEEN 1 AND 255",
            name="ck_events_timezone_length",
        ),
        sa.CheckConstraint(
            "location_en IS NULL OR char_length(btrim(location_en)) BETWEEN 1 AND 200",
            name="ck_events_location_en_length",
        ),
        sa.CheckConstraint(
            "location_de IS NULL OR char_length(btrim(location_de)) BETWEEN 1 AND 200",
            name="ck_events_location_de_length",
        ),
        sa.CheckConstraint(
            "category IS NULL OR char_length(btrim(category)) BETWEEN 1 AND 80",
            name="ck_events_category_length",
        ),
        sa.CheckConstraint(
            "organizer IS NULL OR char_length(btrim(organizer)) BETWEEN 1 AND 200",
            name="ck_events_organizer_length",
        ),
        sa.CheckConstraint(
            "registration_url IS NULL OR registration_url ~ '^https://[^[:space:]]+$'",
            name="ck_events_registration_url_https",
        ),
        sa.CheckConstraint(
            "max_participants IS NULL OR max_participants > 0",
            name="ck_events_max_participants_positive",
        ),
        sa.CheckConstraint("version >= 1", name="ck_events_version_positive"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["app_private.users.id"],
            name=op.f("fk_events_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["app_private.users.id"],
            name=op.f("fk_events_updated_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_events_status",
        "events",
        ["status"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_events_start_date",
        "events",
        ["start_date"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _create_event_media() -> None:
    op.create_table(
        "event_media",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "bucket",
            sa.Text(),
            server_default=sa.text("'event-media'"),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("usage", _EVENT_MEDIA_USAGE_ENUM, nullable=False),
        sa.Column("alt_en", sa.Text(), nullable=False),
        sa.Column("alt_de", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "processing_status",
            _EVENT_MEDIA_PROCESSING_STATUS_ENUM,
            server_default="READY",
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_base_columns(),
        sa.CheckConstraint(
            "bucket = 'event-media'",
            name="ck_event_media_event_bucket",
        ),
        sa.CheckConstraint(
            "char_length(btrim(alt_en)) BETWEEN 1 AND 200",
            name="ck_event_media_alt_en_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(alt_de)) BETWEEN 1 AND 200",
            name="ck_event_media_alt_de_length",
        ),
        sa.CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_event_media_mime_type",
        ),
        sa.CheckConstraint(
            "byte_size BETWEEN 1 AND 5242880",
            name="ck_event_media_byte_size_range",
        ),
        sa.CheckConstraint(
            "width BETWEEN 1 AND 4096 AND height BETWEEN 1 AND 4096 AND width * height <= 16777216",
            name="ck_event_media_dimensions",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_event_media_sort_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["app_private.events.id"],
            name=op.f("fk_event_media_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["app_private.users.id"],
            name=op.f("fk_event_media_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_media")),
        sa.UniqueConstraint(
            "object_key",
            name=op.f("uq_event_media_object_key"),
        ),
        sa.UniqueConstraint(
            "id",
            "event_id",
            name="uq_event_media_id_event_id",
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_event_media_event_id_usage_sort_order",
        "event_media",
        ["event_id", "usage", "sort_order"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _create_event_cover_reference() -> None:
    op.create_foreign_key(
        "fk_events_cover_media_owner_event_media",
        "events",
        "event_media",
        ["cover_media_id", "id"],
        ["id", "event_id"],
        source_schema=_APPLICATION_SCHEMA,
        referent_schema=_APPLICATION_SCHEMA,
        ondelete="RESTRICT",
    )


def _create_event_registrations() -> None:
    op.create_table(
        "event_registrations",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            _EVENT_REGISTRATION_STATUS_ENUM,
            server_default="registered",
            nullable=False,
        ),
        *_base_columns(),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["app_private.events.id"],
            name=op.f("fk_event_registrations_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_private.users.id"],
            name=op.f("fk_event_registrations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_registrations")),
        sa.UniqueConstraint(
            "event_id",
            "user_id",
            name=op.f("uq_event_registrations_event_id_user_id"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_event_registrations_user_id",
        "event_registrations",
        ["user_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _secure_event_tables() -> None:
    for table_name in _TABLES:
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table_name} FROM PUBLIC"))
    for type_name in _ENUM_TYPES:
        op.execute(sa.text(f"REVOKE ALL ON TYPE app_private.{type_name} FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    for table_name in _TABLES:
        op.execute(
            sa.text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                f"ON TABLE app_private.{table_name} TO vgu_buddy_runtime"
            )
        )
        op.execute(sa.text(f"ALTER TABLE app_private.{table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_backend_access
                ON app_private.{table_name}
                AS PERMISSIVE
                FOR ALL
                TO vgu_buddy_runtime
                USING (true)
                WITH CHECK (true)
                """
            )
        )
    for type_name in _ENUM_TYPES:
        op.execute(sa.text(f"GRANT USAGE ON TYPE app_private.{type_name} TO vgu_buddy_runtime"))


def upgrade() -> None:
    """Create private Event persistence in circular-FK-safe order."""
    _create_enum_types()
    _create_events()
    _create_event_media()
    _create_event_cover_reference()
    _create_event_registrations()
    _secure_event_tables()


def downgrade() -> None:
    """Remove Event persistence without changing users or managed Storage policy."""
    for table_name in reversed(_TABLES):
        op.execute(sa.text(f"DROP POLICY {table_name}_backend_access ON app_private.{table_name}"))
    op.drop_constraint(
        "fk_events_cover_media_owner_event_media",
        "events",
        schema=_APPLICATION_SCHEMA,
        type_="foreignkey",
    )
    op.drop_index(
        "ix_event_registrations_user_id",
        table_name="event_registrations",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("event_registrations", schema=_APPLICATION_SCHEMA)
    op.drop_index(
        "ix_event_media_event_id_usage_sort_order",
        table_name="event_media",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("event_media", schema=_APPLICATION_SCHEMA)
    op.drop_index(
        "ix_events_start_date",
        table_name="events",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_events_status",
        table_name="events",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("events", schema=_APPLICATION_SCHEMA)
    for type_name in reversed(_ENUM_TYPES):
        op.execute(sa.text(f"DROP TYPE app_private.{type_name}"))
