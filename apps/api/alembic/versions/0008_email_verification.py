"""Add timestamp-backed email verification persistence.

Revision ID: 0008_email_verification
Revises: 0007_event_tables
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_email_verification"
down_revision: str | Sequence[str] | None = "0007_event_tables"
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
                'REVOKE ALL ON TABLE app_private.email_verification_tokens FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Add evidence-backed USER verification state and digest-only token metadata."""
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema=_APPLICATION_SCHEMA,
    )
    # No trustworthy timestamp exists in the legacy schema. In particular, the old boolean and
    # account/activity timestamps are not verification evidence, so legacy USER rows stay NULL.
    op.execute(
        sa.text(
            "UPDATE app_private.users "
            "SET email_verified_at = NULL "
            "WHERE role = 'USER'"
        )
    )

    op.create_table(
        "email_verification_tokens",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.LargeBinary(), nullable=False),
        sa.Column("email_snapshot", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
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
            "octet_length(token_digest) > 0",
            name="ck_email_verification_tokens_digest_not_empty",
        ),
        sa.CheckConstraint(
            "length(btrim(email_snapshot)) > 0",
            name="ck_email_verification_tokens_email_not_blank",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_email_verification_tokens_expiry_after_creation",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_private.users.id"],
            name=op.f("fk_email_verification_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verification_tokens")),
        sa.UniqueConstraint(
            "token_digest",
            name=op.f("uq_email_verification_tokens_token_digest"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "uq_email_verification_tokens_active_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=True,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text(
            "consumed_at IS NULL AND superseded_at IS NULL AND deleted_at IS NULL"
        ),
    )

    op.execute(
        sa.text(
            "REVOKE ALL ON TABLE app_private.email_verification_tokens FROM PUBLIC"
        )
    )
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            "ON TABLE app_private.email_verification_tokens TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE app_private.email_verification_tokens ENABLE ROW LEVEL SECURITY"
        )
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY email_verification_tokens_backend_access
            ON app_private.email_verification_tokens
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Remove verification-token state and restore the pre-EMAIL-001 User schema."""
    op.execute(
        sa.text(
            "DROP POLICY email_verification_tokens_backend_access "
            "ON app_private.email_verification_tokens"
        )
    )
    op.drop_index(
        "uq_email_verification_tokens_active_user_id",
        table_name="email_verification_tokens",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_email_verification_tokens_expires_at",
        table_name="email_verification_tokens",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_email_verification_tokens_user_id",
        table_name="email_verification_tokens",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("email_verification_tokens", schema=_APPLICATION_SCHEMA)
    op.drop_column("users", "email_verified_at", schema=_APPLICATION_SCHEMA)
