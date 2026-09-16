"""Tests for the shared SQLAlchemy model foundation."""

from datetime import datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import DateTime, String, Table, Uuid
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CreateTable

from app.core.database import APPLICATION_SCHEMA
from app.models import Base


class ModelProbe(Base):
    """Concrete mapping used to verify inherited BE-006 fields."""

    __tablename__ = "be006_model_probe"

    label: Mapped[str] = mapped_column(String, nullable=False)


def test_base_is_abstract_and_uses_private_schema() -> None:
    assert not hasattr(Base, "__table__")
    assert Base.metadata.schema == APPLICATION_SCHEMA
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


def test_concrete_model_inherits_uuid_and_audit_columns() -> None:
    table = ModelProbe.__table__

    assert table.schema == APPLICATION_SCHEMA
    assert set(table.columns.keys()) == {
        "label",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }

    id_column = table.c.id
    assert isinstance(id_column.type, Uuid)
    assert id_column.type.as_uuid is True
    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert id_column.server_default is not None

    created_at = table.c.created_at
    updated_at = table.c.updated_at
    deleted_at = table.c.deleted_at

    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.nullable is False
    assert created_at.server_default is not None

    assert isinstance(updated_at.type, DateTime)
    assert updated_at.type.timezone is True
    assert updated_at.nullable is False
    assert updated_at.server_default is not None
    assert updated_at.onupdate is not None

    assert isinstance(deleted_at.type, DateTime)
    assert deleted_at.type.timezone is True
    assert deleted_at.nullable is True
    assert deleted_at.server_default is None


def test_model_annotations_use_domain_python_types() -> None:
    annotations = get_type_hints(Base)

    assert get_args(annotations["id"]) == (UUID,)
    assert get_args(annotations["created_at"]) == (datetime,)
    assert get_args(annotations["updated_at"]) == (datetime,)
    assert get_args(annotations["deleted_at"]) == (datetime | None,)


def test_postgresql_ddl_uses_native_types_defaults_and_named_primary_key() -> None:
    table = cast(Table, ModelProbe.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    ddl = str(CreateTable(table).compile(dialect=dialect)).lower()

    assert "create table app_private.be006_model_probe" in ddl
    assert "id uuid default gen_random_uuid() not null" in ddl
    assert ddl.count("timestamp with time zone") == 3
    assert ddl.count("default now() not null") == 2
    assert "deleted_at timestamp with time zone" in ddl
    assert "constraint pk_be006_model_probe primary key (id)" in ddl
