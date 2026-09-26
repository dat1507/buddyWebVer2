"""Add independent activities and profile-owned custom preferences.

Revision ID: 0011_preference_persistence
Revises: 0010_edge_email_outbox_functions
Create Date: 2026-09-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_preference_persistence"
down_revision: str | Sequence[str] | None = "0010_edge_email_outbox_functions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_TABLES = (
    "activities",
    "profile_activities",
    "profile_custom_preferences",
)

_PREFERENCE_KIND_ENUM = postgresql.ENUM(
    "INTEREST",
    "LANGUAGE",
    "ACTIVITY",
    name="preference_kind",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)
_LANGUAGE_PROFICIENCY_ENUM = postgresql.ENUM(
    "native",
    "fluent",
    "intermediate",
    "beginner",
    name="language_proficiency",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
    table_name text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            FOREACH table_name IN ARRAY ARRAY[
                'activities',
                'profile_activities',
                'profile_custom_preferences'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON TABLE app_private.%I FROM %I',
                    table_name,
                    api_role
                );
            END LOOP;
            EXECUTE format(
                'REVOKE ALL ON TYPE app_private.preference_kind FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$
"""

_VALIDATE_LEGACY_ACTIVITY_IDS = r"""
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM app_private.student_profiles AS profile
        WHERE profile.preferences ? 'preferred_activity_ids'
          AND jsonb_typeof(profile.preferences -> 'preferred_activity_ids')
              IS DISTINCT FROM 'array'
    ) THEN
        RAISE EXCEPTION
            'cannot migrate preferred activities: preferred_activity_ids must be an array'
            USING ERRCODE = '22023';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM app_private.student_profiles AS profile
        CROSS JOIN LATERAL jsonb_array_elements(
            profile.preferences -> 'preferred_activity_ids'
        ) AS item(value)
        WHERE profile.preferences ? 'preferred_activity_ids'
          AND (
              jsonb_typeof(item.value) IS DISTINCT FROM 'string'
              OR CASE
                  WHEN jsonb_typeof(item.value) = 'string'
                  THEN item.value #>> '{}'
                  ELSE NULL
              END !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          )
    ) THEN
        RAISE EXCEPTION
            'cannot migrate preferred activities: every value must be a canonical UUID string'
            USING ERRCODE = '22023';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM app_private.student_profiles AS profile
        CROSS JOIN LATERAL jsonb_array_elements_text(
            profile.preferences -> 'preferred_activity_ids'
        ) AS legacy(activity_id)
        LEFT JOIN app_private.interests AS interest
          ON interest.id::text = lower(legacy.activity_id)
        WHERE profile.preferences ? 'preferred_activity_ids'
          AND interest.id IS NULL
    ) THEN
        RAISE EXCEPTION
            'cannot migrate preferred activities: at least one legacy Interest ID is orphaned'
            USING ERRCODE = '23503';
    END IF;
END
$$
"""

_SEED_ACTIVITIES_FROM_INTERESTS = """
INSERT INTO app_private.activities (
    id,
    code,
    label_en,
    label_de,
    is_active,
    created_at,
    updated_at,
    deleted_at
)
SELECT
    interest.id,
    interest.code,
    interest.label_en,
    interest.label_de,
    interest.is_active,
    interest.created_at,
    interest.updated_at,
    interest.deleted_at
FROM app_private.interests AS interest
ON CONFLICT (code) DO UPDATE
SET
    label_en = EXCLUDED.label_en,
    label_de = EXCLUDED.label_de,
    updated_at = now()
WHERE
    activities.label_en IS DISTINCT FROM EXCLUDED.label_en
    OR activities.label_de IS DISTINCT FROM EXCLUDED.label_de
"""

_MIGRATE_PROFILE_ACTIVITIES = """
INSERT INTO app_private.profile_activities (profile_id, activity_id)
SELECT DISTINCT
    profile.id,
    activity.id
FROM app_private.student_profiles AS profile
CROSS JOIN LATERAL jsonb_array_elements_text(
    profile.preferences -> 'preferred_activity_ids'
) AS legacy(activity_id)
JOIN app_private.interests AS interest
  ON interest.id = legacy.activity_id::uuid
JOIN app_private.activities AS activity
  ON activity.code = interest.code
WHERE profile.preferences ? 'preferred_activity_ids'
ON CONFLICT (profile_id, activity_id) DO NOTHING
"""


def _create_preference_kind() -> None:
    op.execute(
        sa.text(
            "CREATE TYPE app_private.preference_kind "
            "AS ENUM ('INTEREST', 'LANGUAGE', 'ACTIVITY')"
        )
    )


def _create_activities() -> None:
    op.create_table(
        "activities",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label_en", sa.Text(), nullable=False),
        sa.Column("label_de", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
            "code ~ '^[a-z0-9]+(-[a-z0-9]+|_[a-z0-9]+)*$' "
            "AND char_length(code) <= 64",
            name="ck_activities_code_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_activities_label_en_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_activities_label_de_length",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
        sa.UniqueConstraint("code", name=op.f("uq_activities_code")),
        schema=_APPLICATION_SCHEMA,
    )


def _create_profile_activities() -> None:
    op.create_table(
        "profile_activities",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["app_private.activities.id"],
            name=op.f("fk_profile_activities_activity_id_activities"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_profile_activities_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "activity_id",
            name=op.f("pk_profile_activities"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_profile_activities_activity_id",
        "profile_activities",
        ["activity_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _create_profile_custom_preferences() -> None:
    op.create_table(
        "profile_custom_preferences",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("kind", _PREFERENCE_KIND_ENUM, nullable=False),
        sa.Column("display_label", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.Text(), nullable=False),
        sa.Column("proficiency", _LANGUAGE_PROFICIENCY_ENUM, nullable=True),
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
            "char_length(btrim(display_label)) BETWEEN 1 AND 120",
            name="ck_profile_custom_preferences_display_label_length",
        ),
        sa.CheckConstraint(
            "char_length(normalized_key) BETWEEN 1 AND 255 "
            "AND normalized_key = btrim(normalized_key)",
            name="ck_profile_custom_preferences_normalized_key_length",
        ),
        sa.CheckConstraint(
            "(kind = 'LANGUAGE' AND proficiency IS NOT NULL) "
            "OR (kind IN ('INTEREST', 'ACTIVITY') AND proficiency IS NULL)",
            name="ck_profile_custom_preferences_language_proficiency_scope",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f(
                "fk_profile_custom_preferences_profile_id_student_profiles"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_custom_preferences")),
        sa.UniqueConstraint(
            "profile_id",
            "kind",
            "normalized_key",
            name="uq_profile_custom_preferences_profile_kind_key",
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_profile_custom_preferences_kind_normalized_key",
        "profile_custom_preferences",
        ["kind", "normalized_key"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _secure_preference_tables() -> None:
    for table_name in _TABLES:
        op.execute(sa.text(f"REVOKE ALL ON TABLE app_private.{table_name} FROM PUBLIC"))
        op.execute(
            sa.text(
                f"REVOKE ALL ON TABLE app_private.{table_name} FROM vgu_buddy_runtime"
            )
        )
        op.execute(
            sa.text(f"ALTER TABLE app_private.{table_name} ENABLE ROW LEVEL SECURITY")
        )

    op.execute(sa.text("REVOKE ALL ON TYPE app_private.preference_kind FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    op.execute(sa.text("GRANT SELECT ON TABLE app_private.activities TO vgu_buddy_runtime"))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, DELETE ON TABLE app_private.profile_activities "
            "TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE "
            "ON TABLE app_private.profile_custom_preferences TO vgu_buddy_runtime"
        )
    )
    op.execute(
        sa.text("GRANT USAGE ON TYPE app_private.preference_kind TO vgu_buddy_runtime")
    )

    op.execute(
        sa.text(
            """
            CREATE POLICY activities_backend_read
            ON app_private.activities
            AS PERMISSIVE
            FOR SELECT
            TO vgu_buddy_runtime
            USING (true)
            """
        )
    )
    for table_name in ("profile_activities", "profile_custom_preferences"):
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_backend_access
                ON app_private.{table_name}
                AS PERMISSIVE
                FOR ALL
                TO vgu_buddy_runtime
                USING (true)
                WITH CHECK (true)
                """
            )
        )


def upgrade() -> None:
    """Create preference persistence and migrate valid legacy activity IDs."""
    _create_preference_kind()
    _create_activities()
    _create_profile_activities()
    _create_profile_custom_preferences()
    op.execute(sa.text(_VALIDATE_LEGACY_ACTIVITY_IDS))
    op.execute(sa.text(_SEED_ACTIVITIES_FROM_INTERESTS))
    op.execute(sa.text(_MIGRATE_PROFILE_ACTIVITIES))
    _secure_preference_tables()


def downgrade() -> None:
    """Remove PREF-001 persistence while retaining the legacy profile JSON."""
    op.execute(
        sa.text(
            "DROP POLICY profile_custom_preferences_backend_access "
            "ON app_private.profile_custom_preferences"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY profile_activities_backend_access "
            "ON app_private.profile_activities"
        )
    )
    op.execute(
        sa.text("DROP POLICY activities_backend_read ON app_private.activities")
    )
    op.drop_index(
        "ix_profile_custom_preferences_kind_normalized_key",
        table_name="profile_custom_preferences",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("profile_custom_preferences", schema=_APPLICATION_SCHEMA)
    op.drop_index(
        "ix_profile_activities_activity_id",
        table_name="profile_activities",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("profile_activities", schema=_APPLICATION_SCHEMA)
    op.drop_table("activities", schema=_APPLICATION_SCHEMA)
    op.execute(sa.text("DROP TYPE app_private.preference_kind"))
