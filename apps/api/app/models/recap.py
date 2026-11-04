"""Independent recap publication and private photo derivative ownership."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base


class Recap(Base):
    __tablename__ = "recaps"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')", name="ck_recaps_status"),
        CheckConstraint("version >= 1", name="ck_recaps_version"),
        ForeignKeyConstraint(
            ["thumbnail_id", "id"],
            [
                f"{APPLICATION_SCHEMA}.recap_photos.id",
                f"{APPLICATION_SCHEMA}.recap_photos.recap_id",
            ],
            name="fk_recaps_thumbnail_owner",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        Index("ix_recaps_public_order", "status", "event_date", "created_at", "id"),
        Index(
            "ix_recaps_first_publication",
            "first_published_at",
            "id",
            postgresql_where=text("status='PUBLISHED' AND deleted_at IS NULL"),
        ),
    )
    first_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_event_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey(f"{APPLICATION_SCHEMA}.events.id", ondelete="RESTRICT")
    )
    title_en: Mapped[str | None] = mapped_column(Text)
    title_de: Mapped[str | None] = mapped_column(Text)
    summary_en: Mapped[str | None] = mapped_column(Text)
    summary_de: Mapped[str | None] = mapped_column(Text)
    editorial_en: Mapped[str | None] = mapped_column(Text)
    editorial_de: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, default="DRAFT", server_default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    thumbnail_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT")
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT")
    )


class RecapPhoto(Base):
    __tablename__ = "recap_photos"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        UniqueConstraint("id", "recap_id", name="uq_recap_photo_owner"),
        UniqueConstraint("recap_id", "upload_id", name="uq_recap_photo_retry"),
        CheckConstraint("sort_order BETWEEN 0 AND 11", name="ck_recap_photo_order"),
        CheckConstraint(
            "char_length(alt_en) <= 200 AND char_length(alt_de) <= 200", name="ck_recap_photo_alt"
        ),
        Index("ix_recap_photos_recap_order", "recap_id", "sort_order"),
    )
    recap_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(f"{APPLICATION_SCHEMA}.recaps.id", ondelete="CASCADE")
    )
    upload_id: Mapped[UUID] = mapped_column(Uuid)
    fingerprint: Mapped[str] = mapped_column(Text)
    alt_en: Mapped[str] = mapped_column(Text, default="", server_default="")
    alt_de: Mapped[str] = mapped_column(Text, default="", server_default="")
    caption_en: Mapped[str | None] = mapped_column(Text)
    caption_de: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer)


class RecapImage(Base):
    """Separate rows let existing generic Storage reconciliation discover both variants."""

    __tablename__ = "recap_images"
    __table_args__ = (
        UniqueConstraint("photo_id", "variant", name="uq_recap_image_variant"),
        CheckConstraint("variant IN ('thumbnail', 'display')", name="ck_recap_image_variant"),
        CheckConstraint("bucket = 'event-media'", name="ck_recap_image_bucket"),
        CheckConstraint("byte_size BETWEEN 1 AND 5242880", name="ck_recap_image_bytes"),
        CheckConstraint(
            "width BETWEEN 1 AND 1600 AND height BETWEEN 1 AND 1600", name="ck_recap_image_size"
        ),
    )
    photo_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(f"{APPLICATION_SCHEMA}.recap_photos.id", ondelete="CASCADE")
    )
    bucket: Mapped[str] = mapped_column(Text, default="event-media", server_default="event-media")
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    variant: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)


class RecapMediaCleanup(Base):
    """Durable media deletion work survives permanent recap/photo removal."""

    __tablename__ = "recap_media_cleanup"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_recap_cleanup_key"),
        CheckConstraint("bucket = 'event-media'", name="ck_recap_cleanup_bucket"),
        Index("ix_recap_cleanup_recap", "recap_id"),
    )
    recap_id: Mapped[UUID] = mapped_column(Uuid)
    bucket: Mapped[str] = mapped_column(Text, default="event-media", server_default="event-media")
    object_key: Mapped[str] = mapped_column(Text)
