"""Create the private users table and backend-only access policy.

Revision ID: 0002_users
Revises: 0001_private_app_schema
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_users"
down_revision: str | Sequence[str] | None = "0001_private_app_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_USER_ROLE_ENUM = postgresql.ENUM(
    "USER",
    "ADMIN",
    name="user_role",
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
                'REVOKE ALL ON TABLE app_private.users FROM %I', api_role
            );
            EXECUTE format(
                'REVOKE ALL ON TYPE app_private.user_role FROM %I', api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    """Create the backend-owned user account persistence boundary."""
    op.execute(
        sa.text("CREATE TYPE app_private.user_role AS ENUM ('USER', 'ADMIN')")
    )
    op.create_table(
        "users",
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            _USER_ROLE_ENUM,
            server_default="USER",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
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
            "length(btrim(email)) > 0",
            name="ck_users_email_not_blank",
        ),
        sa.CheckConstraint(
            "length(password_hash) > 0",
            name="ck_users_password_hash_not_empty",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_users_is_active",
        "users",
        ["is_active"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_users_role",
        "users",
        ["role"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )

    op.execute(sa.text("REVOKE ALL ON TABLE app_private.users FROM PUBLIC"))
    op.execute(sa.text("REVOKE ALL ON TYPE app_private.user_role FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            "ON TABLE app_private.users TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "GRANT USAGE ON TYPE app_private.user_role TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text("ALTER TABLE app_private.users ENABLE ROW LEVEL SECURITY")
    )
    op.execute(
        sa.text(
            """
            CREATE POLICY users_backend_access
            ON app_private.users
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def downgrade() -> None:
    """Remove the users table and its dedicated enum type."""
    op.execute(
        sa.text("DROP POLICY users_backend_access ON app_private.users")
    )
    op.drop_index(
        "ix_users_role",
        table_name="users",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_users_is_active",
        table_name="users",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("users", schema=_APPLICATION_SCHEMA)
    op.execute(sa.text("DROP TYPE app_private.user_role"))
