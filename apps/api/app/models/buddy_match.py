"""Durable ACTIVE Buddy relationship persistence and unordered-pair identity."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base


class MatchStatus(StrEnum):
    """The only Buddy Match lifecycle state in the current product contract."""

    ACTIVE = "ACTIVE"


def canonical_user_pair(first_user_id: UUID, second_user_id: UUID) -> tuple[UUID, UUID]:
    """Return one deterministic identity for either direction of a user pair."""
    if first_user_id == second_user_id:
        raise ValueError("A Buddy Match requires two distinct users.")
    return (
        (first_user_id, second_user_id)
        if first_user_id.int < second_user_id.int
        else (second_user_id, first_user_id)
    )


class BuddyMatch(Base):
    """An immutable ACTIVE relationship created from one accepted invitation."""

    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint(
            "participant_one_user_id <> participant_two_user_id",
            name="ck_matches_distinct_users",
        ),
        CheckConstraint(
            "participant_one_profile_id <> participant_two_profile_id",
            name="ck_matches_distinct_profiles",
        ),
        CheckConstraint(
            "pair_low_user_id < pair_high_user_id",
            name="ck_matches_canonical_pair_order",
        ),
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_matches_score_range",
        ),
        CheckConstraint(
            "jsonb_typeof(score_breakdown) = 'object'",
            name="ck_matches_score_breakdown_object",
        ),
        Index(
            "uq_matches_active_pair",
            "pair_low_user_id",
            "pair_high_user_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "ix_matches_participant_one_status_activated_at",
            "participant_one_user_id",
            "status",
            "activated_at",
        ),
        Index(
            "ix_matches_participant_two_status_activated_at",
            "participant_two_user_id",
            "status",
            "activated_at",
        ),
        Index(
            "ix_matches_participant_one_profile_id",
            "participant_one_profile_id",
        ),
        Index(
            "ix_matches_participant_two_profile_id",
            "participant_two_profile_id",
        ),
        Index("ix_matches_semester_id", "semester_id"),
    )

    participant_one_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_two_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_one_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_two_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    pair_low_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        Computed(
            "LEAST(participant_one_user_id, participant_two_user_id)",
            persisted=True,
        ),
        nullable=False,
    )
    pair_high_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        Computed(
            "GREATEST(participant_one_user_id, participant_two_user_id)",
            persisted=True,
        ),
        nullable=False,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(
            MatchStatus,
            name="match_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=MatchStatus.ACTIVE,
        server_default=MatchStatus.ACTIVE.value,
    )
    accepted_invitation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            f"{APPLICATION_SCHEMA}.matching_invitations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )
    semester_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.semesters.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
