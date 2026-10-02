"""Make semester writes fail fast while restore owns the shared write barrier.

Revision ID: 0020_semester_restore_execution
Revises: 0019_semester_reset_execution
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_semester_restore_execution"
down_revision: str | Sequence[str] | None = "0019_semester_reset_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_write_barrier(*, fail_fast: bool) -> None:
    lock_statement = (
        "IF NOT pg_catalog.pg_try_advisory_xact_lock_shared("
        "pg_catalog.hashtextextended('vgu-buddy:semester-write-barrier:v1', 0)) THEN "
        "RAISE EXCEPTION USING ERRCODE = '55P03', "
        "MESSAGE = 'Semester maintenance write barrier is busy'; END IF;"
        if fail_fast
        else "PERFORM pg_catalog.pg_advisory_xact_lock_shared("
        "pg_catalog.hashtextextended('vgu-buddy:semester-write-barrier:v1', 0));"
    )
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION app_private.acquire_semester_write_barrier()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            BEGIN
                IF TG_TABLE_NAME = 'users' THEN
                    IF TG_OP = 'INSERT' AND NEW.role <> 'USER' THEN
                        RETURN NEW;
                    ELSIF TG_OP = 'UPDATE'
                          AND OLD.role <> 'USER' AND NEW.role <> 'USER' THEN
                        RETURN NEW;
                    ELSIF TG_OP = 'DELETE' AND OLD.role <> 'USER' THEN
                        RETURN OLD;
                    END IF;
                END IF;

                {lock_statement}
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )


def upgrade() -> None:
    """Prevent a waiting registration from succeeding after a concurrent restore."""
    _replace_write_barrier(fail_fast=True)


def downgrade() -> None:
    """Restore SEM-005's blocking shared-lock behavior."""
    _replace_write_barrier(fail_fast=False)
