"""Add ACTIVE Buddy Match persistence and unordered-pair uniqueness.

Revision ID: 0013_active_match_persistence
Revises: 0012_invitation_persistence
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_active_match_persistence"
down_revision: str | Sequence[str] | None = "0012_invitation_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_TABLE_NAME = "matches"
_MATCH_STATUS_ENUM = postgresql.ENUM(
    "ACTIVE",
    name="match_status",
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
            EXECUTE format('REVOKE ALL ON TABLE app_private.matches FROM %I', api_role);
            EXECUTE format('REVOKE ALL ON TYPE app_private.match_status FROM %I', api_role);
        END IF;
    END LOOP;
END
$$
"""


def _create_match_status() -> None:
    op.execute(sa.text("CREATE TYPE app_private.match_status AS ENUM ('ACTIVE')"))


def _create_matches() -> None:
    op.create_table(
        _TABLE_NAME,
        sa.Column("participant_one_user_id", sa.Uuid(), nullable=False),
        sa.Column("participant_two_user_id", sa.Uuid(), nullable=False),
        sa.Column("participant_one_profile_id", sa.Uuid(), nullable=False),
        sa.Column("participant_two_profile_id", sa.Uuid(), nullable=False),
        sa.Column(
            "pair_low_user_id",
            sa.Uuid(),
            sa.Computed(
                "LEAST(participant_one_user_id, participant_two_user_id)",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "pair_high_user_id",
            sa.Uuid(),
            sa.Computed(
                "GREATEST(participant_one_user_id, participant_two_user_id)",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            _MATCH_STATUS_ENUM,
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column("accepted_invitation_id", sa.Uuid(), nullable=False),
        # SEM-001 owns the authoritative semester table and will add/backfill
        # the FK. BUDDY-001 persists the planned nullable linkage without
        # inventing a competing semester lifecycle.
        sa.Column("semester_id", sa.Uuid(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
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
            "participant_one_user_id <> participant_two_user_id",
            name="ck_matches_distinct_users",
        ),
        sa.CheckConstraint(
            "participant_one_profile_id <> participant_two_profile_id",
            name="ck_matches_distinct_profiles",
        ),
        sa.CheckConstraint(
            "pair_low_user_id < pair_high_user_id",
            name="ck_matches_canonical_pair_order",
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_matches_score_range",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(score_breakdown) = 'object'",
            name="ck_matches_score_breakdown_object",
        ),
        sa.ForeignKeyConstraint(
            ["participant_one_user_id"],
            ["app_private.users.id"],
            name=op.f("fk_matches_participant_one_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["participant_two_user_id"],
            ["app_private.users.id"],
            name=op.f("fk_matches_participant_two_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["participant_one_profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_matches_participant_one_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["participant_two_profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_matches_participant_two_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_invitation_id"],
            ["app_private.matching_invitations.id"],
            name=op.f("fk_matches_accepted_invitation_id_matching_invitations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matches")),
        sa.UniqueConstraint(
            "accepted_invitation_id",
            name=op.f("uq_matches_accepted_invitation_id"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "uq_matches_active_pair",
        _TABLE_NAME,
        ["pair_low_user_id", "pair_high_user_id"],
        unique=True,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_matches_participant_one_status_activated_at",
        _TABLE_NAME,
        ["participant_one_user_id", "status", "activated_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_matches_participant_two_status_activated_at",
        _TABLE_NAME,
        ["participant_two_user_id", "status", "activated_at"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_matches_participant_one_profile_id",
        _TABLE_NAME,
        ["participant_one_profile_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_matches_participant_two_profile_id",
        _TABLE_NAME,
        ["participant_two_profile_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _secure_matches() -> None:
    op.execute(sa.text("REVOKE ALL ON TABLE app_private.matches FROM PUBLIC"))
    op.execute(sa.text("REVOKE ALL ON TABLE app_private.matches FROM vgu_buddy_runtime"))
    op.execute(sa.text("REVOKE ALL ON TYPE app_private.match_status FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT ON TABLE app_private.matches TO vgu_buddy_runtime"
        )
    )
    op.execute(sa.text("GRANT USAGE ON TYPE app_private.match_status TO vgu_buddy_runtime"))
    op.execute(sa.text("ALTER TABLE app_private.matches ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY matches_backend_access
            ON app_private.matches
            AS PERMISSIVE
            FOR ALL
            TO vgu_buddy_runtime
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def upgrade() -> None:
    """Create the immutable ACTIVE Match record and backend access boundary."""
    _create_match_status()
    _create_matches()
    _secure_matches()


def downgrade() -> None:
    """Remove only BUDDY-001 persistence objects."""
    op.execute(sa.text("DROP POLICY matches_backend_access ON app_private.matches"))
    op.drop_index(
        "ix_matches_participant_two_profile_id",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_matches_participant_one_profile_id",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_matches_participant_two_status_activated_at",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "ix_matches_participant_one_status_activated_at",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_index(
        "uq_matches_active_pair",
        table_name=_TABLE_NAME,
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table(_TABLE_NAME, schema=_APPLICATION_SCHEMA)
    op.execute(sa.text("DROP TYPE app_private.match_status"))
