"""Persist sender-scoped Buddy message idempotency keys.

Revision ID: 0015_chat_send_idempotency
Revises: 0014_buddy_chat_persistence
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_chat_send_idempotency"
down_revision: str | Sequence[str] | None = "0014_buddy_chat_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_MESSAGE_TABLE = "buddy_messages"
_UNIQUE_NAME = "uq_buddy_messages_sender_id_client_message_id"


def upgrade() -> None:
    """Add the minimal durable key required for idempotent HTTP/realtime retries."""
    op.add_column(
        _MESSAGE_TABLE,
        sa.Column("client_message_id", sa.Uuid(), nullable=True),
        schema=_APPLICATION_SCHEMA,
    )
    # Existing CHAT-001 rows predate a client key. Their already-unique server ID
    # gives each row a deterministic non-colliding backfill without inventing a
    # second relationship or changing message content/retention.
    op.execute(
        sa.text(
            "UPDATE app_private.buddy_messages "
            "SET client_message_id = id WHERE client_message_id IS NULL"
        )
    )
    op.alter_column(
        _MESSAGE_TABLE,
        "client_message_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_unique_constraint(
        _UNIQUE_NAME,
        _MESSAGE_TABLE,
        ["sender_id", "client_message_id"],
        schema=_APPLICATION_SCHEMA,
    )
    op.execute(
        sa.text(
            "GRANT INSERT (client_message_id) "
            "ON TABLE app_private.buddy_messages TO vgu_buddy_runtime"
        )
    )


def downgrade() -> None:
    """Remove only CHAT-002 idempotency persistence."""
    op.drop_constraint(
        _UNIQUE_NAME,
        _MESSAGE_TABLE,
        type_="unique",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_column(
        _MESSAGE_TABLE,
        "client_message_id",
        schema=_APPLICATION_SCHEMA,
    )
