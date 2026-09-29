"""Add durable matching invitation persistence and lifecycle invariants.

Revision ID: 0012_invitation_persistence
Revises: 0011_preference_persistence
Create Date: 2026-09-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_invitation_persistence"
down_revision: str | Sequence[str] | None = "0011_preference_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_TABLE_NAME = "matching_invitations"
_INVITATION_STATUS_ENUM = postgresql.ENUM(
    "PENDING",
    "ACCEPTED",
    "DECLINED",
    "CANCELLED",
    "EXPIRED",
    name="invitation_status",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.matching_invitations FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON TYPE app_private.invitation_status FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def _create_invitation_status() -> None:
    op.execute(
        sa.text(
            "CREATE TYPE app_private.invitation_status AS ENUM "
            "('PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED', 'EXPIRED')"
        )
    )


def _create_matching_invitations() -> None:
    op.create_table(
        _TABLE_NAME,
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "pair_low_user_id",
            sa.Uuid(),
            sa.Computed("LEAST(sender_id, recipient_id)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "pair_high_user_id",
            sa.Uuid(),
            sa.Computed("GREATEST(sender_id, recipient_id)", persisted=True),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            _INVITATION_STATUS_ENUM,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(now() + INTERVAL '7 days')"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
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
            "sender_id <> recipient_id",
            name="ck_matching_invitations_distinct_participants",
        ),
        sa.CheckConstraint(
            "pair_low_user_id < pair_high_user_id",
            name="ck_matching_invitations_canonical_pair_order",
        ),
        sa.CheckConstraint(
            "message = btrim(message) AND char_length(message) <= 10000",
            name="ck_matching_invitations_message_canonical_length",
        ),
        sa.CheckConstraint(
            "expires_at = created_at + INTERVAL '7 days'",
            name="ck_matching_invitations_expiry_interval",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING' AND responded_at IS NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'ACCEPTED' AND responded_at IS NOT NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL) "
            "OR (status = 'DECLINED' AND responded_at IS NOT NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'CANCELLED' AND responded_at IS NULL "
            "AND cancelled_at IS NOT NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'EXPIRED' AND responded_at IS NULL "
            "AND cancelled_at IS NULL AND expired_at IS NOT NULL "
            "AND sender_hidden_at IS NULL)",
            name="ck_matching_invitations_status_timestamps",
        ),
        sa.CheckConstraint(
            "(responded_at IS NULL OR responded_at >= created_at) "
            "AND (cancelled_at IS NULL OR cancelled_at >= created_at) "
            "AND (expired_at IS NULL OR expired_at >= expires_at) "
            "AND (sender_hidden_at IS NULL OR sender_hidden_at >= responded_at)",
            name="ck_matching_invitations_timestamp_order",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_matching_invitations_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["app_private.users.id"],
            name=op.f("fk_matching_invitations_recipient_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["app_private.users.id"],
            name=op.f("fk_matching_invitations_sender_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matching_invitations")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "uq_matching_invitations_pending_pair",
        _TABLE_NAME,
        ["pair_low_user_id", "pair_high_user_id"],
        unique=True,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "ix_matching_invitations_sender_status_created_at",
        _TABLE_NAME,
        ["sender_id", "status", "created_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_matching_invitations_recipient_status_created_at",
        _TABLE_NAME,
        ["recipient_id", "status", "created_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_matching_invitations_pending_expires_at",
        _TABLE_NAME,
        ["expires_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def _secure_matching_invitations() -> None:
    op.execute(sa.text("REVOKE ALL ON TABLE app_private.matching_invitations FROM PUBLIC"))
    op.execute(
        sa.text("REVOKE ALL ON TABLE app_private.matching_invitations FROM vgu_buddy_runtime")
    )
    op.execute(sa.text("REVOKE ALL ON TYPE app_private.invitation_status FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE ON TABLE app_private.matching_invitations "
            "TO vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("GRANT USAGE ON TYPE app_private.invitation_status TO vgu_buddy_runtime"))
    op.execute(sa.text("ALTER TABLE app_private.matching_invitations ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY matching_invitations_backend_access
            ON app_private.matching_invitations
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def upgrade() -> None:
    """Create the invitation record, indexes and backend-only access boundary."""
    _create_invitation_status()
    _create_matching_invitations()
    _secure_matching_invitations()


def downgrade() -> None:
    """Remove only INV-001 persistence objects."""
    op.execute(
        sa.text(
            "DROP POLICY matching_invitations_backend_access ON app_private.matching_invitations"
        )
    )
    op.drop_index(
        "ix_matching_invitations_pending_expires_at",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_matching_invitations_recipient_status_created_at",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_matching_invitations_sender_status_created_at",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "uq_matching_invitations_pending_pair",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table(_TABLE_NAME, schema=_APPLICATION_SCHEMA)
    op.execute(sa.text("DROP TYPE app_private.invitation_status"))
