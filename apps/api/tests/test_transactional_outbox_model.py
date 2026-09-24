"""Persistence contract for the MAIL-001 transactional outbox."""

from datetime import datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Integer, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.database import APPLICATION_SCHEMA
from app.models import TransactionalOutbox


def test_outbox_is_private_and_persists_only_template_inputs() -> None:
    table = cast(Table, TransactionalOutbox.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert set(table.columns.keys()) == {
        "event_type",
        "aggregate_id",
        "recipient_user_id",
        "recipient_email",
        "idempotency_key",
        "payload",
        "attempts",
        "next_attempt_at",
        "lease_owner",
        "lease_expires_at",
        "sent_at",
        "failed_at",
        "provider_message_id",
        "last_error_code",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert isinstance(table.c.event_type.type, Text)
    assert isinstance(table.c.payload.type, JSONB)
    assert isinstance(table.c.attempts.type, Integer)
    assert "subject" not in table.columns
    assert "body" not in table.columns
    assert "provider_response" not in table.columns


def test_outbox_constraints_indexes_and_user_deletion_contract() -> None:
    table = cast(Table, TransactionalOutbox.__table__)
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_transactional_outbox_event_type_length",
        "ck_transactional_outbox_recipient_email_length",
        "ck_transactional_outbox_idempotency_key_length",
        "ck_transactional_outbox_payload_object",
        "ck_transactional_outbox_attempts_nonnegative",
        "ck_transactional_outbox_lease_pair",
        "ck_transactional_outbox_one_terminal_state",
        "ck_transactional_outbox_terminal_lease_clear",
    }
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].ondelete == "SET NULL"
    assert tuple(element.target_fullname for element in foreign_keys[0].elements) == (
        "app_private.users.id",
    )
    indexes = {str(index.name): index for index in table.indexes if index.name is not None}
    assert set(indexes) == {
        "ix_transactional_outbox_recipient_user_id",
        "ix_transactional_outbox_delivery_ready",
        "ix_transactional_outbox_lease_expires_at",
    }
    assert table.c.idempotency_key.unique is True


def test_outbox_timestamps_and_annotations_are_explicit() -> None:
    table = cast(Table, TransactionalOutbox.__table__)
    annotations = get_type_hints(TransactionalOutbox)

    for name in ("next_attempt_at", "lease_expires_at", "sent_at", "failed_at"):
        column_type = table.c[name].type
        assert isinstance(column_type, DateTime)
        assert column_type.timezone is True
    assert get_args(annotations["aggregate_id"]) == (UUID,)
    assert get_args(annotations["recipient_user_id"]) == (UUID | None,)
    assert get_args(annotations["payload"]) == (dict[str, object],)
    assert get_args(annotations["attempts"]) == (int,)
    assert get_args(annotations["next_attempt_at"]) == (datetime,)


def test_postgresql_ddl_matches_worker_query_contract() -> None:
    table = cast(Table, TransactionalOutbox.__table__)
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in table.indexes
    }

    assert "create table app_private.transactional_outbox" in table_ddl
    assert "payload jsonb not null" in table_ddl
    assert "constraint uq_transactional_outbox_idempotency_key" in table_ddl
    assert "on delete set null" in table_ddl
    assert any(
        "create index ix_transactional_outbox_delivery_ready" in ddl
        and "where sent_at is null and failed_at is null and deleted_at is null" in ddl
        for ddl in index_ddl
    )
