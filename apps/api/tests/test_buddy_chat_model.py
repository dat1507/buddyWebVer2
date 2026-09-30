"""CHAT-001 model, retention, constraint, and index contracts."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import ForeignKeyConstraint, Table, UniqueConstraint, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import (
    BUDDY_MESSAGE_MAX_RETENTION_DAYS,
    BUDDY_MESSAGE_READ_RETENTION_DAYS,
    MAX_BUDDY_MESSAGE_CODE_POINTS,
    BuddyConversation,
    BuddyMessage,
    buddy_message_expires_at,
    validate_buddy_message_body,
)


def test_message_retention_constants_and_aware_deadline_are_deterministic() -> None:
    created_at = datetime(2026, 9, 30, 4, 0, tzinfo=UTC)

    assert BUDDY_MESSAGE_MAX_RETENTION_DAYS == 90
    assert BUDDY_MESSAGE_READ_RETENTION_DAYS == 30
    assert buddy_message_expires_at(created_at) == created_at + timedelta(days=90)
    with pytest.raises(ValueError, match="timezone-aware"):
        buddy_message_expires_at(datetime(2026, 9, 30, 4, 0))


def test_message_body_is_plain_preserved_nonblank_and_code_point_bounded() -> None:
    inert_html = "  <script>alert('still text')</script> 😀  "

    assert validate_buddy_message_body(inert_html) == inert_html
    assert validate_buddy_message_body("😀" * MAX_BUDDY_MESSAGE_CODE_POINTS)
    with pytest.raises(ValueError, match="blank"):
        validate_buddy_message_body(" \t\n ")
    with pytest.raises(ValueError, match="code-point"):
        validate_buddy_message_body("😀" * (MAX_BUDDY_MESSAGE_CODE_POINTS + 1))


def test_chat_models_have_no_speculative_edit_delete_or_version_state() -> None:
    conversation_columns = set(BuddyConversation.__table__.c.keys())
    message_columns = set(BuddyMessage.__table__.c.keys())

    assert conversation_columns == {"id", "match_id", "semester_id", "created_at"}
    assert message_columns == {
        "id",
        "conversation_id",
        "sender_id",
        "body",
        "created_at",
        "read_at",
        "expires_at",
    }
    assert inspect(BuddyConversation).version_id_col is None
    assert inspect(BuddyMessage).version_id_col is None
    for speculative_column in (
        "updated_at",
        "deleted_at",
        "edited_at",
        "deleted_by",
        "status",
        "version",
    ):
        assert speculative_column not in conversation_columns
        assert speculative_column not in message_columns


def test_message_model_validates_body_and_timezone_assignments() -> None:
    created_at = datetime(2026, 9, 30, 4, 0, tzinfo=UTC)
    message = BuddyMessage(
        conversation_id=uuid4(),
        sender_id=uuid4(),
        body="Hello Buddy",
        created_at=created_at,
        expires_at=created_at + timedelta(days=90),
    )

    assert message.body == "Hello Buddy"
    with pytest.raises(ValueError, match="blank"):
        message.body = "   "
    with pytest.raises(ValueError, match="timezone-aware"):
        message.read_at = datetime(2026, 10, 1, 4, 0)


def test_postgresql_ddl_enforces_match_sender_retention_and_query_indexes() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    conversation_table = cast(Table, BuddyConversation.__table__)
    message_table = cast(Table, BuddyMessage.__table__)
    conversation_ddl = str(CreateTable(conversation_table).compile(dialect=dialect)).lower()
    message_ddl = str(CreateTable(message_table).compile(dialect=dialect)).lower()
    conversation_indexes = {
        str(index.name): str(CreateIndex(index).compile(dialect=dialect)).lower()
        for index in conversation_table.indexes
    }
    message_indexes = {
        str(index.name): str(CreateIndex(index).compile(dialect=dialect)).lower()
        for index in message_table.indexes
    }
    conversation_fks = {
        str(constraint.name): constraint
        for constraint in conversation_table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    message_fks = {
        str(constraint.name): constraint
        for constraint in message_table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    conversation_uniques = {
        str(constraint.name)
        for constraint in conversation_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert conversation_table.schema == "app_private"
    assert message_table.schema == "app_private"
    assert "uq_buddy_conversations_match_id" in conversation_uniques
    assert set(conversation_fks) == {"fk_buddy_conversations_match_id_matches"}
    assert conversation_fks["fk_buddy_conversations_match_id_matches"].ondelete == "CASCADE"
    assert "semester_id uuid" in conversation_ddl
    assert "references app_private.semesters" not in conversation_ddl
    assert conversation_indexes == {}

    assert "body ~ '[^[:space:]]'" in message_ddl
    assert "char_length(body) <= 10000" in message_ddl
    assert "expires_at = created_at + interval '90 days'" in message_ddl
    assert "read_at + interval '30 days'" in message_ddl
    assert set(message_fks) == {
        "fk_buddy_messages_conversation_id_buddy_conversations",
        "fk_buddy_messages_sender_id_users",
    }
    assert all(constraint.ondelete == "CASCADE" for constraint in message_fks.values())
    assert set(message_indexes) == {
        "ix_buddy_messages_conversation_created_at_id",
        "ix_buddy_messages_expires_at",
        "ix_buddy_messages_sender_id",
    }
    assert (
        "(conversation_id, created_at, id)"
        in message_indexes["ix_buddy_messages_conversation_created_at_id"]
    )
