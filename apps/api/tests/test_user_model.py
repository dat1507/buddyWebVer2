"""Tests for the persisted authentication user contract."""

from datetime import datetime
from typing import cast, get_args, get_type_hints

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateIndex, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import User, UserRole


def test_user_table_uses_private_schema_and_inherits_audit_fields() -> None:
    table = cast(Table, User.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "users"
    assert set(table.columns.keys()) == {
        "email",
        "password_hash",
        "role",
        "is_active",
        "email_verified",
        "email_verified_at",
        "last_login",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert "password" not in table.columns


def test_user_identity_and_password_columns_are_required_and_email_is_unique() -> None:
    table = cast(Table, User.__table__)
    email = table.c.email
    password_hash = table.c.password_hash

    assert isinstance(email.type, Text)
    assert email.nullable is False
    assert isinstance(password_hash.type, Text)
    assert password_hash.nullable is False

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns == {("email",)}

    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_names == {
        "ck_users_email_not_blank",
        "ck_users_password_hash_not_empty",
    }


def test_user_role_uses_private_native_enum_and_least_privilege_default() -> None:
    role = User.__table__.c.role

    assert isinstance(role.type, Enum)
    assert role.type.enum_class is UserRole
    assert role.type.enums == ["USER", "ADMIN"]
    assert role.type.native_enum is True
    assert role.type.validate_strings is True
    assert role.type.name == "user_role"
    assert role.type.schema == APPLICATION_SCHEMA
    assert role.nullable is False
    assert role.default is not None
    assert cast(ColumnDefault, role.default).arg == UserRole.USER
    assert role.server_default is not None
    assert str(cast(DefaultClause, role.server_default).arg) == UserRole.USER.value


def test_user_state_defaults_and_verification_timestamp_contract() -> None:
    table = cast(Table, User.__table__)
    is_active = table.c.is_active
    email_verified = table.c.email_verified
    email_verified_at = table.c.email_verified_at
    last_login = table.c.last_login

    assert isinstance(is_active.type, Boolean)
    assert is_active.nullable is False
    assert is_active.default is not None
    assert cast(ColumnDefault, is_active.default).arg is True
    assert is_active.server_default is not None
    assert str(cast(DefaultClause, is_active.server_default).arg) == "true"

    assert isinstance(email_verified.type, Boolean)
    assert email_verified.nullable is False
    assert email_verified.default is not None
    assert cast(ColumnDefault, email_verified.default).arg is False
    assert email_verified.server_default is not None
    assert str(cast(DefaultClause, email_verified.server_default).arg) == "false"

    assert isinstance(email_verified_at.type, DateTime)
    assert email_verified_at.type.timezone is True
    assert email_verified_at.nullable is True
    assert email_verified_at.default is None
    assert email_verified_at.server_default is None

    assert isinstance(last_login.type, DateTime)
    assert last_login.type.timezone is True
    assert last_login.nullable is True
    assert last_login.default is None
    assert last_login.server_default is None


def test_user_model_declares_role_and_active_lookup_indexes_without_email_duplicate() -> None:
    table = cast(Table, User.__table__)
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert indexes == {
        "ix_users_role": ("role",),
        "ix_users_is_active": ("is_active",),
    }


def test_user_annotations_use_domain_python_types() -> None:
    annotations = get_type_hints(User)

    assert get_args(annotations["email"]) == (str,)
    assert get_args(annotations["password_hash"]) == (str,)
    assert get_args(annotations["role"]) == (UserRole,)
    assert get_args(annotations["is_active"]) == (bool,)
    assert get_args(annotations["email_verified"]) == (bool,)
    assert get_args(annotations["email_verified_at"]) == (datetime | None,)
    assert get_args(annotations["last_login"]) == (datetime | None,)


def test_current_email_verification_is_timestamp_backed_for_users_only() -> None:
    verified_at = datetime.fromisoformat("2026-09-24T10:00:00+00:00")
    legacy_true_user = User(role=UserRole.USER, email_verified=True, email_verified_at=None)
    timestamped_user = User(
        role=UserRole.USER,
        email_verified=False,
        email_verified_at=verified_at,
    )
    bootstrapped_admin = User(
        role=UserRole.ADMIN,
        email_verified=True,
        email_verified_at=None,
    )

    assert legacy_true_user.is_current_email_verified is False
    assert timestamped_user.is_current_email_verified is True
    assert bootstrapped_admin.is_current_email_verified is True


def test_postgresql_ddl_matches_user_contract() -> None:
    table = cast(Table, User.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in table.indexes
    }

    assert "create table app_private.users" in table_ddl
    assert "email text not null" in table_ddl
    assert "password_hash text not null" in table_ddl
    assert "role app_private.user_role default 'user' not null" in table_ddl
    assert "is_active boolean default true not null" in table_ddl
    assert "email_verified boolean default false not null" in table_ddl
    assert "email_verified_at timestamp with time zone" in table_ddl
    assert "last_login timestamp with time zone" in table_ddl
    assert "constraint uq_users_email unique (email)" in table_ddl
    assert "constraint ck_users_email_not_blank" in table_ddl
    assert "constraint ck_users_password_hash_not_empty" in table_ddl
    assert index_ddl == {
        "create index ix_users_role on app_private.users (role)",
        "create index ix_users_is_active on app_private.users (is_active)",
    }
