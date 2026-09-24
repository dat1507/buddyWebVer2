"""Transactional email outbox persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base


class TransactionalOutbox(Base):
    """One idempotent transactional-email event, leased only by backend workers."""

    __tablename__ = "transactional_outbox"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(event_type)) BETWEEN 1 AND 100",
            name="ck_transactional_outbox_event_type_length",
        ),
        CheckConstraint(
            "length(btrim(recipient_email)) BETWEEN 1 AND 320",
            name="ck_transactional_outbox_recipient_email_length",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) BETWEEN 1 AND 256",
            name="ck_transactional_outbox_idempotency_key_length",
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_transactional_outbox_payload_object",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_transactional_outbox_attempts_nonnegative",
        ),
        CheckConstraint(
            "(lease_owner IS NULL) = (lease_expires_at IS NULL)",
            name="ck_transactional_outbox_lease_pair",
        ),
        CheckConstraint(
            "NOT (sent_at IS NOT NULL AND failed_at IS NOT NULL)",
            name="ck_transactional_outbox_one_terminal_state",
        ),
        CheckConstraint(
            "(sent_at IS NULL AND failed_at IS NULL) "
            "OR (lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_transactional_outbox_terminal_lease_clear",
        ),
        Index("ix_transactional_outbox_recipient_user_id", "recipient_user_id"),
        Index(
            "ix_transactional_outbox_delivery_ready",
            "next_attempt_at",
            postgresql_where=text(
                "sent_at IS NULL AND failed_at IS NULL AND deleted_at IS NULL"
            ),
        ),
        Index(
            "ix_transactional_outbox_lease_expires_at",
            "lease_expires_at",
            postgresql_where=text("lease_expires_at IS NOT NULL"),
        ),
    )

    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    recipient_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_email: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    lease_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
