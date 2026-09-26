"""Shared preference catalogs and profile-owned preference persistence."""

from __future__ import annotations

from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH: Final = 120
MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH: Final = 255
MAX_CUSTOM_PREFERENCE_INPUT_LENGTH: Final = MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH


class _CatalogKeyBase(DeclarativeBase):
    """Mappings whose contract uses natural or composite primary keys."""

    metadata = Base.metadata


class LanguageProficiency(StrEnum):
    """Self-reported spoken-language proficiency used by matching."""

    NATIVE = "native"
    FLUENT = "fluent"
    INTERMEDIATE = "intermediate"
    BEGINNER = "beginner"


class PreferenceKind(StrEnum):
    """Supported profile-owned custom preference dimensions."""

    INTEREST = "INTEREST"
    LANGUAGE = "LANGUAGE"
    ACTIVITY = "ACTIVITY"


class Interest(Base):
    """Shared, localized catalog for both interests and hobbies."""

    __tablename__ = "interests"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z0-9]+(-[a-z0-9]+|_[a-z0-9]+)*$' "
            "AND char_length(code) <= 64",
            name="ck_interests_code_format",
        ),
        CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_interests_label_en_length",
        ),
        CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_interests_label_de_length",
        ),
        CheckConstraint(
            "char_length(btrim(category)) BETWEEN 1 AND 80",
            name="ck_interests_category_length",
        ),
    )

    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label_en: Mapped[str] = mapped_column(Text, nullable=False)
    label_de: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )


class Language(_CatalogKeyBase):
    """Localized language catalog keyed by a stable normalized code."""

    __tablename__ = "languages"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="ck_languages_code_format",
        ),
        CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_languages_label_en_length",
        ),
        CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_languages_label_de_length",
        ),
    )

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    label_en: Mapped[str] = mapped_column(Text, nullable=False)
    label_de: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )


class Activity(Base):
    """Shared predefined activity catalog, independent from interests."""

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z0-9]+(-[a-z0-9]+|_[a-z0-9]+)*$' "
            "AND char_length(code) <= 64",
            name="ck_activities_code_format",
        ),
        CheckConstraint(
            "char_length(btrim(label_en)) BETWEEN 1 AND 120",
            name="ck_activities_label_en_length",
        ),
        CheckConstraint(
            "char_length(btrim(label_de)) BETWEEN 1 AND 120",
            name="ck_activities_label_de_length",
        ),
    )

    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label_en: Mapped[str] = mapped_column(Text, nullable=False)
    label_de: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )


class ProfileInterest(_CatalogKeyBase):
    """One normalized interest selection for a student profile."""

    __tablename__ = "profile_interests"
    __table_args__ = (Index("ix_profile_interests_interest_id", "interest_id"),)

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interest_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.interests.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class ProfileLanguage(_CatalogKeyBase):
    """One normalized language and proficiency for a student profile."""

    __tablename__ = "profile_languages"
    __table_args__ = (Index("ix_profile_languages_language_code", "language_code"),)

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    language_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey(f"{APPLICATION_SCHEMA}.languages.code", ondelete="RESTRICT"),
        primary_key=True,
    )
    proficiency: Mapped[LanguageProficiency] = mapped_column(
        Enum(
            LanguageProficiency,
            name="language_proficiency",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda levels: [level.value for level in levels],
        ),
        nullable=False,
    )


class ProfileActivity(_CatalogKeyBase):
    """One predefined activity selection for a student profile."""

    __tablename__ = "profile_activities"
    __table_args__ = (Index("ix_profile_activities_activity_id", "activity_id"),)

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.activities.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class ProfileCustomPreference(Base):
    """A normalized custom preference owned by exactly one profile."""

    __tablename__ = "profile_custom_preferences"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(display_label)) BETWEEN 1 AND "
            f"{MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH}",
            name="ck_profile_custom_preferences_display_label_length",
        ),
        CheckConstraint(
            "char_length(normalized_key) BETWEEN 1 AND "
            f"{MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH} "
            "AND normalized_key = btrim(normalized_key)",
            name="ck_profile_custom_preferences_normalized_key_length",
        ),
        CheckConstraint(
            "(kind = 'LANGUAGE' AND proficiency IS NOT NULL) "
            "OR (kind IN ('INTEREST', 'ACTIVITY') AND proficiency IS NULL)",
            name="ck_profile_custom_preferences_language_proficiency_scope",
        ),
        UniqueConstraint(
            "profile_id",
            "kind",
            "normalized_key",
            name="uq_profile_custom_preferences_profile_kind_key",
        ),
        Index(
            "ix_profile_custom_preferences_kind_normalized_key",
            "kind",
            "normalized_key",
        ),
    )

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[PreferenceKind] = mapped_column(
        Enum(
            PreferenceKind,
            name="preference_kind",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda kinds: [kind.value for kind in kinds],
        ),
        nullable=False,
    )
    display_label: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(Text, nullable=False)
    proficiency: Mapped[LanguageProficiency | None] = mapped_column(
        Enum(
            LanguageProficiency,
            name="language_proficiency",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda levels: [level.value for level in levels],
        ),
        nullable=True,
    )
