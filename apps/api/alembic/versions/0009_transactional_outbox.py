"""Add the private transactional email outbox.

Revision ID: 0009_transactional_outbox
Revises: 0008_email_verification
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_transactional_outbox"
down_revision: str | Sequence[str] | None = "0008_email_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.transactional_outbox FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create backend-only transactional email state with leases and retry metadata."""
    op.create_table(
        "transactional_outbox",
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("last_error_code", sa.Text(), nullable=True),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(btrim(event_type)) BETWEEN 1 AND 100",
            name="ck_transactional_outbox_event_type_length",
        ),
        sa.CheckConstraint(
            "length(btrim(recipient_email)) BETWEEN 1 AND 320",
            name="ck_transactional_outbox_recipient_email_length",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) BETWEEN 1 AND 256",
            name="ck_transactional_outbox_idempotency_key_length",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_transactional_outbox_payload_object",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_transactional_outbox_attempts_nonnegative",
        ),
        sa.CheckConstraint(
            "(lease_owner IS NULL) = (lease_expires_at IS NULL)",
            name="ck_transactional_outbox_lease_pair",
        ),
        sa.CheckConstraint(
            "NOT (sent_at IS NOT NULL AND failed_at IS NOT NULL)",
            name="ck_transactional_outbox_one_terminal_state",
        ),
        sa.CheckConstraint(
            "(sent_at IS NULL AND failed_at IS NULL) "
            "OR (lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_transactional_outbox_terminal_lease_clear",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["app_private.users.id"],
            name=op.f("fk_transactional_outbox_recipient_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactional_outbox")),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_transactional_outbox_idempotency_key"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_transactional_outbox_recipient_user_id",
        "transactional_outbox",
        ["recipient_user_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_transactional_outbox_delivery_ready",
        "transactional_outbox",
        ["next_attempt_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text(
            "sent_at IS NULL AND failed_at IS NULL AND deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_transactional_outbox_lease_expires_at",
        "transactional_outbox",
        ["lease_expires_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text("lease_expires_at IS NOT NULL"),
    )

    op.execute(sa.text("REVOKE ALL ON TABLE app_private.transactional_outbox FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            "ON TABLE app_private.transactional_outbox TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text("ALTER TABLE app_private.transactional_outbox ENABLE ROW LEVEL SECURITY")
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY transactional_outbox_backend_access
            ON app_private.transactional_outbox
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Remove only the transactional outbox state introduced by MAIL-001."""
    op.execute(
        sa.text(
            "DROP POLICY transactional_outbox_backend_access "
            "ON app_private.transactional_outbox"
        )
    )
    op.drop_index(
        "ix_transactional_outbox_lease_expires_at",
        table_name="transactional_outbox",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_transactional_outbox_delivery_ready",
        table_name="transactional_outbox",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_transactional_outbox_recipient_user_id",
        table_name="transactional_outbox",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("transactional_outbox", schema=_APPLICATION_SCHEMA)
