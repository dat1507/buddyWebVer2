"""Grant the runtime role the narrow permissions required by backup restore.

Revision ID: 0021_restore_runtime_permissions
Revises: 0020_semester_restore_execution
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_restore_runtime_permissions"
down_revision: str | Sequence[str] | None = "0020_semester_restore_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow compatibility checks and exact restoration of persisted read state."""
    op.execute(sa.text("GRANT SELECT ON TABLE public.alembic_version TO vgu_buddy_runtime"))
    op.execute(
        sa.text("GRANT INSERT (read_at) ON TABLE app_private.buddy_messages TO vgu_buddy_runtime")
    )


def downgrade() -> None:
    """Return the runtime role to its pre-restore permission set."""
    op.execute(
        sa.text(
            "REVOKE INSERT (read_at) ON TABLE app_private.buddy_messages FROM vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("REVOKE SELECT ON TABLE public.alembic_version FROM vgu_buddy_runtime"))
