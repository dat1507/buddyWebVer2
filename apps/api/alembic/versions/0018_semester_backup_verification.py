"""Permit immutable pre-reset verification before READY retention starts.

Revision ID: 0018_backup_verification
Revises: 0017_semester_boundary_metadata
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_backup_verification"
down_revision: str | Sequence[str] | None = "0017_semester_boundary_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "app_private"

_LIFECYCLE_V2 = (
    "(state = 'CREATING' AND expires_at IS NULL AND failure_code IS NULL) OR "
    "(state IN ('READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED') "
    "AND verified_at IS NOT NULL AND expires_at IS NOT NULL "
    "AND database_manifest_location IS NOT NULL "
    "AND database_manifest_checksum IS NOT NULL "
    "AND avatar_manifest_location IS NOT NULL "
    "AND avatar_manifest_checksum IS NOT NULL AND failure_code IS NULL) OR "
    "(state = 'FAILED' AND failure_code IS NOT NULL)"
)

_LIFECYCLE_V1 = (
    "(state = 'CREATING' AND verified_at IS NULL AND failure_code IS NULL) OR "
    "(state IN ('READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED') "
    "AND verified_at IS NOT NULL AND expires_at IS NOT NULL "
    "AND database_manifest_location IS NOT NULL "
    "AND database_manifest_checksum IS NOT NULL "
    "AND avatar_manifest_location IS NOT NULL "
    "AND avatar_manifest_checksum IS NOT NULL AND failure_code IS NULL) OR "
    "(state = 'FAILED' AND failure_code IS NOT NULL)"
)


def _replace_integrity_function(*, immutable_verification: bool) -> None:
    immutable_clause = ""
    if immutable_verification:
        immutable_clause = """
                   OR (OLD.verified_at IS NOT NULL
                       AND NEW.verified_at IS DISTINCT FROM OLD.verified_at)
                   OR (OLD.expires_at IS NOT NULL
                       AND NEW.expires_at IS DISTINCT FROM OLD.expires_at)
                   OR (OLD.database_manifest_location IS NOT NULL AND (
                       NEW.database_manifest_location IS DISTINCT FROM OLD.database_manifest_location
                       OR NEW.database_manifest_checksum IS DISTINCT FROM OLD.database_manifest_checksum
                       OR NEW.database_row_counts IS DISTINCT FROM OLD.database_row_counts
                   ))
                   OR (OLD.avatar_manifest_location IS NOT NULL AND (
                       NEW.avatar_manifest_location IS DISTINCT FROM OLD.avatar_manifest_location
                       OR NEW.avatar_manifest_checksum IS DISTINCT FROM OLD.avatar_manifest_checksum
                       OR NEW.avatar_object_count IS DISTINCT FROM OLD.avatar_object_count
                   ))
        """
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION app_private.enforce_semester_backup()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            BEGIN
                IF NEW.restored_by_admin_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM app_private.users AS actor
                    WHERE actor.id = NEW.restored_by_admin_id
                      AND actor.role = 'ADMIN'
                      AND actor.deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_semester_backups_restore_admin_actor',
                        MESSAGE = 'Semester backup restore actor is invalid';
                END IF;
                IF TG_OP = 'UPDATE' THEN
                    IF NEW.id IS DISTINCT FROM OLD.id
                       OR NEW.source_semester_id IS DISTINCT FROM OLD.source_semester_id
                       OR NEW.source_boundary_at IS DISTINCT FROM OLD.source_boundary_at
                       OR NEW.created_by_operation_id IS DISTINCT FROM OLD.created_by_operation_id
                       OR NEW.created_at IS DISTINCT FROM OLD.created_at
                       OR (OLD.state = 'CREATING' AND NEW.state NOT IN ('CREATING', 'READY', 'FAILED'))
                       OR (OLD.state = 'READY' AND NEW.state NOT IN
                           ('READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED'))
                       OR (OLD.state = 'RESTORE_BLOCKED_NEW_DATA' AND NEW.state NOT IN
                           ('RESTORE_BLOCKED_NEW_DATA', 'EXPIRED'))
                       OR (OLD.state IN ('EXPIRED', 'FAILED') AND NEW IS DISTINCT FROM OLD)
                       OR (OLD.state = 'RESTORE_BLOCKED_NEW_DATA' AND NEW.restored_at IS NOT NULL)
                       {immutable_clause}
                    THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '23514',
                            CONSTRAINT = 'ck_semester_backups_state_transition',
                            MESSAGE = 'Semester backup update is invalid';
                    END IF;
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )


def upgrade() -> None:
    """Allow a durable verification proof before reset completion starts retention."""
    op.drop_constraint(
        "ck_semester_backups_lifecycle",
        "semester_backups",
        schema=_SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "ck_semester_backups_lifecycle",
        "semester_backups",
        _LIFECYCLE_V2,
        schema=_SCHEMA,
    )
    _replace_integrity_function(immutable_verification=True)


def downgrade() -> None:
    """Restore SEM-001 lifecycle rules when no verified CREATING row exists."""
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM app_private.semester_backups
                    WHERE state = 'CREATING' AND verified_at IS NOT NULL
                ) THEN
                    RAISE EXCEPTION 'Cannot downgrade with a verified CREATING backup';
                END IF;
            END
            $$
            """
        )
    )
    op.drop_constraint(
        "ck_semester_backups_lifecycle",
        "semester_backups",
        schema=_SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "ck_semester_backups_lifecycle",
        "semester_backups",
        _LIFECYCLE_V1,
        schema=_SCHEMA,
    )
    _replace_integrity_function(immutable_verification=False)
