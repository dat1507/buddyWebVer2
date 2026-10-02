"""Add the guarded semester reset and database write barrier.

Revision ID: 0019_semester_reset_execution
Revises: 0018_backup_verification
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_semester_reset_execution"
down_revision: str | Sequence[str] | None = "0018_backup_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "app_private"
_BARRIER_FUNCTION = "acquire_semester_write_barrier()"
_RESET_FUNCTION = "execute_semester_reset(uuid, uuid, uuid, integer)"
_BARRIER_TABLES = (
    "users",
    "email_verification_tokens",
    "refresh_sessions",
    "student_profiles",
    "profile_photos",
    "profile_interests",
    "profile_languages",
    "profile_activities",
    "profile_custom_preferences",
    "event_registrations",
    "matching_invitations",
    "matches",
    "buddy_conversations",
    "buddy_messages",
    "transactional_outbox",
)


def _create_write_barrier() -> None:
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.acquire_semester_write_barrier()
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

                PERFORM pg_catalog.pg_advisory_xact_lock_shared(
                    pg_catalog.hashtextextended('vgu-buddy:semester-write-barrier:v1', 0)
                );
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END
            $$
            """
        )
    )
    for table_name in _BARRIER_TABLES:
        op.execute(
            sa.text(
                f"CREATE TRIGGER trg_{table_name}_semester_write_barrier "
                f"BEFORE INSERT OR UPDATE OR DELETE ON app_private.{table_name} "
                "FOR EACH ROW EXECUTE FUNCTION app_private.acquire_semester_write_barrier()"
            )
        )


def _create_reset_function() -> None:
    op.execute(
        sa.text(
            """
            CREATE FUNCTION app_private.execute_semester_reset(
                requested_operation_id uuid,
                requested_backup_id uuid,
                requested_admin_id uuid,
                avatar_objects_processed integer
            )
            RETURNS jsonb
            LANGUAGE plpgsql
            SECURITY DEFINER
            SET search_path = ''
            AS $$
            DECLARE
                reset_operation app_private.semester_operations%ROWTYPE;
                reset_backup app_private.semester_backups%ROWTYPE;
                source_semester app_private.semesters%ROWTYPE;
                completion_time timestamptz;
                new_semester_id uuid;
                affected jsonb;
                summary jsonb;
                removed bigint;
            BEGIN
                IF NOT pg_catalog.pg_try_advisory_xact_lock(
                    pg_catalog.hashtextextended('vgu-buddy:semester-write-barrier:v1', 0)
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '55P03',
                        MESSAGE = 'Semester reset write barrier is busy';
                END IF;

                SELECT operation.*
                INTO reset_operation
                FROM app_private.semester_operations AS operation
                WHERE operation.id = requested_operation_id
                FOR UPDATE;
                IF NOT FOUND THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset operation is invalid';
                END IF;

                SELECT backup.*
                INTO reset_backup
                FROM app_private.semester_backups AS backup
                WHERE backup.id = requested_backup_id
                FOR UPDATE;
                IF NOT FOUND THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset backup is invalid';
                END IF;

                SELECT semester.*
                INTO source_semester
                FROM app_private.semesters AS semester
                WHERE semester.id = reset_operation.semester_id
                FOR UPDATE;
                IF NOT FOUND THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset boundary is invalid';
                END IF;

                IF reset_operation.state = 'SUCCEEDED' THEN
                    IF reset_operation.operation_type <> 'RESET'
                       OR reset_operation.backup_id IS DISTINCT FROM requested_backup_id
                       OR source_semester.status <> 'CLOSED'
                       OR source_semester.reset_operation_id IS DISTINCT FROM requested_operation_id
                    THEN
                        RAISE EXCEPTION USING ERRCODE = '23514',
                            MESSAGE = 'Completed semester reset metadata is invalid';
                    END IF;
                    RETURN reset_operation.result_summary;
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM app_private.users AS actor
                    WHERE actor.id = requested_admin_id
                      AND actor.role = 'ADMIN'
                      AND actor.is_active
                      AND actor.deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION USING ERRCODE = '42501',
                        MESSAGE = 'Semester reset actor is invalid';
                END IF;

                IF reset_operation.operation_type <> 'RESET'
                   OR reset_operation.state <> 'RUNNING'
                   OR reset_operation.admin_actor_id IS DISTINCT FROM requested_admin_id
                   OR reset_operation.backup_id IS DISTINCT FROM requested_backup_id
                   OR source_semester.status <> 'CURRENT'
                   OR source_semester.reset_operation_id IS NOT NULL
                   OR reset_backup.created_by_operation_id IS DISTINCT FROM requested_operation_id
                   OR reset_backup.source_semester_id IS DISTINCT FROM source_semester.id
                   OR reset_backup.source_boundary_at IS DISTINCT FROM source_semester.started_at
                   OR reset_backup.state <> 'CREATING'
                   OR reset_backup.verified_at IS NULL
                   OR reset_backup.expires_at IS NOT NULL
                   OR reset_backup.failure_code IS NOT NULL
                   OR reset_backup.database_manifest_location IS NULL
                   OR reset_backup.database_manifest_checksum IS NULL
                   OR reset_backup.avatar_manifest_location IS NULL
                   OR reset_backup.avatar_manifest_checksum IS NULL
                   OR avatar_objects_processed < 0
                   OR avatar_objects_processed <> reset_backup.avatar_object_count
                THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset precondition failed';
                END IF;

                affected := pg_catalog.jsonb_build_object(
                    'users', (
                        SELECT pg_catalog.count(*) FROM app_private.users
                        WHERE role = 'USER' AND semester_id = source_semester.id
                    ),
                    'email_verification_tokens', (
                        SELECT pg_catalog.count(*) FROM app_private.email_verification_tokens
                        WHERE user_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    ),
                    'refresh_sessions', (
                        SELECT pg_catalog.count(*) FROM app_private.refresh_sessions
                        WHERE user_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    ),
                    'student_profiles', (
                        SELECT pg_catalog.count(*) FROM app_private.student_profiles
                        WHERE user_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    ),
                    'profile_photos', (
                        SELECT pg_catalog.count(*) FROM app_private.profile_photos
                        WHERE profile_id IN (
                            SELECT profile.id FROM app_private.student_profiles AS profile
                            JOIN app_private.users AS owner ON owner.id = profile.user_id
                            WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                        )
                    ),
                    'profile_interests', (
                        SELECT pg_catalog.count(*) FROM app_private.profile_interests
                        WHERE profile_id IN (
                            SELECT profile.id FROM app_private.student_profiles AS profile
                            JOIN app_private.users AS owner ON owner.id = profile.user_id
                            WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                        )
                    ),
                    'profile_languages', (
                        SELECT pg_catalog.count(*) FROM app_private.profile_languages
                        WHERE profile_id IN (
                            SELECT profile.id FROM app_private.student_profiles AS profile
                            JOIN app_private.users AS owner ON owner.id = profile.user_id
                            WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                        )
                    ),
                    'profile_activities', (
                        SELECT pg_catalog.count(*) FROM app_private.profile_activities
                        WHERE profile_id IN (
                            SELECT profile.id FROM app_private.student_profiles AS profile
                            JOIN app_private.users AS owner ON owner.id = profile.user_id
                            WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                        )
                    ),
                    'profile_custom_preferences', (
                        SELECT pg_catalog.count(*) FROM app_private.profile_custom_preferences
                        WHERE profile_id IN (
                            SELECT profile.id FROM app_private.student_profiles AS profile
                            JOIN app_private.users AS owner ON owner.id = profile.user_id
                            WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                        )
                    ),
                    'event_registrations', (
                        SELECT pg_catalog.count(*) FROM app_private.event_registrations
                        WHERE user_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    ),
                    'matching_invitations', (
                        SELECT pg_catalog.count(*) FROM app_private.matching_invitations
                        WHERE sender_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        ) OR recipient_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    ),
                    'matches', (
                        SELECT pg_catalog.count(*) FROM app_private.matches
                        WHERE semester_id = source_semester.id
                    ),
                    'buddy_conversations', (
                        SELECT pg_catalog.count(*) FROM app_private.buddy_conversations
                        WHERE semester_id = source_semester.id
                    ),
                    'buddy_messages', (
                        SELECT pg_catalog.count(*) FROM app_private.buddy_messages
                        WHERE conversation_id IN (
                            SELECT id FROM app_private.buddy_conversations
                            WHERE semester_id = source_semester.id
                        )
                    ),
                    'transactional_outbox', (
                        SELECT pg_catalog.count(*) FROM app_private.transactional_outbox
                        WHERE recipient_user_id IN (
                            SELECT id FROM app_private.users
                            WHERE role = 'USER' AND semester_id = source_semester.id
                        )
                    )
                );

                IF EXISTS (
                    SELECT 1
                    FROM pg_catalog.jsonb_each_text(affected) AS current_count(table_name, value)
                    WHERE NOT reset_backup.database_row_counts ? current_count.table_name
                       OR (reset_backup.database_row_counts ->> current_count.table_name)::bigint
                          <> current_count.value::bigint
                ) THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset snapshot changed after backup';
                END IF;

                DELETE FROM app_private.buddy_messages
                WHERE conversation_id IN (
                    SELECT id FROM app_private.buddy_conversations
                    WHERE semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'buddy_messages')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.buddy_conversations
                WHERE semester_id = source_semester.id;
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'buddy_conversations')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.matches WHERE semester_id = source_semester.id;
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'matches')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.matching_invitations
                WHERE sender_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                ) OR recipient_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'matching_invitations')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.transactional_outbox
                WHERE recipient_user_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'transactional_outbox')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.event_registrations
                WHERE user_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'event_registrations')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.profile_interests
                WHERE profile_id IN (
                    SELECT profile.id FROM app_private.student_profiles AS profile
                    JOIN app_private.users AS owner ON owner.id = profile.user_id
                    WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'profile_interests')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.profile_languages
                WHERE profile_id IN (
                    SELECT profile.id FROM app_private.student_profiles AS profile
                    JOIN app_private.users AS owner ON owner.id = profile.user_id
                    WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'profile_languages')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.profile_activities
                WHERE profile_id IN (
                    SELECT profile.id FROM app_private.student_profiles AS profile
                    JOIN app_private.users AS owner ON owner.id = profile.user_id
                    WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'profile_activities')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.profile_custom_preferences
                WHERE profile_id IN (
                    SELECT profile.id FROM app_private.student_profiles AS profile
                    JOIN app_private.users AS owner ON owner.id = profile.user_id
                    WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'profile_custom_preferences')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.profile_photos
                WHERE profile_id IN (
                    SELECT profile.id FROM app_private.student_profiles AS profile
                    JOIN app_private.users AS owner ON owner.id = profile.user_id
                    WHERE owner.role = 'USER' AND owner.semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'profile_photos')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.student_profiles
                WHERE user_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'student_profiles')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.email_verification_tokens
                WHERE user_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'email_verification_tokens')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.refresh_sessions
                WHERE user_id IN (
                    SELECT id FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                );
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'refresh_sessions')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                DELETE FROM app_private.users
                WHERE role = 'USER' AND semester_id = source_semester.id;
                GET DIAGNOSTICS removed = ROW_COUNT;
                IF removed <> (affected ->> 'users')::bigint THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset delete count mismatched';
                END IF;

                IF EXISTS (
                    SELECT 1 FROM app_private.users
                    WHERE role = 'USER' AND semester_id = source_semester.id
                    UNION ALL
                    SELECT 1 FROM app_private.matches
                    WHERE semester_id = source_semester.id
                    UNION ALL
                    SELECT 1 FROM app_private.buddy_conversations
                    WHERE semester_id = source_semester.id
                ) THEN
                    RAISE EXCEPTION USING ERRCODE = '23514',
                        MESSAGE = 'Semester reset post-delete verification failed';
                END IF;

                completion_time := pg_catalog.statement_timestamp();
                UPDATE app_private.semesters
                SET status = 'CLOSED',
                    closed_at = completion_time,
                    reset_operation_id = requested_operation_id,
                    updated_at = completion_time
                WHERE id = source_semester.id;

                INSERT INTO app_private.semesters (
                    status,
                    started_at,
                    student_accounts_created,
                    first_student_created_at
                ) VALUES ('CURRENT', completion_time, 0, NULL)
                RETURNING id INTO new_semester_id;

                summary := pg_catalog.jsonb_build_object(
                    'closed_semester_id', source_semester.id,
                    'new_semester_id', new_semester_id,
                    'deleted', affected,
                    'avatar_objects_processed', avatar_objects_processed
                );
                UPDATE app_private.semester_operations
                SET state = 'SUCCEEDED',
                    completed_at = completion_time,
                    affected_counts = affected,
                    result_summary = summary,
                    failure_code = NULL,
                    updated_at = completion_time
                WHERE id = requested_operation_id;

                RETURN summary;
            END
            $$
            """
        )
    )


def _secure_functions() -> None:
    op.execute(sa.text(f"REVOKE ALL ON FUNCTION app_private.{_BARRIER_FUNCTION} FROM PUBLIC"))
    op.execute(sa.text(f"REVOKE ALL ON FUNCTION app_private.{_RESET_FUNCTION} FROM PUBLIC"))
    op.execute(
        sa.text(f"REVOKE ALL ON FUNCTION app_private.{_RESET_FUNCTION} FROM vgu_buddy_runtime")
    )
    op.execute(
        sa.text(f"GRANT EXECUTE ON FUNCTION app_private.{_RESET_FUNCTION} TO vgu_buddy_runtime")
    )
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                api_role text;
            BEGIN
                FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
                LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                        EXECUTE format(
                            'REVOKE ALL ON FUNCTION app_private.execute_semester_reset('
                            'uuid, uuid, uuid, integer) FROM %I',
                            api_role
                        );
                        EXECUTE format(
                            'REVOKE ALL ON FUNCTION app_private.acquire_semester_write_barrier() '
                            'FROM %I',
                            api_role
                        );
                    END IF;
                END LOOP;
            END
            $$
            """
        )
    )


def upgrade() -> None:
    """Install one database-enforced barrier and fixed-scope reset function."""
    _create_write_barrier()
    _create_reset_function()
    _secure_functions()


def downgrade() -> None:
    """Remove only SEM-005 execution primitives."""
    op.execute(
        sa.text(f"REVOKE ALL ON FUNCTION app_private.{_RESET_FUNCTION} FROM vgu_buddy_runtime")
    )
    op.execute(sa.text(f"DROP FUNCTION app_private.{_RESET_FUNCTION}"))
    for table_name in reversed(_BARRIER_TABLES):
        op.execute(
            sa.text(
                f"DROP TRIGGER trg_{table_name}_semester_write_barrier ON app_private.{table_name}"
            )
        )
    op.execute(sa.text(f"DROP FUNCTION app_private.{_BARRIER_FUNCTION}"))
