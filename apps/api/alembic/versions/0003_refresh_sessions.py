"""Create persistent refresh-token rotation and revocation state.

Revision ID: 0003_refresh_sessions
Revises: 0002_users
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_refresh_sessions"
down_revision: str | Sequence[str] | None = "0002_users"
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
                'REVOKE ALL ON TABLE app_private.refresh_sessions FROM %I', api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create backend-only refresh-family state for atomic one-use rotation."""
    op.create_table(
        "refresh_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_private.users.id"],
            name=op.f("fk_refresh_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_sessions")),
        sa.UniqueConstraint(
            "refresh_token_id",
            name=op.f("uq_refresh_sessions_refresh_token_id"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_refresh_sessions_user_id",
        "refresh_sessions",
        ["user_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_refresh_sessions_expires_at",
        "refresh_sessions",
        ["expires_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )

    op.execute(sa.text("REVOKE ALL ON TABLE app_private.refresh_sessions FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            "ON TABLE app_private.refresh_sessions TO vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("ALTER TABLE app_private.refresh_sessions ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY refresh_sessions_backend_access
            ON app_private.refresh_sessions
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Remove refresh-session state without modifying User accounts."""
    op.execute(
        sa.text("DROP POLICY refresh_sessions_backend_access ON app_private.refresh_sessions")
    )
    op.drop_index(
        "ix_refresh_sessions_expires_at",
        table_name="refresh_sessions",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_refresh_sessions_user_id",
        table_name="refresh_sessions",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("refresh_sessions", schema=_APPLICATION_SCHEMA)
