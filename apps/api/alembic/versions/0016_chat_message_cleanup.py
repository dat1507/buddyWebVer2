"""Add the least-privilege expired Buddy-message cleanup entry point.

Revision ID: 0016_chat_message_cleanup
Revises: 0015_chat_send_idempotency
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_chat_message_cleanup"
down_revision: str | Sequence[str] | None = "0015_chat_send_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION_SIGNATURE = (
    "app_private.cleanup_expired_buddy_messages(integer, timestamp with time zone)"
)

_CREATE_CLEANUP_FUNCTION = """
CREATE FUNCTION app_private.cleanup_expired_buddy_messages(
    p_batch_size integer DEFAULT 20,
    p_cleanup_now timestamp with time zone DEFAULT statement_timestamp()
)
RETURNS TABLE (message_id uuid)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF p_batch_size IS NULL OR p_batch_size NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'invalid Buddy message cleanup batch size' USING ERRCODE = '22023';
    END IF;
    IF p_cleanup_now IS NULL OR p_cleanup_now > statement_timestamp() THEN
        RAISE EXCEPTION 'invalid Buddy message cleanup timestamp' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    WITH due AS (
        SELECT candidate.id
        FROM app_private.buddy_messages AS candidate
        WHERE candidate.expires_at <= p_cleanup_now
        ORDER BY candidate.expires_at, candidate.id
        LIMIT p_batch_size
        FOR UPDATE OF candidate SKIP LOCKED
    )
    DELETE FROM app_private.buddy_messages AS expired
    USING due
    WHERE expired.id = due.id
    RETURNING expired.id;
END
$$
"""

_DATA_API_REVOCATIONS = f"""
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL ON FUNCTION {_FUNCTION_SIGNATURE} FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Expose only the bounded expired-message deletion operation to runtime."""
    op.execute(sa.text(_CREATE_CLEANUP_FUNCTION))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(sa.text(f"REVOKE ALL ON FUNCTION {_FUNCTION_SIGNATURE} FROM PUBLIC"))
    op.execute(sa.text(f"GRANT EXECUTE ON FUNCTION {_FUNCTION_SIGNATURE} TO vgu_buddy_runtime"))


def downgrade() -> None:
    """Remove only the CHAT-005 cleanup entry point."""
    op.execute(sa.text(f"DROP FUNCTION {_FUNCTION_SIGNATURE}"))
