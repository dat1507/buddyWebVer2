"""Add semester boundaries and durable reset/restore metadata.

Revision ID: 0017_semester_boundary_metadata
Revises: 0016_chat_message_cleanup
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_semester_boundary_metadata"
down_revision: str | Sequence[str] | None = "0016_chat_message_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "app_private"

_SEMESTER_STATUS = postgresql.ENUM(
    "CURRENT",
    "CLOSED",
    name="semester_status",
    schema=_SCHEMA,
    create_type=False,
)
_OPERATION_TYPE = postgresql.ENUM(
    "RESET",
    "RESTORE",
    name="semester_operation_type",
    schema=_SCHEMA,
    create_type=False,
)
_OPERATION_STATE = postgresql.ENUM(
    "REQUESTED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="semester_operation_state",
    schema=_SCHEMA,
    create_type=False,
)
_BACKUP_STATE = postgresql.ENUM(
    "CREATING",
    "READY",
    "RESTORE_BLOCKED_NEW_DATA",
    "EXPIRED",
    "FAILED",
    name="semester_backup_state",
    schema=_SCHEMA,
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
            EXECUTE format('REVOKE ALL ON TABLE app_private.semesters FROM %I', api_role);
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.semester_operations FROM %I', api_role
            );
            EXECUTE format(
                'REVOKE ALL ON TABLE app_private.semester_backups FROM %I', api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.enforce_semester_boundary() FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.enforce_semester_operation() FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.enforce_semester_backup() FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.stamp_user_semester() FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.stamp_match_semester() FROM %I',
                api_role
            );
            EXECUTE format(
                'REVOKE ALL ON FUNCTION app_private.stamp_conversation_semester() FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""


def _create_enums() -> None:
    op.execute(sa.text("CREATE TYPE app_private.semester_status AS ENUM ('CURRENT', 'CLOSED')"))
    op.execute(
        sa.text("CREATE TYPE app_private.semester_operation_type AS ENUM ('RESET', 'RESTORE')")
    )
    op.execute(
        sa.text(
            "CREATE TYPE app_private.semester_operation_state AS ENUM "
            "('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')"
        )
    )
    op.execute(
        sa.text(
            "CREATE TYPE app_private.semester_backup_state AS ENUM "
            "('CREATING', 'READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED', 'FAILED')"
        )
    )


def _create_semesters() -> None:
    op.create_table(
        "semesters",
        sa.Column("status", _SEMESTER_STATUS, server_default="CURRENT", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("statement_timestamp()"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_operation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "student_accounts_created",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("first_student_created_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "student_accounts_created >= 0",
            name="ck_semesters_student_accounts_created_non_negative",
        ),
        sa.CheckConstraint(
            "(student_accounts_created = 0 AND first_student_created_at IS NULL) "
            "OR (student_accounts_created > 0 AND first_student_created_at IS NOT NULL)",
            name="ck_semesters_student_marker_consistent",
        ),
        sa.CheckConstraint(
            "(status = 'CURRENT' AND closed_at IS NULL AND reset_operation_id IS NULL) "
            "OR (status = 'CLOSED' AND closed_at IS NOT NULL "
            "AND reset_operation_id IS NOT NULL)",
            name="ck_semesters_boundary_state",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semesters")),
        schema=_SCHEMA,
    )
    op.create_index(
        "uq_semesters_current",
        "semesters",
        ["status"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("status = 'CURRENT'"),
    )
    op.create_index(
        "ix_semesters_reset_operation_id",
        "semesters",
        ["reset_operation_id"],
        unique=False,
        schema=_SCHEMA,
    )
    op.execute(
        sa.text(
            "INSERT INTO app_private.semesters "
            "(status, started_at, student_accounts_created, first_student_created_at) "
            "SELECT 'CURRENT', "
            "COALESCE(MIN(created_at) FILTER (WHERE role = 'USER'), statement_timestamp()), "
            "COUNT(*) FILTER (WHERE role = 'USER'), "
            "MIN(created_at) FILTER (WHERE role = 'USER') "
            "FROM app_private.users"
        )
    )


def _stamp_existing_cohort() -> None:
    op.add_column("users", sa.Column("semester_id", sa.Uuid(), nullable=True), schema=_SCHEMA)
    op.execute(
        sa.text(
            "UPDATE app_private.users SET semester_id = current_semester.id "
            "FROM app_private.semesters AS current_semester "
            "WHERE users.role = 'USER' AND current_semester.status = 'CURRENT'"
        )
    )
    op.create_foreign_key(
        "fk_users_semester_id_semesters",
        "users",
        "semesters",
        ["semester_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_users_role_semester",
        "users",
        "(role = 'USER' AND semester_id IS NOT NULL) OR (role = 'ADMIN' AND semester_id IS NULL)",
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_users_semester_id",
        "users",
        ["semester_id"],
        unique=False,
        schema=_SCHEMA,
    )

    op.execute(
        sa.text(
            "UPDATE app_private.matches SET semester_id = current_semester.id "
            "FROM app_private.semesters AS current_semester "
            "WHERE matches.semester_id IS NULL AND current_semester.status = 'CURRENT'"
        )
    )
    op.alter_column(
        "matches",
        "semester_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        "fk_matches_semester_id_semesters",
        "matches",
        "semesters",
        ["semester_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_matches_semester_id",
        "matches",
        ["semester_id"],
        unique=False,
        schema=_SCHEMA,
    )

    op.execute(
        sa.text(
            "UPDATE app_private.buddy_conversations AS conversation "
            "SET semester_id = buddy_match.semester_id "
            "FROM app_private.matches AS buddy_match "
            "WHERE conversation.match_id = buddy_match.id"
        )
    )
    op.alter_column(
        "buddy_conversations",
        "semester_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        "fk_buddy_conversations_semester_id_semesters",
        "buddy_conversations",
        "semesters",
        ["semester_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_buddy_conversations_semester_id",
        "buddy_conversations",
        ["semester_id"],
        unique=False,
        schema=_SCHEMA,
    )


def _create_operations() -> None:
    op.create_table(
        "semester_operations",
        sa.Column("operation_type", _OPERATION_TYPE, nullable=False),
        sa.Column(
            "state",
            _OPERATION_STATE,
            server_default="REQUESTED",
            nullable=False,
        ),
        sa.Column("semester_id", sa.Uuid(), nullable=False),
        sa.Column("admin_actor_id", sa.Uuid(), nullable=False),
        sa.Column("backup_id", sa.Uuid(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("statement_timestamp()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "affected_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("failure_code", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "jsonb_typeof(affected_counts) = 'object'",
            name="ck_semester_operations_affected_counts_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_summary) = 'object'",
            name="ck_semester_operations_result_summary_object",
        ),
        sa.CheckConstraint(
            "failure_code IS NULL OR char_length(btrim(failure_code)) BETWEEN 1 AND 100",
            name="ck_semester_operations_failure_code_length",
        ),
        sa.CheckConstraint(
            "(state = 'REQUESTED' AND started_at IS NULL AND completed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'RUNNING' AND started_at IS NOT NULL AND completed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'SUCCEEDED' AND started_at IS NOT NULL AND completed_at IS NOT NULL "
            "AND failure_code IS NULL) OR "
            "(state = 'FAILED' AND completed_at IS NOT NULL AND failure_code IS NOT NULL)",
            name="ck_semester_operations_lifecycle",
        ),
        sa.CheckConstraint(
            "(started_at IS NULL OR started_at >= requested_at) "
            "AND (completed_at IS NULL OR completed_at >= requested_at) "
            "AND (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)",
            name="ck_semester_operations_timestamp_order",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["app_private.semesters.id"],
            name="fk_semester_operations_semester_id_semesters",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["admin_actor_id"],
            ["app_private.users.id"],
            name="fk_semester_operations_admin_actor_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semester_operations")),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_operations_semester_id",
        "semester_operations",
        ["semester_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_operations_admin_actor_id",
        "semester_operations",
        ["admin_actor_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_operations_backup_id",
        "semester_operations",
        ["backup_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_operations_state_requested_at",
        "semester_operations",
        ["state", "requested_at"],
        schema=_SCHEMA,
    )
    op.create_index(
        "uq_semester_operations_running",
        "semester_operations",
        ["state"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("state = 'RUNNING'"),
    )


def _create_backups() -> None:
    op.create_table(
        "semester_backups",
        sa.Column("source_semester_id", sa.Uuid(), nullable=False),
        sa.Column("source_boundary_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_operation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            _BACKUP_STATE,
            server_default="CREATING",
            nullable=False,
        ),
        sa.Column("database_manifest_location", sa.Text(), nullable=True),
        sa.Column("database_manifest_checksum", sa.Text(), nullable=True),
        sa.Column(
            "database_row_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("avatar_manifest_location", sa.Text(), nullable=True),
        sa.Column("avatar_manifest_checksum", sa.Text(), nullable=True),
        sa.Column("avatar_object_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("restore_operation_id", sa.Uuid(), nullable=True),
        sa.Column("failure_code", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "jsonb_typeof(database_row_counts) = 'object'",
            name="ck_semester_backups_database_row_counts_object",
        ),
        sa.CheckConstraint(
            "avatar_object_count >= 0",
            name="ck_semester_backups_avatar_object_count_non_negative",
        ),
        sa.CheckConstraint(
            "failure_code IS NULL OR char_length(btrim(failure_code)) BETWEEN 1 AND 100",
            name="ck_semester_backups_failure_code_length",
        ),
        sa.CheckConstraint(
            "(state = 'CREATING' AND verified_at IS NULL AND failure_code IS NULL) OR "
            "(state IN ('READY', 'RESTORE_BLOCKED_NEW_DATA', 'EXPIRED') "
            "AND verified_at IS NOT NULL AND expires_at IS NOT NULL "
            "AND database_manifest_location IS NOT NULL "
            "AND database_manifest_checksum IS NOT NULL "
            "AND avatar_manifest_location IS NOT NULL "
            "AND avatar_manifest_checksum IS NOT NULL AND failure_code IS NULL) OR "
            "(state = 'FAILED' AND failure_code IS NOT NULL)",
            name="ck_semester_backups_lifecycle",
        ),
        sa.CheckConstraint(
            "(verified_at IS NULL OR verified_at >= source_boundary_at) "
            "AND (expires_at IS NULL OR verified_at IS NULL OR expires_at > verified_at) "
            "AND (restored_at IS NULL OR verified_at IS NOT NULL)",
            name="ck_semester_backups_timestamp_order",
        ),
        sa.CheckConstraint(
            "(restored_at IS NULL AND restored_by_admin_id IS NULL "
            "AND restore_operation_id IS NULL) OR "
            "(restored_at IS NOT NULL AND restored_by_admin_id IS NOT NULL "
            "AND restore_operation_id IS NOT NULL)",
            name="ck_semester_backups_restore_metadata_complete",
        ),
        sa.ForeignKeyConstraint(
            ["source_semester_id"],
            ["app_private.semesters.id"],
            name="fk_semester_backups_source_semester_id_semesters",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_operation_id"],
            ["app_private.semester_operations.id"],
            name="fk_semester_backups_created_by_operation_id_semester_operations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["restored_by_admin_id"],
            ["app_private.users.id"],
            name="fk_semester_backups_restored_by_admin_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["restore_operation_id"],
            ["app_private.semester_operations.id"],
            name="fk_semester_backups_restore_operation_id_semester_operations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semester_backups")),
        sa.UniqueConstraint(
            "created_by_operation_id",
            name="uq_semester_backups_created_by_operation_id",
        ),
        sa.UniqueConstraint(
            "restore_operation_id",
            name="uq_semester_backups_restore_operation_id",
        ),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_backups_source_semester_id",
        "semester_backups",
        ["source_semester_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_backups_created_by_operation_id",
        "semester_backups",
        ["created_by_operation_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_backups_restored_by_admin_id",
        "semester_backups",
        ["restored_by_admin_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_backups_restore_operation_id",
        "semester_backups",
        ["restore_operation_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_semester_backups_state_expires_at",
        "semester_backups",
        ["state", "expires_at"],
        schema=_SCHEMA,
    )

    op.create_foreign_key(
        "fk_semester_operations_backup_id_semester_backups",
        "semester_operations",
        "semester_backups",
        ["backup_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_semesters_reset_operation_id_semester_operations",
        "semesters",
        "semester_operations",
        ["reset_operation_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
        ondelete="RESTRICT",
    )


def _create_integrity_guards() -> None:
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.stamp_user_semester()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            DECLARE
                target_status app_private.semester_status;
            BEGIN
                IF NEW.role <> 'USER' THEN
                    RETURN NEW;
                END IF;
                IF NEW.semester_id IS NULL THEN
                    SELECT semester.id, semester.status
                    INTO NEW.semester_id, target_status
                    FROM app_private.semesters AS semester
                    WHERE semester.status = 'CURRENT'
                    FOR UPDATE;
                    IF NEW.semester_id IS NULL THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '23514',
                            CONSTRAINT = 'ck_users_current_semester_required',
                            MESSAGE = 'Current semester is unavailable';
                    END IF;
                ELSE
                    SELECT semester.status
                    INTO target_status
                    FROM app_private.semesters AS semester
                    WHERE semester.id = NEW.semester_id
                    FOR UPDATE;
                END IF;
                IF target_status = 'CURRENT' THEN
                    UPDATE app_private.semesters
                    SET student_accounts_created = student_accounts_created + 1,
                        first_student_created_at = COALESCE(
                            first_student_created_at,
                            statement_timestamp()
                        ),
                        updated_at = statement_timestamp()
                    WHERE id = NEW.semester_id;
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_users_stamp_semester
            BEFORE INSERT ON app_private.users
            FOR EACH ROW EXECUTE FUNCTION app_private.stamp_user_semester()
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.stamp_match_semester()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            DECLARE
                first_semester_id uuid;
                second_semester_id uuid;
            BEGIN
                SELECT first_user.semester_id, second_user.semester_id
                INTO first_semester_id, second_semester_id
                FROM app_private.users AS first_user
                JOIN app_private.users AS second_user
                  ON second_user.id = NEW.participant_two_user_id
                WHERE first_user.id = NEW.participant_one_user_id;
                IF first_semester_id IS NULL
                   OR first_semester_id IS DISTINCT FROM second_semester_id
                   OR (NEW.semester_id IS NOT NULL
                       AND NEW.semester_id IS DISTINCT FROM first_semester_id)
                THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_matches_participant_semester',
                        MESSAGE = 'Match participant semester is invalid';
                END IF;
                NEW.semester_id := first_semester_id;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_matches_stamp_semester
            BEFORE INSERT OR UPDATE OF participant_one_user_id, participant_two_user_id, semester_id
            ON app_private.matches
            FOR EACH ROW EXECUTE FUNCTION app_private.stamp_match_semester()
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.stamp_conversation_semester()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            DECLARE
                match_semester_id uuid;
            BEGIN
                SELECT buddy_match.semester_id
                INTO match_semester_id
                FROM app_private.matches AS buddy_match
                WHERE buddy_match.id = NEW.match_id;
                IF match_semester_id IS NULL
                   OR (NEW.semester_id IS NOT NULL
                       AND NEW.semester_id IS DISTINCT FROM match_semester_id)
                THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_buddy_conversations_match_semester',
                        MESSAGE = 'Buddy conversation semester is invalid';
                END IF;
                NEW.semester_id := match_semester_id;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_buddy_conversations_stamp_semester
            BEFORE INSERT OR UPDATE OF match_id, semester_id
            ON app_private.buddy_conversations
            FOR EACH ROW EXECUTE FUNCTION app_private.stamp_conversation_semester()
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.enforce_semester_boundary()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            BEGIN
                IF NEW.id IS DISTINCT FROM OLD.id
                   OR NEW.started_at IS DISTINCT FROM OLD.started_at
                   OR NEW.created_at IS DISTINCT FROM OLD.created_at
                   OR NEW.student_accounts_created < OLD.student_accounts_created
                   OR (OLD.first_student_created_at IS NOT NULL
                       AND NEW.first_student_created_at IS DISTINCT FROM OLD.first_student_created_at)
                   OR (OLD.status = 'CLOSED' AND NEW IS DISTINCT FROM OLD)
                   OR (OLD.status = 'CURRENT' AND NEW.status = 'CURRENT'
                       AND (NEW.closed_at IS NOT NULL OR NEW.reset_operation_id IS NOT NULL))
                   OR (OLD.status = 'CURRENT' AND NEW.status NOT IN ('CURRENT', 'CLOSED'))
                THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_semesters_immutable_boundary',
                        MESSAGE = 'Semester boundary update is invalid';
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_semesters_immutable_boundary
            BEFORE UPDATE ON app_private.semesters
            FOR EACH ROW EXECUTE FUNCTION app_private.enforce_semester_boundary()
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.enforce_semester_operation()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY INVOKER
            SET search_path = ''
            AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM app_private.users AS actor
                    WHERE actor.id = NEW.admin_actor_id
                      AND actor.role = 'ADMIN'
                      AND actor.deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        CONSTRAINT = 'ck_semester_operations_admin_actor',
                        MESSAGE = 'Semester operation actor is invalid';
                END IF;
                IF TG_OP = 'UPDATE' THEN
                    IF NEW.id IS DISTINCT FROM OLD.id
                       OR NEW.operation_type IS DISTINCT FROM OLD.operation_type
                       OR NEW.semester_id IS DISTINCT FROM OLD.semester_id
                       OR NEW.admin_actor_id IS DISTINCT FROM OLD.admin_actor_id
                       OR NEW.requested_at IS DISTINCT FROM OLD.requested_at
                       OR NEW.created_at IS DISTINCT FROM OLD.created_at
                       OR (OLD.state = 'REQUESTED' AND NEW.state NOT IN ('REQUESTED', 'RUNNING', 'FAILED'))
                       OR (OLD.state = 'RUNNING' AND NEW.state NOT IN ('RUNNING', 'SUCCEEDED', 'FAILED'))
                       OR (OLD.state IN ('SUCCEEDED', 'FAILED') AND NEW IS DISTINCT FROM OLD)
                    THEN
                        RAISE EXCEPTION USING
                            ERRCODE = '23514',
                            CONSTRAINT = 'ck_semester_operations_state_transition',
                            MESSAGE = 'Semester operation update is invalid';
                    END IF;
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_semester_operations_integrity
            BEFORE INSERT OR UPDATE ON app_private.semester_operations
            FOR EACH ROW EXECUTE FUNCTION app_private.enforce_semester_operation()
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.enforce_semester_backup()
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
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_semester_backups_integrity
            BEFORE INSERT OR UPDATE ON app_private.semester_backups
            FOR EACH ROW EXECUTE FUNCTION app_private.enforce_semester_backup()
            """
        )
    )


def _secure_tables() -> None:
    for table in ("semesters", "semester_operations", "semester_backups"):
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table} FROM PUBLIC"))
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table} FROM vgu_buddy_runtime"))
        op.execute(sa.text(f"ALTER TABLE app_private.{table} ENABLE ROW LEVEL SECURITY"))
    for enum_name in (
        "semester_status",
        "semester_operation_type",
        "semester_operation_state",
        "semester_backup_state",
    ):
        op.execute(sa.text(f"REVOKE ALL ON TYPE app_private.{enum_name} FROM PUBLIC"))
        op.execute(sa.text(f"GRANT USAGE ON TYPE app_private.{enum_name} TO vgu_buddy_runtime"))

    for function_name in (
        "stamp_user_semester()",
        "stamp_match_semester()",
        "stamp_conversation_semester()",
        "enforce_semester_boundary()",
        "enforce_semester_operation()",
        "enforce_semester_backup()",
    ):
        op.execute(sa.text(f"REVOKE ALL ON FUNCTION app_private.{function_name} FROM PUBLIC"))
        op.execute(
            sa.text(f"REVOKE ALL ON FUNCTION app_private.{function_name} FROM vgu_buddy_runtime")
        )
    op.execute(sa.text(_DATA_API_REVOCATIONS))

    op.execute(sa.text("GRANT SELECT ON TABLE app_private.semesters TO vgu_buddy_runtime"))
    op.execute(
        sa.text(
            "GRANT UPDATE (student_accounts_created, first_student_created_at, updated_at) "
            "ON TABLE app_private.semesters TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE ON TABLE app_private.semester_operations "
            "TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE ON TABLE app_private.semester_backups "
            "TO vgu_buddy_runtime"
        )
    )

    for table in ("semesters", "semester_operations", "semester_backups"):
        op.execute(
            sa.text(
                f"CREATE POLICY {table}_backend_access ON app_private.{table} "
                "AS PERMISSIVE FOR ALL TO vgu_buddy_runtime USING (true) WITH CHECK (true)"
            )
        )


def upgrade() -> None:
    """Persist one current cohort and the backend-only operation state machine."""
    _create_enums()
    _create_semesters()
    _stamp_existing_cohort()
    _create_operations()
    _create_backups()
    _create_integrity_guards()
    _secure_tables()


def downgrade() -> None:
    """Remove only SEM-001 persistence and return cohort links to placeholders."""
    for table in ("semester_backups", "semester_operations", "semesters"):
        op.execute(sa.text(f"DROP POLICY {table}_backend_access ON app_private.{table}"))

    op.execute(
        sa.text("DROP TRIGGER trg_semester_backups_integrity ON app_private.semester_backups")
    )
    op.execute(sa.text("DROP FUNCTION app_private.enforce_semester_backup()"))
    op.execute(
        sa.text("DROP TRIGGER trg_semester_operations_integrity ON app_private.semester_operations")
    )
    op.execute(sa.text("DROP FUNCTION app_private.enforce_semester_operation()"))
    op.execute(sa.text("DROP TRIGGER trg_semesters_immutable_boundary ON app_private.semesters"))
    op.execute(sa.text("DROP FUNCTION app_private.enforce_semester_boundary()"))
    op.execute(sa.text("DROP TRIGGER trg_users_stamp_semester ON app_private.users"))
    op.execute(sa.text("DROP FUNCTION app_private.stamp_user_semester()"))
    op.execute(
        sa.text(
            "DROP TRIGGER trg_buddy_conversations_stamp_semester ON app_private.buddy_conversations"
        )
    )
    op.execute(sa.text("DROP FUNCTION app_private.stamp_conversation_semester()"))
    op.execute(sa.text("DROP TRIGGER trg_matches_stamp_semester ON app_private.matches"))
    op.execute(sa.text("DROP FUNCTION app_private.stamp_match_semester()"))

    op.drop_constraint(
        "fk_semesters_reset_operation_id_semester_operations",
        "semesters",
        type_="foreignkey",
        schema=_SCHEMA,
    )
    op.drop_constraint(
        "fk_semester_operations_backup_id_semester_backups",
        "semester_operations",
        type_="foreignkey",
        schema=_SCHEMA,
    )

    for index_name in (
        "ix_semester_backups_state_expires_at",
        "ix_semester_backups_restore_operation_id",
        "ix_semester_backups_restored_by_admin_id",
        "ix_semester_backups_created_by_operation_id",
        "ix_semester_backups_source_semester_id",
    ):
        op.drop_index(index_name, table_name="semester_backups", schema=_SCHEMA)
    op.drop_table("semester_backups", schema=_SCHEMA)

    for index_name in (
        "uq_semester_operations_running",
        "ix_semester_operations_state_requested_at",
        "ix_semester_operations_backup_id",
        "ix_semester_operations_admin_actor_id",
        "ix_semester_operations_semester_id",
    ):
        op.drop_index(index_name, table_name="semester_operations", schema=_SCHEMA)
    op.drop_table("semester_operations", schema=_SCHEMA)

    op.drop_index(
        "ix_buddy_conversations_semester_id",
        table_name="buddy_conversations",
        schema=_SCHEMA,
    )
    op.drop_constraint(
        "fk_buddy_conversations_semester_id_semesters",
        "buddy_conversations",
        type_="foreignkey",
        schema=_SCHEMA,
    )
    op.alter_column(
        "buddy_conversations",
        "semester_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema=_SCHEMA,
    )
    op.drop_index("ix_matches_semester_id", table_name="matches", schema=_SCHEMA)
    op.drop_constraint(
        "fk_matches_semester_id_semesters",
        "matches",
        type_="foreignkey",
        schema=_SCHEMA,
    )
    op.alter_column(
        "matches",
        "semester_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema=_SCHEMA,
    )
    op.drop_index("ix_users_semester_id", table_name="users", schema=_SCHEMA)
    op.drop_constraint(
        "ck_users_role_semester",
        "users",
        type_="check",
        schema=_SCHEMA,
    )
    op.drop_constraint(
        "fk_users_semester_id_semesters",
        "users",
        type_="foreignkey",
        schema=_SCHEMA,
    )
    op.drop_column("users", "semester_id", schema=_SCHEMA)

    op.drop_index("ix_semesters_reset_operation_id", table_name="semesters", schema=_SCHEMA)
    op.drop_index("uq_semesters_current", table_name="semesters", schema=_SCHEMA)
    op.drop_table("semesters", schema=_SCHEMA)

    op.execute(sa.text("DROP TYPE app_private.semester_backup_state"))
    op.execute(sa.text("DROP TYPE app_private.semester_operation_state"))
    op.execute(sa.text("DROP TYPE app_private.semester_operation_type"))
    op.execute(sa.text("DROP TYPE app_private.semester_status"))
