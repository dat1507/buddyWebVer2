"""Schema-contract tests for normalized profile catalogs and selections."""

from typing import cast

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.engine import make_url
from sqlalchemy.schema import ColumnDefault, CreateIndex, CreateTable, DefaultClause

from app.core.database import APPLICATION_SCHEMA
from app.models import (
    Base,
    Interest,
    Language,
    LanguageProficiency,
    ProfileInterest,
    ProfileLanguage,
)


def _check_names(table: Table) -> set[str]:
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _foreign_keys(table: Table) -> dict[str, ForeignKeyConstraint]:
    return {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_interest_is_one_localized_active_catalog_for_interests_and_hobbies() -> None:
    table = cast(Table, Interest.__table__)

    assert table.metadata is Base.metadata
    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "interests"
    assert f"{APPLICATION_SCHEMA}.hobbies" not in Base.metadata.tables
    assert set(table.columns.keys()) == {
        "code",
        "label_en",
        "label_de",
        "category",
        "is_active",
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert all(isinstance(table.c[name].type, Text) for name in ("code", "label_en", "label_de"))
    assert isinstance(table.c.category.type, Text)
    assert isinstance(table.c.is_active.type, Boolean)
    assert cast(ColumnDefault, table.c.is_active.default).arg is True
    assert str(cast(DefaultClause, table.c.is_active.server_default).arg) == "true"

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_columns == {("code",)}
    assert _check_names(table) == {
        "ck_interests_code_format",
        "ck_interests_label_en_length",
        "ck_interests_label_de_length",
        "ck_interests_category_length",
    }


def test_language_uses_a_stable_natural_key_and_localized_active_catalog() -> None:
    table = cast(Table, Language.__table__)

    assert table.metadata is Base.metadata
    assert table.schema == APPLICATION_SCHEMA
    assert table.name == "languages"
    assert set(table.columns.keys()) == {"code", "label_en", "label_de", "is_active"}
    assert isinstance(table.c.code.type, Text)
    assert table.c.code.primary_key is True
    assert table.c.code.nullable is False
    assert isinstance(table.c.label_en.type, Text)
    assert isinstance(table.c.label_de.type, Text)
    assert isinstance(table.c.is_active.type, Boolean)
    assert cast(ColumnDefault, table.c.is_active.default).arg is True
    assert str(cast(DefaultClause, table.c.is_active.server_default).arg) == "true"
    assert _check_names(table) == {
        "ck_languages_code_format",
        "ck_languages_label_en_length",
        "ck_languages_label_de_length",
    }


def test_profile_interest_uses_only_a_unique_catalog_pair() -> None:
    table = cast(Table, ProfileInterest.__table__)

    assert table.metadata is Base.metadata
    assert table.schema == APPLICATION_SCHEMA
    assert set(table.columns.keys()) == {"profile_id", "interest_id"}
    assert isinstance(table.c.profile_id.type, Uuid)
    assert isinstance(table.c.interest_id.type, Uuid)
    primary_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    )
    assert primary_key.name == "pk_profile_interests"
    assert tuple(column.name for column in primary_key.columns) == ("profile_id", "interest_id")

    foreign_keys = _foreign_keys(table)
    assert set(foreign_keys) == {
        "fk_profile_interests_profile_id_student_profiles",
        "fk_profile_interests_interest_id_interests",
    }
    assert foreign_keys["fk_profile_interests_profile_id_student_profiles"].ondelete == "CASCADE"
    assert foreign_keys["fk_profile_interests_interest_id_interests"].ondelete == "RESTRICT"
    assert {
        index.name: tuple(column.name for column in index.columns) for index in table.indexes
    } == {"ix_profile_interests_interest_id": ("interest_id",)}


def test_profile_language_uses_one_catalog_pair_with_required_proficiency() -> None:
    table = cast(Table, ProfileLanguage.__table__)

    assert table.metadata is Base.metadata
    assert table.schema == APPLICATION_SCHEMA
    assert set(table.columns.keys()) == {"profile_id", "language_code", "proficiency"}
    primary_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    )
    assert primary_key.name == "pk_profile_languages"
    assert tuple(column.name for column in primary_key.columns) == (
        "profile_id",
        "language_code",
    )

    proficiency = table.c.proficiency
    assert isinstance(proficiency.type, Enum)
    assert proficiency.type.enum_class is LanguageProficiency
    assert proficiency.type.enums == ["native", "fluent", "intermediate", "beginner"]
    assert proficiency.type.schema == APPLICATION_SCHEMA
    assert proficiency.nullable is False

    foreign_keys = _foreign_keys(table)
    assert set(foreign_keys) == {
        "fk_profile_languages_profile_id_student_profiles",
        "fk_profile_languages_language_code_languages",
    }
    assert foreign_keys["fk_profile_languages_profile_id_student_profiles"].ondelete == "CASCADE"
    assert foreign_keys["fk_profile_languages_language_code_languages"].ondelete == "RESTRICT"
    assert {
        index.name: tuple(column.name for column in index.columns) for index in table.indexes
    } == {"ix_profile_languages_language_code": ("language_code",)}


def test_catalog_relations_reference_only_normalized_catalog_values() -> None:
    interest_columns = set(ProfileInterest.__table__.columns.keys())
    language_columns = set(ProfileLanguage.__table__.columns.keys())

    assert not {"interest", "hobby", "label", "value", "name"}.intersection(interest_columns)
    assert not {"language", "label", "value", "name"}.intersection(language_columns)
    assert tuple(LanguageProficiency) == (
        LanguageProficiency.NATIVE,
        LanguageProficiency.FLUENT,
        LanguageProficiency.INTERMEDIATE,
        LanguageProficiency.BEGINNER,
    )


def test_postgresql_ddl_preserves_catalog_history_and_pair_uniqueness() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    interest_table = cast(Table, Interest.__table__)
    language_table = cast(Table, Language.__table__)
    profile_interest_table = cast(Table, ProfileInterest.__table__)
    profile_language_table = cast(Table, ProfileLanguage.__table__)
    interest_ddl = str(CreateTable(interest_table).compile(dialect=dialect)).lower()
    language_ddl = str(CreateTable(language_table).compile(dialect=dialect)).lower()
    profile_interest_ddl = str(CreateTable(profile_interest_table).compile(dialect=dialect)).lower()
    profile_language_ddl = str(CreateTable(profile_language_table).compile(dialect=dialect)).lower()
    relation_index_ddl = {
        str(CreateIndex(index).compile(dialect=dialect)).lower()
        for table in (profile_interest_table, profile_language_table)
        for index in table.indexes
    }

    assert "create table app_private.interests" in interest_ddl
    assert "constraint uq_interests_code unique (code)" in interest_ddl
    assert "is_active boolean default true not null" in interest_ddl
    assert "create table app_private.languages" in language_ddl
    assert "constraint pk_languages primary key (code)" in language_ddl
    assert "is_active boolean default true not null" in language_ddl
    assert "constraint pk_profile_interests primary key (profile_id, interest_id)" in profile_interest_ddl
    assert "references app_private.interests (id) on delete restrict" in profile_interest_ddl
    assert (
        "constraint pk_profile_languages primary key (profile_id, language_code)"
        in profile_language_ddl
    )
    assert "proficiency app_private.language_proficiency not null" in profile_language_ddl
    assert "references app_private.languages (code) on delete restrict" in profile_language_ddl
    assert relation_index_ddl == {
        "create index ix_profile_interests_interest_id "
        "on app_private.profile_interests (interest_id)",
        "create index ix_profile_languages_language_code "
        "on app_private.profile_languages (language_code)",
    }
