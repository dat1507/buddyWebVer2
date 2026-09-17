"""Persistent refresh-token rotation and revocation state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base


class RefreshSession(Base):
    """One server-authoritative refresh-token family for a browser session."""

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        Index("ix_refresh_sessions_user_id", "user_id"),
        Index("ix_refresh_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
