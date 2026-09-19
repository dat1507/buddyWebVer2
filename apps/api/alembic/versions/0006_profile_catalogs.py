"""Create canonical profile, catalog, relation and photo persistence.

Revision ID: 0006_profile_catalogs
Revises: 0005_storage_buckets
Create Date: 2026-09-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_profile_catalogs"
down_revision: str | Sequence[str] | None = "0005_storage_buckets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMA = "app_private"
_TABLES = (
    "student_profiles",
    "interests",
    "languages",
    "profile_interests",
    "profile_languages",
    "profile_photos",
)
_ENUM_TYPES = (
    "student_type",
    "language_proficiency",
    "profile_photo_processing_status",
)

_STUDENT_TYPE_ENUM = postgresql.ENUM(
    "VIETNAMESE",
    "INTERNATIONAL",
    name="student_type",
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
_PHOTO_PROCESSING_STATUS_ENUM = postgresql.ENUM(
    "READY",
    "FAILED",
    name="profile_photo_processing_status",
    schema=_APPLICATION_SCHEMA,
    create_type=False,
)

_DATA_API_REVOCATIONS = """
DO $$
DECLARE
    api_role text;
    table_name text;
    type_name text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            FOREACH table_name IN ARRAY ARRAY[
                'student_profiles',
                'interests',
                'languages',
                'profile_interests',
                'profile_languages',
                'profile_photos'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON TABLE app_private.%I FROM %I',
                    table_name,
                    api_role
                );
            END LOOP;
            FOREACH type_name IN ARRAY ARRAY[
                'student_type',
                'language_proficiency',
                'profile_photo_processing_status'
            ]
            LOOP
                EXECUTE format(
                    'REVOKE ALL ON TYPE app_private.%I FROM %I',
                    type_name,
                    api_role
                );
            END LOOP;
        END IF;
    END LOOP;
END
$$
"""

_INTEREST_SEED = """
INSERT INTO app_private.interests (code, label_en, label_de, category)
VALUES
    ('art', 'Art', 'Kunst', 'creative'),
    ('cooking', 'Cooking', 'Kochen', 'lifestyle'),
    ('gaming', 'Gaming', 'Gaming', 'entertainment'),
    ('hiking', 'Hiking', 'Wandern', 'outdoors'),
    ('language-exchange', 'Language Exchange', 'Sprachaustausch', 'social'),
    ('movies', 'Movies', 'Filme', 'entertainment'),
    ('music', 'Music', 'Musik', 'culture'),
    ('photography', 'Photography', 'Fotografie', 'creative'),
    ('reading', 'Reading', 'Lesen', 'culture'),
    ('sports', 'Sports', 'Sport', 'activity'),
    ('technology', 'Technology', 'Technologie', 'academic'),
    ('travel', 'Travel', 'Reisen', 'lifestyle'),
    ('volunteering', 'Volunteering', 'Ehrenamtliches Engagement', 'social')
ON CONFLICT (code) DO UPDATE
SET
    label_en = EXCLUDED.label_en,
    label_de = EXCLUDED.label_de,
    category = EXCLUDED.category,
    updated_at = now()
WHERE
    interests.label_en IS DISTINCT FROM EXCLUDED.label_en
    OR interests.label_de IS DISTINCT FROM EXCLUDED.label_de
    OR interests.category IS DISTINCT FROM EXCLUDED.category
"""

_LANGUAGE_SEED = """
INSERT INTO app_private.languages (code, label_en, label_de)
VALUES
    ('de', 'German', 'Deutsch'),
    ('en', 'English', 'Englisch'),
    ('es', 'Spanish', 'Spanisch'),
    ('fr', 'French', 'Französisch'),
    ('ja', 'Japanese', 'Japanisch'),
    ('ko', 'Korean', 'Koreanisch'),
    ('vi', 'Vietnamese', 'Vietnamesisch'),
    ('zh', 'Chinese', 'Chinesisch')
ON CONFLICT (code) DO UPDATE
SET
    label_en = EXCLUDED.label_en,
    label_de = EXCLUDED.label_de
WHERE
    languages.label_en IS DISTINCT FROM EXCLUDED.label_en
    OR languages.label_de IS DISTINCT FROM EXCLUDED.label_de
"""


def _create_enum_types() -> None:
    op.execute(
        sa.text(
            "CREATE TYPE app_private.student_type "
            "AS ENUM ('VIETNAMESE', 'INTERNATIONAL')"
        )
    )
    op.execute(
        sa.text(
            "CREATE TYPE app_private.language_proficiency "
            "AS ENUM ('native', 'fluent', 'intermediate', 'beginner')"
        )
    )
    op.execute(
        sa.text(
            "CREATE TYPE app_private.profile_photo_processing_status "
            "AS ENUM ('READY', 'FAILED')"
        )
    )


def _create_student_profiles() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("student_type", _STUDENT_TYPE_ENUM, nullable=True),
        sa.Column("nationality", sa.Text(), nullable=True),
        sa.Column("major", sa.Text(), nullable=True),
        sa.Column("study_year", sa.Integer(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("home_university", sa.Text(), nullable=True),
        sa.Column("arrival_date", sa.Date(), nullable=True),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("availability", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "matching_opt_in",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "full_name IS NULL OR char_length(btrim(full_name)) BETWEEN 1 AND 120",
            name="ck_student_profiles_full_name_length",
        ),
        sa.CheckConstraint(
            "display_name IS NULL OR char_length(btrim(display_name)) BETWEEN 1 AND 80",
            name="ck_student_profiles_display_name_length",
        ),
        sa.CheckConstraint(
            "study_year IS NULL OR study_year BETWEEN 1 AND 10",
            name="ck_student_profiles_study_year_range",
        ),
        sa.CheckConstraint(
            "bio IS NULL OR char_length(bio) <= 500",
            name="ck_student_profiles_bio_length",
        ),
        sa.CheckConstraint(
            "arrival_date IS NULL OR departure_date IS NULL OR departure_date >= arrival_date",
            name="ck_student_profiles_date_order",
        ),
        sa.CheckConstraint(
            "availability IS NULL OR jsonb_typeof(availability) = 'object'",
            name="ck_student_profiles_availability_object",
        ),
        sa.CheckConstraint(
            "preferences IS NULL OR jsonb_typeof(preferences) = 'object'",
            name="ck_student_profiles_preferences_object",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_student_profiles_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app_private.users.id"],
            name=op.f("fk_student_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_student_profiles_user_id")),
        schema=_APPLICATION_SCHEMA,
    )


def _create_catalogs() -> None:
    op.create_table(
        "interests",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label_en", sa.Text(), nullable=False),
        sa.Column("label_de", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
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
            name="ck_interests_code_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_interests_label_en_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_interests_label_de_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(category)) BETWEEN 1 AND 80",
            name="ck_interests_category_length",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interests")),
        sa.UniqueConstraint("code", name=op.f("uq_interests_code")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_table(
        "languages",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label_en", sa.Text(), nullable=False),
        sa.Column("label_de", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(
            "code ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="ck_languages_code_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_languages_label_en_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_languages_label_de_length",
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_languages")),
        schema=_APPLICATION_SCHEMA,
    )


def _create_profile_relations() -> None:
    op.create_table(
        "profile_interests",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("interest_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["interest_id"],
            ["app_private.interests.id"],
            name=op.f("fk_profile_interests_interest_id_interests"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_profile_interests_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "interest_id",
            name=op.f("pk_profile_interests"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_profile_interests_interest_id",
        "profile_interests",
        ["interest_id"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )
    op.create_table(
        "profile_languages",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("language_code", sa.Text(), nullable=False),
        sa.Column("proficiency", _LANGUAGE_PROFICIENCY_ENUM, nullable=False),
        sa.ForeignKeyConstraint(
            ["language_code"],
            ["app_private.languages.code"],
            name=op.f("fk_profile_languages_language_code_languages"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_profile_languages_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "profile_id",
            "language_code",
            name=op.f("pk_profile_languages"),
        ),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "ix_profile_languages_language_code",
        "profile_languages",
        ["language_code"],
        unique=False,
        schema=_APPLICATION_SCHEMA,
    )


def _create_profile_photos() -> None:
    op.create_table(
        "profile_photos",
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column(
            "bucket",
            sa.Text(),
            server_default=sa.text("'profile-images'"),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("is_avatar", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "processing_status",
            _PHOTO_PROCESSING_STATUS_ENUM,
            server_default="READY",
            nullable=False,
        ),
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
            "bucket = 'profile-images'",
            name="ck_profile_photos_profile_bucket",
        ),
        sa.CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_profile_photos_mime_type",
        ),
        sa.CheckConstraint(
            "byte_size BETWEEN 1 AND 5242880",
            name="ck_profile_photos_byte_size_range",
        ),
        sa.CheckConstraint(
            "width BETWEEN 1 AND 4096 AND height BETWEEN 1 AND 4096 "
            "AND width * height <= 16777216",
            name="ck_profile_photos_dimensions",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["app_private.student_profiles.id"],
            name=op.f("fk_profile_photos_profile_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_photos")),
        sa.UniqueConstraint("object_key", name=op.f("uq_profile_photos_object_key")),
        schema=_APPLICATION_SCHEMA,
    )
    op.create_index(
        "uq_profile_photos_one_avatar_per_profile",
        "profile_photos",
        ["profile_id"],
        unique=True,
        schema=_APPLICATION_SCHEMA,
        postgresql_where=sa.text("is_avatar AND deleted_at IS NULL"),
    )


def _secure_profile_tables() -> None:
    for table_name in _TABLES:
        op.execute(
            sa.text(f"REVOKE ALL ON TABLE app_private.{table_name} FROM PUBLIC")
        )
    for type_name in _ENUM_TYPES:
        op.execute(sa.text(f"REVOKE ALL ON TYPE app_private.{type_name} FROM PUBLIC"))
    op.execute(sa.text(_DATA_API_REVOCATIONS))
    for table_name in _TABLES:
        op.execute(
            sa.text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                f"ON TABLE app_private.{table_name} TO vgu_buddy_runtime"
            )
        )
        op.execute(
            sa.text(f"ALTER TABLE app_private.{table_name} ENABLE ROW LEVEL SECURITY")
        )
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
    for type_name in _ENUM_TYPES:
        op.execute(
            sa.text(
                f"GRANT USAGE ON TYPE app_private.{type_name} TO vgu_buddy_runtime"
            )
        )


def upgrade() -> None:
    """Create private profile persistence and seed extensible catalogs."""
    _create_enum_types()
    _create_student_profiles()
    _create_catalogs()
    _create_profile_relations()
    _create_profile_photos()
    op.execute(sa.text(_INTEREST_SEED))
    op.execute(sa.text(_LANGUAGE_SEED))
    _secure_profile_tables()


def downgrade() -> None:
    """Remove profile persistence without modifying account or Storage state."""
    for table_name in reversed(_TABLES):
        op.execute(
            sa.text(
                f"DROP POLICY {table_name}_backend_access "
                f"ON app_private.{table_name}"
            )
        )
    op.drop_index(
        "uq_profile_photos_one_avatar_per_profile",
        table_name="profile_photos",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("profile_photos", schema=_APPLICATION_SCHEMA)
    op.drop_index(
        "ix_profile_languages_language_code",
        table_name="profile_languages",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("profile_languages", schema=_APPLICATION_SCHEMA)
    op.drop_index(
        "ix_profile_interests_interest_id",
        table_name="profile_interests",
        schema=_APPLICATION_SCHEMA,
    )
    op.drop_table("profile_interests", schema=_APPLICATION_SCHEMA)
    op.drop_table("languages", schema=_APPLICATION_SCHEMA)
    op.drop_table("interests", schema=_APPLICATION_SCHEMA)
    op.drop_table("student_profiles", schema=_APPLICATION_SCHEMA)
    op.execute(sa.text("DROP TYPE app_private.profile_photo_processing_status"))
    op.execute(sa.text("DROP TYPE app_private.language_proficiency"))
    op.execute(sa.text("DROP TYPE app_private.student_type"))
