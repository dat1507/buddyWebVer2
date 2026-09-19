"""Create append-only, redacted admin audit records.

Revision ID: 0004_audit_logs
Revises: 0003_refresh_sessions
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_audit_logs"
down_revision: str | Sequence[str] | None = "0003_refresh_sessions"
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
                'REVOKE ALL ON TABLE app_private.audit_logs FROM %I', api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create the backend-only audit table with append-only runtime privileges."""
    op.create_table(
        "audit_logs",
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(btrim(action)) BETWEEN 1 AND 100",
            name="ck_audit_logs_action_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(resource_type)) BETWEEN 1 AND 100",
            name="ck_audit_logs_resource_type_length",
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["app_private.users.id"],
            name=op.f("fk_audit_logs_admin_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_admin_id_created_at",
        "audit_logs",
        ["admin_id", "created_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_audit_logs_resource_type_resource_id",
        "audit_logs",
        ["resource_type", "resource_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )

    op.execute(sa.text("REVOKE ALL ON TABLE app_private.audit_logs FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(sa.text("REVOKE ALL ON TABLE app_private.audit_logs FROM vgu_buddy_runtime"))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT ON TABLE app_private.audit_logs TO vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("ALTER TABLE app_private.audit_logs ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY audit_logs_backend_read
            ON app_private.audit_logs
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
            CREATE POLICY audit_logs_backend_insert
            ON app_private.audit_logs
            AS PERMISSIVE
            FOR INSERT
            TO vgu_buddy_runtime
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Remove audit persistence without changing accounts or domain records."""
    op.execute(sa.text("DROP POLICY audit_logs_backend_insert ON app_private.audit_logs"))
    op.execute(sa.text("DROP POLICY audit_logs_backend_read ON app_private.audit_logs"))
    op.drop_index(
        "ix_audit_logs_resource_type_resource_id",
        table_name="audit_logs",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_audit_logs_admin_id_created_at",
        table_name="audit_logs",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("audit_logs", schema=_APPLICATION_SCHEMA)
