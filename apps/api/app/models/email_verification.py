"""Persistent one-use email-verification token metadata."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base


class EmailVerificationToken(Base):
    """Digest-only token state; plaintext verification tokens are never persisted."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        CheckConstraint(
            "octet_length(token_digest) > 0",
            name="ck_email_verification_tokens_digest_not_empty",
        ),
        CheckConstraint(
            "length(btrim(email_snapshot)) > 0",
            name="ck_email_verification_tokens_email_not_blank",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_email_verification_tokens_expiry_after_creation",
        ),
        Index("ix_email_verification_tokens_user_id", "user_id"),
        Index("ix_email_verification_tokens_expires_at", "expires_at"),
        Index(
            "uq_email_verification_tokens_active_user_id",
            "user_id",
            unique=True,
            postgresql_where=text(
                "consumed_at IS NULL AND superseded_at IS NULL AND deleted_at IS NULL"
            ),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_digest: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        unique=True,
    )
    email_snapshot: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
