"""Create the private application schema and least-privilege runtime role.

Revision ID: 0001_private_app_schema
Revises:
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_private_app_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA app_private FROM %I', api_role);
            EXECUTE format(
                'REVOKE ALL ON ALL TABLES IN SCHEMA app_private FROM %I', api_role
            );
            EXECUTE format(
                'REVOKE ALL ON ALL SEQUENCES IN SCHEMA app_private FROM %I', api_role
            );
            EXECUTE format(
                'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA app_private FROM %I', api_role
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA app_private '
                'REVOKE ALL ON TABLES FROM %I', api_role
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA app_private '
                'REVOKE ALL ON SEQUENCES FROM %I', api_role
            );
            EXECUTE format(
                'ALTER DEFAULT PRIVILEGES IN SCHEMA app_private '
                'REVOKE ALL ON FUNCTIONS FROM %I', api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create a non-exposed schema with explicit default privileges."""
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS app_private"))
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = 'vgu_buddy_runtime'
                ) THEN
                    CREATE ROLE vgu_buddy_runtime
                        LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
                END IF;
            END
            $$
            """
        )
    )
    op.execute(sa.text("REVOKE ALL ON SCHEMA app_private FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(sa.text("GRANT USAGE ON SCHEMA app_private TO vgu_buddy_runtime"))
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "REVOKE ALL ON TABLES FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "REVOKE ALL ON SEQUENCES FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "REVOKE ALL ON FUNCTIONS FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO vgu_buddy_runtime"
        )
    )


def downgrade() -> None:
    """Remove the empty foundation schema without cascading data loss."""
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA app_private "
            "REVOKE USAGE, SELECT, UPDATE ON SEQUENCES FROM vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("REVOKE ALL ON SCHEMA app_private FROM vgu_buddy_runtime"))
    op.execute(sa.text("DROP SCHEMA app_private"))
    op.execute(sa.text("DROP ROLE vgu_buddy_runtime"))
