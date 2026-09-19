"""Schema-contract tests for append-only admin audit records."""

from datetime import datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Table, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import AuditLog


def test_audit_log_uses_private_schema_and_expected_columns() -> None:
    table = cast(Table, AuditLog.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "audit_logs"
    assert set(table.columns.keys()) == {
        "admin_id",
        "action",
        "resource_type",
        "resource_id",
        "old_value",
        "new_value",
        "metadata",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }


def test_audit_identity_payload_and_actor_constraints() -> None:
    table = cast(Table, AuditLog.__table__)

    assert isinstance(table.c.admin_id.type, Uuid)
    assert table.c.admin_id.nullable is False
    assert isinstance(table.c.action.type, Text)
    assert table.c.action.nullable is False
    assert isinstance(table.c.resource_type.type, Text)
    assert table.c.resource_type.nullable is False
    assert isinstance(table.c.resource_id.type, Uuid)
    assert table.c.resource_id.nullable is False
    assert isinstance(table.c.old_value.type, JSONB)
    assert table.c.old_value.nullable is True
    assert isinstance(table.c.new_value.type, JSONB)
    assert table.c.new_value.nullable is True
    assert isinstance(table.c.metadata.type, JSONB)
    assert table.c.metadata.nullable is False
    assert isinstance(table.c.metadata.server_default, DefaultClause)
    assert str(table.c.metadata.server_default.arg) == "'{}'::jsonb"

    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].name == "fk_audit_logs_admin_id_users"
    assert foreign_keys[0].ondelete == "RESTRICT"
    assert tuple(element.target_fullname for element in foreign_keys[0].elements) == (
        "app_private.users.id",
    )

    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_names == {
        "ck_audit_logs_action_length",
        "ck_audit_logs_resource_type_length",
    }


def test_audit_log_declares_actor_time_and_resource_indexes() -> None:
    table = cast(Table, AuditLog.__table__)
    indexes = {
        index.name: tuple(column.name for column in index.columns) for index in table.indexes
    }

    assert indexes == {
        "ix_audit_logs_admin_id_created_at": ("admin_id", "created_at"),
        "ix_audit_logs_resource_type_resource_id": ("resource_type", "resource_id"),
    }


def test_audit_log_annotations_use_domain_types() -> None:
    annotations = get_type_hints(AuditLog)

    assert get_args(annotations["admin_id"]) == (UUID,)
    assert get_args(annotations["resource_id"]) == (UUID,)
    assert get_args(annotations["created_at"]) == (datetime,)


def test_postgresql_ddl_matches_audit_contract() -> None:
    table = cast(Table, AuditLog.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in table.indexes
    }

    assert "create table app_private.audit_logs" in table_ddl
    assert "admin_id uuid not null" in table_ddl
    assert "action text not null" in table_ddl
    assert "resource_type text not null" in table_ddl
    assert "resource_id uuid not null" in table_ddl
    assert "old_value jsonb" in table_ddl
    assert "new_value jsonb" in table_ddl
    assert "metadata jsonb default '{}'::jsonb not null" in table_ddl
    assert "constraint pk_audit_logs primary key (id)" in table_ddl
    assert "foreign key(admin_id) references app_private.users (id) on delete restrict" in table_ddl
    assert "constraint ck_audit_logs_action_length" in table_ddl
    assert "constraint ck_audit_logs_resource_type_length" in table_ddl
    assert index_ddl == {
        "create index ix_audit_logs_admin_id_created_at "
        "on app_private.audit_logs (admin_id, created_at)",
        "create index ix_audit_logs_resource_type_resource_id "
        "on app_private.audit_logs (resource_type, resource_id)",
    }
