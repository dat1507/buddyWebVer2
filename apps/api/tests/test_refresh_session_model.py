"""Tests for persistent refresh-token family state."""

from datetime import datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Table, UniqueConstraint, Uuid
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.database import APPLICATION_SCHEMA
from app.models import RefreshSession


def test_refresh_session_uses_private_schema_and_audit_fields() -> None:
    table = cast(Table, RefreshSession.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "refresh_sessions"
    assert set(table.columns.keys()) == {
        "user_id",
        "refresh_token_id",
        "expires_at",
        "revoked_at",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }


def test_refresh_session_identity_and_rotation_columns_are_constrained() -> None:
    table = cast(Table, RefreshSession.__table__)

    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    assert isinstance(table.c.refresh_token_id.type, Uuid)
    assert table.c.refresh_token_id.nullable is False
    assert isinstance(table.c.expires_at.type, DateTime)
    assert table.c.expires_at.type.timezone is True
    assert table.c.expires_at.nullable is False
    assert isinstance(table.c.revoked_at.type, DateTime)
    assert table.c.revoked_at.type.timezone is True
    assert table.c.revoked_at.nullable is True

    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].name == "fk_refresh_sessions_user_id_users"
    assert foreign_keys[0].ondelete == "CASCADE"
    assert tuple(element.target_fullname for element in foreign_keys[0].elements) == (
        "app_private.users.id",
    )

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns == {("refresh_token_id",)}


def test_refresh_session_declares_user_and_expiry_indexes() -> None:
    table = cast(Table, RefreshSession.__table__)
    indexes = {
        index.name: tuple(column.name for column in index.columns) for index in table.indexes
    }

    assert indexes == {
        "ix_refresh_sessions_user_id": ("user_id",),
        "ix_refresh_sessions_expires_at": ("expires_at",),
    }


def test_refresh_session_annotations_use_domain_types() -> None:
    annotations = get_type_hints(RefreshSession)

    assert get_args(annotations["user_id"]) == (UUID,)
    assert get_args(annotations["refresh_token_id"]) == (UUID,)
    assert get_args(annotations["expires_at"]) == (datetime,)
    assert get_args(annotations["revoked_at"]) == (datetime | None,)


def test_postgresql_ddl_matches_refresh_session_contract() -> None:
    table = cast(Table, RefreshSession.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in table.indexes
    }

    assert "create table app_private.refresh_sessions" in table_ddl
    assert "user_id uuid not null" in table_ddl
    assert "refresh_token_id uuid not null" in table_ddl
    assert "expires_at timestamp with time zone not null" in table_ddl
    assert "revoked_at timestamp with time zone" in table_ddl
    assert "constraint pk_refresh_sessions primary key (id)" in table_ddl
    assert "constraint uq_refresh_sessions_refresh_token_id unique (refresh_token_id)" in table_ddl
    assert "foreign key(user_id) references app_private.users (id) on delete cascade" in table_ddl
    assert index_ddl == {
        "create index ix_refresh_sessions_user_id on app_private.refresh_sessions (user_id)",
        "create index ix_refresh_sessions_expires_at on app_private.refresh_sessions (expires_at)",
    }
