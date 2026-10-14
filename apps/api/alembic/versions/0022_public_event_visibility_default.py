"""Default legacy Event visibility storage to PUBLIC.

Revision ID: 0022_public_event_visibility_default
Revises: 0021_restore_runtime_permissions
Create Date: 2026-10-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_public_event_visibility_default"
down_revision: str | Sequence[str] | None = "0021_restore_runtime_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make new rows public by default without rewriting existing Event data."""
    op.alter_column(
        "events",
        "visibility",
        schema="app_private",
        existing_type=sa.Enum(name="event_visibility", schema="app_private"),
        server_default=sa.text("'PUBLIC'::app_private.event_visibility"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore the legacy MEMBERS storage default without changing existing rows."""
    op.alter_column(
        "events",
        "visibility",
        schema="app_private",
        existing_type=sa.Enum(name="event_visibility", schema="app_private"),
        server_default=sa.text("'MEMBERS'::app_private.event_visibility"),
        existing_nullable=False,
    )
