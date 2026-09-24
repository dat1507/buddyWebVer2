"""Persistence-contract tests for EMAIL-001 verification token metadata."""

from datetime import datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, LargeBinary, Table, Text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.database import APPLICATION_SCHEMA
from app.models import EmailVerificationToken


def test_email_verification_token_table_is_private_and_digest_only() -> None:
    table = cast(Table, EmailVerificationToken.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "email_verification_tokens"
    assert set(table.columns.keys()) == {
        "user_id",
        "token_digest",
        "email_snapshot",
        "expires_at",
        "consumed_at",
        "superseded_at",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert "token" not in table.columns
    assert isinstance(table.c.token_digest.type, LargeBinary)
    assert table.c.token_digest.nullable is False
    assert isinstance(table.c.email_snapshot.type, Text)
    assert table.c.email_snapshot.nullable is False


def test_email_verification_token_constraints_and_indexes_support_one_current_token() -> None:
    table = cast(Table, EmailVerificationToken.__table__)
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_names == {
        "ck_email_verification_tokens_digest_not_empty",
        "ck_email_verification_tokens_email_not_blank",
        "ck_email_verification_tokens_expiry_after_creation",
    }

    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    foreign_key = foreign_keys[0]
    assert foreign_key.ondelete == "CASCADE"
    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "app_private.users.id",
    )

    indexes = {str(index.name): index for index in table.indexes if index.name is not None}
    assert set(indexes) == {
        "ix_email_verification_tokens_user_id",
        "ix_email_verification_tokens_expires_at",
        "uq_email_verification_tokens_active_user_id",
    }
    active = indexes["uq_email_verification_tokens_active_user_id"]
    assert active.unique is True
    assert tuple(column.name for column in active.columns) == ("user_id",)
    where = str(active.dialect_options["postgresql"]["where"])
    assert where == (
        "consumed_at IS NULL AND superseded_at IS NULL AND deleted_at IS NULL"
    )


def test_email_verification_token_timestamps_and_annotations_are_explicit() -> None:
    table = cast(Table, EmailVerificationToken.__table__)
    annotations = get_type_hints(EmailVerificationToken)

    for name in ("expires_at", "consumed_at", "superseded_at"):
        column = table.c[name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
    assert table.c.expires_at.nullable is False
    assert table.c.consumed_at.nullable is True
    assert table.c.superseded_at.nullable is True
    assert get_args(annotations["user_id"]) == (UUID,)
    assert get_args(annotations["token_digest"]) == (bytes,)
    assert get_args(annotations["email_snapshot"]) == (str,)
    assert get_args(annotations["expires_at"]) == (datetime,)
    assert get_args(annotations["consumed_at"]) == (datetime | None,)
    assert get_args(annotations["superseded_at"]) == (datetime | None,)


def test_postgresql_ddl_contains_no_plaintext_token_column() -> None:
    table = cast(Table, EmailVerificationToken.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in table.indexes
    }

    assert "create table app_private.email_verification_tokens" in table_ddl
    assert "token_digest bytea not null" in table_ddl
    assert "constraint uq_email_verification_tokens_token_digest" in table_ddl
    assert "constraint fk_email_verification_tokens_user_id_users" in table_ddl
    assert "references app_private.users (id) on delete cascade" in table_ddl
    assert "\n\ttoken " not in table_ddl
    assert any(
        "create unique index uq_email_verification_tokens_active_user_id" in ddl
        and "where consumed_at is null and superseded_at is null and deleted_at is null" in ddl
        for ddl in index_ddl
    )
