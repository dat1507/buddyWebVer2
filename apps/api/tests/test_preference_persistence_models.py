"""PREF-001 model contracts for independent and profile-owned preferences."""

from typing import cast

from sqlalchemy import (
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import (
    Activity,
    Interest,
    LanguageProficiency,
    PreferenceKind,
    ProfileActivity,
    ProfileCustomPreference,
)


def _foreign_keys(table: Table) -> dict[str, ForeignKeyConstraint]:
    return {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_activity_is_an_independent_localized_catalog() -> None:
    activity_table = cast(Table, Activity.__table__)
    interest_table = cast(Table, Interest.__table__)

    assert activity_table.name == "activities"
    assert activity_table is not interest_table
    assert set(activity_table.columns.keys()) == {
        "code",
        "label_en",
        "label_de",
        "is_active",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert {constraint.name for constraint in activity_table.constraints} >= {
        "pk_activities",
        "uq_activities_code",
        "ck_activities_code_format",
        "ck_activities_label_en_length",
        "ck_activities_label_de_length",
    }
    assert not activity_table.foreign_keys


def test_profile_activity_uses_a_unique_catalog_pair_and_safe_cascades() -> None:
    table = cast(Table, ProfileActivity.__table__)
    primary_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    )
    foreign_keys = _foreign_keys(table)

    assert set(table.columns.keys()) == {"profile_id", "activity_id"}
    assert isinstance(table.c.profile_id.type, Uuid)
    assert isinstance(table.c.activity_id.type, Uuid)
    assert primary_key.name == "pk_profile_activities"
    assert tuple(column.name for column in primary_key.columns) == (
        "profile_id",
        "activity_id",
    )
    assert foreign_keys[
        "fk_profile_activities_profile_id_student_profiles"
    ].ondelete == "CASCADE"
    assert foreign_keys[
        "fk_profile_activities_activity_id_activities"
    ].ondelete == "RESTRICT"
    assert {index.name: tuple(column.name for column in index.columns) for index in table.indexes} == {
        "ix_profile_activities_activity_id": ("activity_id",)
    }


def test_custom_preferences_are_owned_bounded_and_unique_per_kind() -> None:
    table = cast(Table, ProfileCustomPreference.__table__)
    foreign_keys = _foreign_keys(table)
    unique_constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert set(table.columns.keys()) == {
        "profile_id",
        "kind",
        "display_label",
        "normalized_key",
        "proficiency",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert isinstance(table.c.kind.type, Enum)
    assert table.c.kind.type.name == "preference_kind"
    assert table.c.kind.type.enums == [kind.value for kind in PreferenceKind]
    assert isinstance(table.c.proficiency.type, Enum)
    assert table.c.proficiency.type.name == "language_proficiency"
    assert table.c.proficiency.type.enums == [
        proficiency.value for proficiency in LanguageProficiency
    ]
    assert foreign_keys[
        "fk_profile_custom_preferences_profile_id_student_profiles"
    ].ondelete == "CASCADE"
    uniqueness = unique_constraints["uq_profile_custom_preferences_profile_kind_key"]
    assert tuple(column.name for column in uniqueness.columns) == (
        "profile_id",
        "kind",
        "normalized_key",
    )
    assert {constraint.name for constraint in table.constraints} >= {
        "ck_profile_custom_preferences_display_label_length",
        "ck_profile_custom_preferences_normalized_key_length",
        "ck_profile_custom_preferences_language_proficiency_scope",
    }
    assert {index.name: tuple(column.name for column in index.columns) for index in table.indexes} == {
        "ix_profile_custom_preferences_kind_normalized_key": (
            "kind",
            "normalized_key",
        )
    }


def test_postgresql_ddl_keeps_catalog_and_owner_bound_storage_separate() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    activity_table = cast(Table, Activity.__table__)
    profile_activity_table = cast(Table, ProfileActivity.__table__)
    custom_table = cast(Table, ProfileCustomPreference.__table__)

    activity_ddl = str(CreateTable(activity_table).compile(dialect=dialect)).lower()
    relation_ddl = str(CreateTable(profile_activity_table).compile(dialect=dialect)).lower()
    custom_ddl = str(CreateTable(custom_table).compile(dialect=dialect)).lower()
    custom_index_ddl = "\n".join(
        str(CreateIndex(index).compile(dialect=dialect)).lower()
        for index in custom_table.indexes
    )

    assert "create table app_private.activities" in activity_ddl
    assert "constraint uq_activities_code unique (code)" in activity_ddl
    assert "references app_private.interests" not in activity_ddl
    assert "create table app_private.profile_activities" in relation_ddl
    assert "references app_private.activities (id) on delete restrict" in relation_ddl
    assert "references app_private.student_profiles (id) on delete cascade" in relation_ddl
    assert "create table app_private.profile_custom_preferences" in custom_ddl
    assert "kind app_private.preference_kind not null" in custom_ddl
    assert "proficiency app_private.language_proficiency" in custom_ddl
    assert "unique (profile_id, kind, normalized_key)" in custom_ddl
    assert "ix_profile_custom_preferences_kind_normalized_key" in custom_index_ddl
