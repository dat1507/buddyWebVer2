"""Schema-contract tests for canonical student profiles and owned photos."""

from datetime import date, datetime
from typing import cast, get_args, get_type_hints
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateIndex, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import (
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    StudentType,
    UserRole,
)


def _constraint_names(table: Table) -> set[str]:
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_profile_enums_are_separate_from_account_role_and_nationality() -> None:
    assert tuple(StudentType) == (StudentType.VIETNAMESE, StudentType.INTERNATIONAL)
    assert tuple(ProfilePhotoProcessingStatus) == (
        ProfilePhotoProcessingStatus.READY,
        ProfilePhotoProcessingStatus.FAILED,
    )
    assert not set(StudentType).intersection(UserRole)


def test_student_profile_has_one_user_owner_and_only_profile_fields() -> None:
    table = cast(Table, StudentProfile.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "student_profiles"
    assert set(table.columns.keys()) == {
        "user_id",
        "full_name",
        "display_name",
        "student_type",
        "nationality",
        "major",
        "study_year",
        "bio",
        "home_university",
        "arrival_date",
        "departure_date",
        "availability",
        "preferences",
        "matching_opt_in",
        "version",
        "onboarding_completed_at",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert not {"password", "password_hash", "credential", "gender", "role"}.intersection(
        table.columns.keys()
    )

    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert len(foreign_keys) == 1
    assert foreign_keys[0].name == "fk_student_profiles_user_id_users"
    assert foreign_keys[0].ondelete == "CASCADE"
    assert tuple(element.target_fullname for element in foreign_keys[0].elements) == (
        "app_private.users.id",
    )

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns == {("user_id",)}


def test_student_profile_supports_nullable_drafts_and_bounded_fields() -> None:
    table = cast(Table, StudentProfile.__table__)

    nullable_draft_fields = {
        "full_name",
        "display_name",
        "student_type",
        "nationality",
        "major",
        "study_year",
        "bio",
        "home_university",
        "arrival_date",
        "departure_date",
        "availability",
        "preferences",
        "onboarding_completed_at",
    }
    assert all(table.c[name].nullable for name in nullable_draft_fields)
    assert table.c.user_id.nullable is False
    assert isinstance(table.c.student_type.type, Enum)
    assert table.c.student_type.type.enum_class is StudentType
    assert table.c.student_type.type.enums == ["VIETNAMESE", "INTERNATIONAL"]
    assert table.c.student_type.type.schema == APPLICATION_SCHEMA
    assert isinstance(table.c.availability.type, JSONB)
    assert isinstance(table.c.preferences.type, JSONB)
    assert _constraint_names(table) == {
        "ck_student_profiles_full_name_length",
        "ck_student_profiles_display_name_length",
        "ck_student_profiles_study_year_range",
        "ck_student_profiles_bio_length",
        "ck_student_profiles_date_order",
        "ck_student_profiles_availability_object",
        "ck_student_profiles_preferences_object",
        "ck_student_profiles_version_positive",
    }


def test_student_profile_matching_defaults_and_domain_annotations() -> None:
    table = cast(Table, StudentProfile.__table__)
    matching_opt_in = table.c.matching_opt_in
    version = table.c.version

    assert isinstance(matching_opt_in.type, Boolean)
    assert matching_opt_in.nullable is False
    assert cast(ColumnDefault, matching_opt_in.default).arg is False
    assert str(cast(DefaultClause, matching_opt_in.server_default).arg) == "false"
    assert isinstance(version.type, Integer)
    assert version.nullable is False
    assert cast(ColumnDefault, version.default).arg == 1
    assert str(cast(DefaultClause, version.server_default).arg) == "1"

    annotations = get_type_hints(StudentProfile)
    assert get_args(annotations["user_id"]) == (UUID,)
    assert get_args(annotations["student_type"]) == (StudentType | None,)
    assert get_args(annotations["arrival_date"]) == (date | None,)
    assert get_args(annotations["onboarding_completed_at"]) == (datetime | None,)


def test_profile_photo_owns_private_validated_image_metadata() -> None:
    table = cast(Table, ProfilePhoto.__table__)

    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "profile_photos"
    assert set(table.columns.keys()) == {
        "profile_id",
        "bucket",
        "object_key",
        "mime_type",
        "byte_size",
        "width",
        "height",
        "is_avatar",
        "processing_status",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert isinstance(table.c.profile_id.type, Uuid)
    assert table.c.profile_id.nullable is False
    assert isinstance(table.c.bucket.type, Text)
    assert str(cast(DefaultClause, table.c.bucket.server_default).arg) == "'profile-images'"
    assert isinstance(table.c.object_key.type, Text)
    assert isinstance(table.c.mime_type.type, Text)
    assert isinstance(table.c.byte_size.type, Integer)
    assert isinstance(table.c.width.type, Integer)
    assert isinstance(table.c.height.type, Integer)

    foreign_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )
    assert foreign_key.name == "fk_profile_photos_profile_id_student_profiles"
    assert foreign_key.ondelete == "CASCADE"
    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "app_private.student_profiles.id",
    )

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns == {("object_key",)}
    assert _constraint_names(table) == {
        "ck_profile_photos_profile_bucket",
        "ck_profile_photos_mime_type",
        "ck_profile_photos_byte_size_range",
        "ck_profile_photos_dimensions",
    }


def test_profile_photo_avatar_and_processing_contract() -> None:
    table = cast(Table, ProfilePhoto.__table__)
    is_avatar = table.c.is_avatar
    processing_status = table.c.processing_status

    assert isinstance(is_avatar.type, Boolean)
    assert is_avatar.nullable is False
    assert cast(ColumnDefault, is_avatar.default).arg is False
    assert str(cast(DefaultClause, is_avatar.server_default).arg) == "false"
    assert isinstance(processing_status.type, Enum)
    assert processing_status.type.enum_class is ProfilePhotoProcessingStatus
    assert processing_status.type.enums == ["READY", "FAILED"]
    assert processing_status.type.schema == APPLICATION_SCHEMA
    assert cast(ColumnDefault, processing_status.default).arg is ProfilePhotoProcessingStatus.READY
    assert str(cast(DefaultClause, processing_status.server_default).arg) == "READY"

    assert len(table.indexes) == 1
    avatar_index = next(iter(table.indexes))
    assert avatar_index.name == "uq_profile_photos_one_avatar_per_profile"
    assert avatar_index.unique is True
    assert tuple(column.name for column in avatar_index.columns) == ("profile_id",)
    assert (
        str(avatar_index.dialect_options["postgresql"]["where"])
        == "is_avatar AND deleted_at IS NULL"
    )


def test_postgresql_ddl_matches_profile_contract() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    profile_table = cast(Table, StudentProfile.__table__)
    photo_table = cast(Table, ProfilePhoto.__table__)
    profile_ddl = str(CreateTable(profile_table).compile(dialect=dialect)).lower()
    photo_ddl = str(CreateTable(photo_table).compile(dialect=dialect)).lower()
    photo_index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower() for index in photo_table.indexes
    }

    assert "create table app_private.student_profiles" in profile_ddl
    assert "user_id uuid not null" in profile_ddl
    assert "student_type app_private.student_type" in profile_ddl
    assert "foreign key(user_id) references app_private.users (id) on delete cascade" in profile_ddl
    assert "constraint uq_student_profiles_user_id unique (user_id)" in profile_ddl
    assert "matching_opt_in boolean default false not null" in profile_ddl
    assert "version integer default 1 not null" in profile_ddl
    assert "create table app_private.profile_photos" in photo_ddl
    assert "profile_id uuid not null" in photo_ddl
    assert "bucket text default 'profile-images' not null" in photo_ddl
    assert (
        "processing_status app_private.profile_photo_processing_status default 'ready' not null"
        in photo_ddl
    )
    assert (
        "foreign key(profile_id) references app_private.student_profiles (id) on delete cascade"
        in photo_ddl
    )
    assert "constraint uq_profile_photos_object_key unique (object_key)" in photo_ddl
    assert photo_index_ddl == {
        "create unique index uq_profile_photos_one_avatar_per_profile "
        "on app_private.profile_photos (profile_id) where is_avatar and deleted_at is null"
    }
