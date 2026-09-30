"""Add one Buddy conversation per Match and durable text messages.

Revision ID: 0014_buddy_chat_persistence
Revises: 0013_active_match_persistence
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_buddy_chat_persistence"
down_revision: str | Sequence[str] | None = "0013_active_match_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_CONVERSATION_TABLE = "buddy_conversations"
_MESSAGE_TABLE = "buddy_messages"

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.buddy_conversations FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.buddy_messages FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION '
                'app_private.enforce_buddy_message_sender() FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def _create_conversations() -> None:
    op.create_table(
        _CONVERSATION_TABLE,
        sa.Column("match_id", sa.Uuid(), nullable=False),
        # SEM-001 owns the authoritative semesters table, backfill, and FK.
        sa.Column("semester_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["app_private.matches.id"],
            name=op.f("fk_buddy_conversations_match_id_matches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buddy_conversations")),
        sa.UniqueConstraint(
            "match_id",
            name=op.f("uq_buddy_conversations_match_id"),
        ),
        schema=_APPLICATION_SCHEMA,
    )


def _create_messages() -> None:
    op.create_table(
        _MESSAGE_TABLE,
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(now() + INTERVAL '90 days')"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "body ~ '[^[:space:]]' AND char_length(body) <= 10000",
            name="ck_buddy_messages_body_length",
        ),
        sa.CheckConstraint(
            "(read_at IS NULL "
            "AND expires_at = created_at + INTERVAL '90 days') "
            "OR (read_at IS NOT NULL "
            "AND read_at >= created_at "
            "AND expires_at = LEAST("
            "read_at + INTERVAL '30 days', "
            "created_at + INTERVAL '90 days'))",
            name="ck_buddy_messages_retention_timestamps",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["app_private.buddy_conversations.id"],
            name=op.f("fk_buddy_messages_conversation_id_buddy_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["app_private.users.id"],
            name=op.f("fk_buddy_messages_sender_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buddy_messages")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_buddy_messages_conversation_created_at_id",
        _MESSAGE_TABLE,
        ["conversation_id", "created_at", "id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_buddy_messages_expires_at",
        _MESSAGE_TABLE,
        ["expires_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_buddy_messages_sender_id",
        _MESSAGE_TABLE,
        ["sender_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _create_sender_guard() -> None:
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.enforce_buddy_message_sender()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM app_private.buddy_conversations AS conversation
                    JOIN app_private.matches AS buddy_match
                      ON buddy_match.id = conversation.match_id
                    WHERE conversation.id = NEW.conversation_id
                      AND buddy_match.status = 'ACTIVE'
                      AND buddy_match.deleted_at IS NULL
                      AND NEW.sender_id IN (
                          buddy_match.participant_one_user_id,
                          buddy_match.participant_two_user_id
                      )
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_buddy_messages_sender_active_participant',
                        MESSAGE = 'Buddy message sender is not an active participant';
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_buddy_messages_sender_active_participant
            BEFORE INSERT OR UPDATE OF conversation_id, sender_id
            ON app_private.buddy_messages
            FOR EACH ROW
            EXECUTE FUNCTION app_private.enforce_buddy_message_sender()
            """
        )
    )
    op.execute(
        sa.text("REVOKE ALL ON FUNCTION app_private.enforce_buddy_message_sender() FROM PUBLIC")
    )
    op.execute(
        sa.text(
            "REVOKE ALL ON FUNCTION app_private.enforce_buddy_message_sender() "
            "FROM vgu_buddy_runtime"
        )
    )


def _secure_chat_tables() -> None:
    for table_name in (_CONVERSATION_TABLE, _MESSAGE_TABLE):
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table_name} FROM PUBLIC"))
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table_name} FROM vgu_buddy_runtime"))
        op.execute(sa.text(f"ALTER TABLE app_private.{table_name} ENABLE ROW LEVEL SECURITY"))

    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text("GRANT SELECT ON TABLE app_private.buddy_conversations TO vgu_buddy_runtime")
    )
    op.execute(
        sa.text(
            "GRANT INSERT (id, match_id, semester_id, created_at) "
            "ON TABLE app_private.buddy_conversations TO vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("GRANT SELECT ON TABLE app_private.buddy_messages TO vgu_buddy_runtime"))
    op.execute(
        sa.text(
            "GRANT INSERT (id, conversation_id, sender_id, body, created_at, expires_at) "
            "ON TABLE app_private.buddy_messages TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "GRANT UPDATE (read_at, expires_at) "
            "ON TABLE app_private.buddy_messages TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY buddy_conversations_backend_read
            ON app_private.buddy_conversations
            AS PERMISSIVE
            FOR SELECT
            TO vgu_buddy_runtime
            USING (true)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY buddy_conversations_backend_insert
            ON app_private.buddy_conversations
            AS PERMISSIVE
            FOR INSERT
            TO vgu_buddy_runtime
            WITH CHECK (true)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY buddy_messages_backend_read
            ON app_private.buddy_messages
            AS PERMISSIVE
            FOR SELECT
            TO vgu_buddy_runtime
            USING (true)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY buddy_messages_backend_insert
            ON app_private.buddy_messages
            AS PERMISSIVE
            FOR INSERT
            TO vgu_buddy_runtime
            WITH CHECK (true)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY buddy_messages_backend_retention_update
            ON app_private.buddy_messages
            AS PERMISSIVE
            FOR UPDATE
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def upgrade() -> None:
    """Create CHAT-001 persistence, integrity guards, and backend-only access."""
    _create_conversations()
    _create_messages()
    _create_sender_guard()
    _secure_chat_tables()


def downgrade() -> None:
    """Remove only CHAT-001 persistence objects."""
    op.execute(
        sa.text("DROP POLICY buddy_messages_backend_retention_update ON app_private.buddy_messages")
    )
    op.execute(sa.text("DROP POLICY buddy_messages_backend_insert ON app_private.buddy_messages"))
    op.execute(sa.text("DROP POLICY buddy_messages_backend_read ON app_private.buddy_messages"))
    op.execute(
        sa.text("DROP POLICY buddy_conversations_backend_insert ON app_private.buddy_conversations")
    )
    op.execute(
        sa.text("DROP POLICY buddy_conversations_backend_read ON app_private.buddy_conversations")
    )
    op.execute(
        sa.text(
            "DROP TRIGGER trg_buddy_messages_sender_active_participant "
            "ON app_private.buddy_messages"
        )
    )
    op.execute(sa.text("DROP FUNCTION app_private.enforce_buddy_message_sender()"))
    op.drop_index(
        "ix_buddy_messages_sender_id",
        table_name=_MESSAGE_TABLE,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_buddy_messages_expires_at",
        table_name=_MESSAGE_TABLE,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_buddy_messages_conversation_created_at_id",
        table_name=_MESSAGE_TABLE,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table(_MESSAGE_TABLE, schema=_APPLICATION_SCHEMA)
    op.drop_table(_CONVERSATION_TABLE, schema=_APPLICATION_SCHEMA)
