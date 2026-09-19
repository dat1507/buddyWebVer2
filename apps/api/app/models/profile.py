"""Canonical student profile and owned private-photo persistence models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    Uuid,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

PROFILE_IMAGE_BUCKET = "profile-images"
MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PROFILE_IMAGE_DIMENSION = 4096
MAX_PROFILE_IMAGE_PIXELS = MAX_PROFILE_IMAGE_DIMENSION * MAX_PROFILE_IMAGE_DIMENSION


class StudentType(StrEnum):
    """Self-selected Buddy Program participation type, independent of account role."""

    VIETNAMESE = "VIETNAMESE"
    INTERNATIONAL = "INTERNATIONAL"


class ProfilePhotoProcessingStatus(StrEnum):
    """Terminal processing state persisted for an owned profile image."""

    READY = "READY"
    FAILED = "FAILED"


class StudentProfile(Base):
    """One canonical, resumable Buddy Program profile owned by one User."""

    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "full_name IS NULL OR char_length(btrim(full_name)) BETWEEN 1 AND 120",
            name="ck_student_profiles_full_name_length",
        ),
        CheckConstraint(
            "display_name IS NULL OR char_length(btrim(display_name)) BETWEEN 1 AND 80",
            name="ck_student_profiles_display_name_length",
        ),
        CheckConstraint(
            "study_year IS NULL OR study_year BETWEEN 1 AND 10",
            name="ck_student_profiles_study_year_range",
        ),
        CheckConstraint(
            "bio IS NULL OR char_length(bio) <= 500",
            name="ck_student_profiles_bio_length",
        ),
        CheckConstraint(
            "arrival_date IS NULL OR departure_date IS NULL OR departure_date >= arrival_date",
            name="ck_student_profiles_date_order",
        ),
        CheckConstraint(
            "availability IS NULL OR jsonb_typeof(availability) = 'object'",
            name="ck_student_profiles_availability_object",
        ),
        CheckConstraint(
            "preferences IS NULL OR jsonb_typeof(preferences) = 'object'",
            name="ck_student_profiles_preferences_object",
        ),
        CheckConstraint("version >= 1", name="ck_student_profiles_version_positive"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_type: Mapped[StudentType | None] = mapped_column(
        Enum(
            StudentType,
            name="student_type",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda types: [student_type.value for student_type in types],
        ),
        nullable=True,
    )
    nationality: Mapped[str | None] = mapped_column(Text, nullable=True)
    major: Mapped[str | None] = mapped_column(Text, nullable=True)
    study_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_university: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    availability: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    preferences: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    matching_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ProfilePhoto(Base):
    """Private image metadata owned by one canonical student profile."""

    __tablename__ = "profile_photos"
    __table_args__ = (
        CheckConstraint(
            f"bucket = '{PROFILE_IMAGE_BUCKET}'",
            name="ck_profile_photos_profile_bucket",
        ),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_profile_photos_mime_type",
        ),
        CheckConstraint(
            f"byte_size BETWEEN 1 AND {MAX_PROFILE_IMAGE_BYTES}",
            name="ck_profile_photos_byte_size_range",
        ),
        CheckConstraint(
            "width BETWEEN 1 AND 4096 AND height BETWEEN 1 AND 4096 "
            f"AND width * height <= {MAX_PROFILE_IMAGE_PIXELS}",
            name="ck_profile_photos_dimensions",
        ),
        Index(
            "uq_profile_photos_one_avatar_per_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("is_avatar AND deleted_at IS NULL"),
        ),
    )

    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    bucket: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=PROFILE_IMAGE_BUCKET,
        server_default=text(f"'{PROFILE_IMAGE_BUCKET}'"),
    )
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    is_avatar: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    processing_status: Mapped[ProfilePhotoProcessingStatus] = mapped_column(
        Enum(
            ProfilePhotoProcessingStatus,
            name="profile_photo_processing_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=ProfilePhotoProcessingStatus.READY,
        server_default=ProfilePhotoProcessingStatus.READY.value,
    )
