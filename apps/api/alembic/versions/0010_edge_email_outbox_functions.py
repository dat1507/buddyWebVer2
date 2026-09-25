"""Add least-privilege database functions for the Edge email worker.

Revision ID: 0010_edge_email_outbox_functions
Revises: 0009_transactional_outbox
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_edge_email_outbox_functions"
down_revision: str | Sequence[str] | None = "0009_transactional_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"

_CREATE_CLAIM_FUNCTION = """
CREATE FUNCTION app_private.claim_transactional_email_outbox(
    p_worker_id text,
    p_batch_size integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    event_type text,
    recipient_email text,
    idempotency_key text,
    payload jsonb
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, app_private
AS $$
BEGIN
    IF p_worker_id IS NULL
       OR length(btrim(p_worker_id)) NOT BETWEEN 1 AND 100
       OR p_worker_id ~ E'[\\r\\n]'
    THEN
        RAISE EXCEPTION 'invalid email outbox worker ID' USING ERRCODE = '22023';
    END IF;
    IF p_batch_size IS NULL OR p_batch_size NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'invalid email outbox batch size' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    WITH ready AS (
        SELECT candidate.id
        FROM app_private.transactional_outbox AS candidate
        WHERE candidate.deleted_at IS NULL
          AND candidate.sent_at IS NULL
          AND candidate.failed_at IS NULL
          AND candidate.next_attempt_at <= statement_timestamp()
          AND (
              candidate.lease_expires_at IS NULL
              OR candidate.lease_expires_at <= statement_timestamp()
          )
        ORDER BY candidate.next_attempt_at, candidate.id
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    ), claimed AS (
        UPDATE app_private.transactional_outbox AS outbox
        SET lease_owner = btrim(p_worker_id),
            lease_expires_at = statement_timestamp() + interval '5 minutes',
            updated_at = statement_timestamp()
        FROM ready
        WHERE outbox.id = ready.id
        RETURNING
            outbox.id,
            outbox.event_type,
            outbox.recipient_email,
            outbox.idempotency_key,
            outbox.payload
    )
    SELECT
        claimed.id,
        claimed.event_type,
        claimed.recipient_email,
        claimed.idempotency_key,
        claimed.payload
    FROM claimed;
END
$$
"""

_CREATE_COMPLETE_FUNCTION = """
CREATE FUNCTION app_private.complete_transactional_email_outbox(
    p_id uuid,
    p_worker_id text,
    p_provider_message_id text
)
RETURNS text
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, app_private
AS $$
DECLARE
    outcome text;
BEGIN
    IF p_worker_id IS NULL
       OR length(btrim(p_worker_id)) NOT BETWEEN 1 AND 100
       OR p_worker_id ~ E'[\\r\\n]'
    THEN
        RAISE EXCEPTION 'invalid email outbox worker ID' USING ERRCODE = '22023';
    END IF;
    IF p_provider_message_id IS NULL
       OR length(btrim(p_provider_message_id)) NOT BETWEEN 1 AND 200
       OR p_provider_message_id ~ E'[\\r\\n]'
    THEN
        RAISE EXCEPTION 'invalid provider message ID' USING ERRCODE = '22023';
    END IF;

    UPDATE app_private.transactional_outbox AS outbox
    SET attempts = outbox.attempts + 1,
        lease_owner = NULL,
        lease_expires_at = NULL,
        sent_at = statement_timestamp(),
        provider_message_id = btrim(p_provider_message_id),
        last_error_code = NULL,
        updated_at = statement_timestamp()
    WHERE outbox.id = p_id
      AND outbox.deleted_at IS NULL
      AND outbox.sent_at IS NULL
      AND outbox.failed_at IS NULL
      AND outbox.lease_owner = btrim(p_worker_id)
    RETURNING 'sent'::text INTO outcome;

    RETURN coalesce(outcome, 'skipped');
END
$$
"""

_CREATE_FAIL_FUNCTION = """
CREATE FUNCTION app_private.fail_transactional_email_outbox(
    p_id uuid,
    p_worker_id text,
    p_retryable boolean,
    p_error_code text
)
RETURNS text
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, app_private
AS $$
DECLARE
    outcome text;
BEGIN
    IF p_worker_id IS NULL
       OR length(btrim(p_worker_id)) NOT BETWEEN 1 AND 100
       OR p_worker_id ~ E'[\\r\\n]'
    THEN
        RAISE EXCEPTION 'invalid email outbox worker ID' USING ERRCODE = '22023';
    END IF;
    IF p_retryable IS NULL THEN
        RAISE EXCEPTION 'retryable flag is required' USING ERRCODE = '22023';
    END IF;
    IF p_error_code IS NULL
       OR length(btrim(p_error_code)) NOT BETWEEN 1 AND 100
       OR p_error_code !~ '^[a-z0-9_]+$'
    THEN
        RAISE EXCEPTION 'invalid email outbox error code' USING ERRCODE = '22023';
    END IF;

    UPDATE app_private.transactional_outbox AS outbox
    SET attempts = outbox.attempts + 1,
        lease_owner = NULL,
        lease_expires_at = NULL,
        next_attempt_at = CASE
            WHEN p_retryable AND outbox.attempts + 1 < 5
            THEN statement_timestamp()
                 + LEAST(power(2, GREATEST(outbox.attempts, 0))::integer, 60)
                   * interval '1 minute'
            ELSE outbox.next_attempt_at
        END,
        failed_at = CASE
            WHEN p_retryable AND outbox.attempts + 1 < 5 THEN NULL
            ELSE statement_timestamp()
        END,
        last_error_code = btrim(p_error_code),
        updated_at = statement_timestamp()
    WHERE outbox.id = p_id
      AND outbox.deleted_at IS NULL
      AND outbox.sent_at IS NULL
      AND outbox.failed_at IS NULL
      AND outbox.lease_owner = btrim(p_worker_id)
    RETURNING CASE
        WHEN outbox.failed_at IS NULL THEN 'retry'
        ELSE 'failed'
    END INTO outcome;

    RETURN coalesce(outcome, 'skipped');
END
$$
"""

_FUNCTION_SIGNATURES = (
    "app_private.claim_transactional_email_outbox(text, integer)",
    "app_private.complete_transactional_email_outbox(uuid, text, text)",
    "app_private.fail_transactional_email_outbox(uuid, text, boolean, text)",
)

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
    function_signature text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            FOREACH function_signature IN ARRAY ARRAY[
                'app_private.claim_transactional_email_outbox(text, integer)',
                'app_private.complete_transactional_email_outbox(uuid, text, text)',
                'app_private.fail_transactional_email_outbox(uuid, text, boolean, text)'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON FUNCTION %s FROM %I',
                    function_signature,
                    api_role
                );
            END LOOP;
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Expose atomic outbox state transitions only to the runtime database role."""
    op.execute(sa.text(_CREATE_CLAIM_FUNCTION))
    op.execute(sa.text(_CREATE_COMPLETE_FUNCTION))
    op.execute(sa.text(_CREATE_FAIL_FUNCTION))
    op.execute(sa.text(_DATA_API_REVOCATIONS))

    for signature in _FUNCTION_SIGNATURES:
        op.execute(sa.text(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC"))
        op.execute(sa.text(f"GRANT EXECUTE ON FUNCTION {signature} TO vgu_buddy_runtime"))


def downgrade() -> None:
    """Remove only the Edge-worker database entry points."""
    for signature in reversed(_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION {signature}"))
