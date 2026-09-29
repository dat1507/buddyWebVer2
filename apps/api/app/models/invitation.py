"""Durable invitation record and explicit lifecycle state machine."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

INVITATION_EXPIRY_DAYS: Final = 7
INVITATION_EXPIRY_INTERVAL: Final = timedelta(days=INVITATION_EXPIRY_DAYS)
MAX_INVITATION_MESSAGE_CODE_POINTS: Final = 10_000


class InvitationStatus(StrEnum):
    """Persisted invitation lifecycle states."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


TERMINAL_INVITATION_STATUSES: Final = frozenset(
    {
        InvitationStatus.ACCEPTED,
        InvitationStatus.DECLINED,
        InvitationStatus.CANCELLED,
        InvitationStatus.EXPIRED,
    }
)


class InvitationTransitionError(ValueError):
    """Raised when a caller attempts a transition outside the lifecycle contract."""

    def __init__(
        self,
        current_status: InvitationStatus,
        target_status: InvitationStatus,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Invitation cannot transition from {current_status.value} to {target_status.value}."
        )


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value


def invitation_expires_at(sent_at: datetime) -> datetime:
    """Return the deterministic seven-day deadline for an aware sent instant."""
    return _require_aware(sent_at, field_name="Invitation sent time") + (INVITATION_EXPIRY_INTERVAL)


class MatchingInvitation(Base):
    """One sender request and its durable, non-destructive response lifecycle."""

    __tablename__ = "matching_invitations"
    __table_args__ = (
        CheckConstraint(
            "sender_id <> recipient_id",
            name="ck_matching_invitations_distinct_participants",
        ),
        CheckConstraint(
            "pair_low_user_id < pair_high_user_id",
            name="ck_matching_invitations_canonical_pair_order",
        ),
        CheckConstraint(
            "message = btrim(message) "
            f"AND char_length(message) <= {MAX_INVITATION_MESSAGE_CODE_POINTS}",
            name="ck_matching_invitations_message_canonical_length",
        ),
        CheckConstraint(
            "expires_at = created_at + INTERVAL '7 days'",
            name="ck_matching_invitations_expiry_interval",
        ),
        CheckConstraint(
            "(status = 'PENDING' AND responded_at IS NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'ACCEPTED' AND responded_at IS NOT NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL) "
            "OR (status = 'DECLINED' AND responded_at IS NOT NULL "
            "AND cancelled_at IS NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'CANCELLED' AND responded_at IS NULL "
            "AND cancelled_at IS NOT NULL AND expired_at IS NULL "
            "AND sender_hidden_at IS NULL) "
            "OR (status = 'EXPIRED' AND responded_at IS NULL "
            "AND cancelled_at IS NULL AND expired_at IS NOT NULL "
            "AND sender_hidden_at IS NULL)",
            name="ck_matching_invitations_status_timestamps",
        ),
        CheckConstraint(
            "(responded_at IS NULL OR responded_at >= created_at) "
            "AND (cancelled_at IS NULL OR cancelled_at >= created_at) "
            "AND (expired_at IS NULL OR expired_at >= expires_at) "
            "AND (sender_hidden_at IS NULL OR sender_hidden_at >= responded_at)",
            name="ck_matching_invitations_timestamp_order",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_matching_invitations_version_positive",
        ),
        Index(
            "uq_matching_invitations_pending_pair",
            "pair_low_user_id",
            "pair_high_user_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "ix_matching_invitations_sender_status_created_at",
            "sender_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_matching_invitations_recipient_status_created_at",
            "recipient_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_matching_invitations_pending_expires_at",
            "expires_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
    )

    sender_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    pair_low_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        Computed("LEAST(sender_id, recipient_id)", persisted=True),
        nullable=False,
    )
    pair_high_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        Computed("GREATEST(sender_id, recipient_id)", persisted=True),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(
            InvitationStatus,
            name="invitation_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=InvitationStatus.PENDING,
        server_default=InvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("(now() + INTERVAL '7 days')"),
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sender_hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    __mapper_args__ = {"version_id_col": version}

    @validates("message")
    def validate_message(self, _key: str, value: str) -> str:
        canonical = value.strip()
        if len(canonical) > MAX_INVITATION_MESSAGE_CODE_POINTS:
            raise ValueError("Invitation message exceeds the persisted code-point limit.")
        return canonical

    @validates(
        "expires_at",
        "responded_at",
        "cancelled_at",
        "expired_at",
        "sender_hidden_at",
    )
    def validate_aware_datetime(
        self,
        key: str,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None:
            _require_aware(value, field_name=key.replace("_", " ").title())
        return value

    def accept(self, *, at: datetime) -> None:
        """Transition a persisted pending invitation to accepted."""
        self._transition(InvitationStatus.ACCEPTED, at=at)

    def decline(self, *, at: datetime) -> None:
        """Transition a persisted pending invitation to declined."""
        self._transition(InvitationStatus.DECLINED, at=at)

    def cancel(self, *, at: datetime) -> None:
        """Transition a persisted pending invitation to cancelled."""
        self._transition(InvitationStatus.CANCELLED, at=at)

    def expire(self, *, at: datetime) -> None:
        """Transition a pending invitation at or after its persisted deadline."""
        transition_time = _require_aware(at, field_name="Invitation transition time")
        if transition_time < self.expires_at:
            raise ValueError("Invitation cannot expire before its persisted deadline.")
        self._transition(InvitationStatus.EXPIRED, at=transition_time)

    def _transition(self, target: InvitationStatus, *, at: datetime) -> None:
        transition_time = _require_aware(at, field_name="Invitation transition time")
        is_terminal_target = target in TERMINAL_INVITATION_STATUSES
        if self.status is not InvitationStatus.PENDING or not is_terminal_target:
            raise InvitationTransitionError(self.status, target)
        if self.created_at is not None and transition_time < self.created_at:
            raise ValueError("Invitation transition cannot predate creation.")

        self.status = target
        if target in {InvitationStatus.ACCEPTED, InvitationStatus.DECLINED}:
            self.responded_at = transition_time
        elif target is InvitationStatus.CANCELLED:
            self.cancelled_at = transition_time
        else:
            self.expired_at = transition_time
