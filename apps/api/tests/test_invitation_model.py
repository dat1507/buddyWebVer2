"""INV-001 model, lifecycle and deterministic timestamp contracts."""

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Enum, ForeignKeyConstraint, Table, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import (
    INVITATION_EXPIRY_DAYS,
    INVITATION_EXPIRY_INTERVAL,
    MAX_INVITATION_MESSAGE_CODE_POINTS,
    InvitationStatus,
    InvitationTransitionError,
    MatchingInvitation,
    invitation_expires_at,
)


def _pending_invitation() -> MatchingInvitation:
    sent_at = datetime(2026, 9, 29, 8, 30, tzinfo=UTC)
    return MatchingInvitation(
        sender_id=uuid4(),
        recipient_id=uuid4(),
        message="Hello",
        status=InvitationStatus.PENDING,
        created_at=sent_at,
        expires_at=invitation_expires_at(sent_at),
    )


def test_expiry_policy_is_seven_days_timezone_safe_and_deterministic() -> None:
    sent_at = datetime(2026, 9, 29, 15, 30, tzinfo=timezone(timedelta(hours=7)))

    expires_at = invitation_expires_at(sent_at)

    assert INVITATION_EXPIRY_DAYS == 7
    assert INVITATION_EXPIRY_INTERVAL == timedelta(days=7)
    assert expires_at == datetime(
        2026,
        10,
        6,
        15,
        30,
        tzinfo=timezone(timedelta(hours=7)),
    )
    assert expires_at.astimezone(UTC) == datetime(2026, 10, 6, 8, 30, tzinfo=UTC)


def test_expiry_policy_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="must be timezone-aware"):
        invitation_expires_at(datetime(2026, 9, 29, 8, 30))


@pytest.mark.parametrize(
    ("method_name", "expected_status", "timestamp_field"),
    (
        ("accept", InvitationStatus.ACCEPTED, "responded_at"),
        ("decline", InvitationStatus.DECLINED, "responded_at"),
        ("cancel", InvitationStatus.CANCELLED, "cancelled_at"),
        ("expire", InvitationStatus.EXPIRED, "expired_at"),
    ),
)
def test_pending_invitation_has_only_explicit_terminal_transitions(
    method_name: str,
    expected_status: InvitationStatus,
    timestamp_field: str,
) -> None:
    invitation = _pending_invitation()
    transition_at = (
        invitation.expires_at
        if expected_status is InvitationStatus.EXPIRED
        else invitation.created_at + timedelta(hours=1)
    )

    getattr(invitation, method_name)(at=transition_at)

    assert invitation.status is expected_status
    assert getattr(invitation, timestamp_field) == transition_at
    populated_terminal_fields = {
        field
        for field in ("responded_at", "cancelled_at", "expired_at")
        if getattr(invitation, field) is not None
    }
    assert populated_terminal_fields == {timestamp_field}


@pytest.mark.parametrize("first_transition", ("accept", "decline", "cancel", "expire"))
def test_terminal_invitation_cannot_transition_again(first_transition: str) -> None:
    invitation = _pending_invitation()
    first_at = (
        invitation.expires_at
        if first_transition == "expire"
        else invitation.created_at + timedelta(hours=1)
    )
    getattr(invitation, first_transition)(at=first_at)

    with pytest.raises(InvitationTransitionError) as error:
        invitation.accept(at=invitation.expires_at + timedelta(seconds=1))

    assert error.value.current_status is invitation.status
    assert error.value.target_status is InvitationStatus.ACCEPTED


def test_expiration_cannot_be_recorded_before_persisted_deadline() -> None:
    invitation = _pending_invitation()

    with pytest.raises(ValueError, match="before its persisted deadline"):
        invitation.expire(at=invitation.expires_at - timedelta(microseconds=1))

    assert invitation.status is InvitationStatus.PENDING
    assert invitation.expired_at is None


def test_transition_rejects_naive_or_precreation_timestamp() -> None:
    invitation = _pending_invitation()

    with pytest.raises(ValueError, match="must be timezone-aware"):
        invitation.accept(at=datetime(2026, 9, 29, 9, 30))
    with pytest.raises(ValueError, match="cannot predate creation"):
        invitation.accept(at=invitation.created_at - timedelta(microseconds=1))

    assert invitation.status is InvitationStatus.PENDING


def test_message_is_outer_trimmed_and_defensively_bounded() -> None:
    invitation = MatchingInvitation(
        sender_id=uuid4(),
        recipient_id=uuid4(),
        message=" \t Hello from INV-001 \n",
        status=InvitationStatus.PENDING,
    )

    assert invitation.message == "Hello from INV-001"

    with pytest.raises(ValueError, match="code-point limit"):
        invitation.message = "x" * (MAX_INVITATION_MESSAGE_CODE_POINTS + 1)


def test_model_has_private_uuid_relationships_and_optimistic_versioning() -> None:
    table = cast(Table, MatchingInvitation.__table__)
    foreign_keys = {
        str(constraint.name): constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert table.schema == "app_private"
    assert set(table.columns) >= {
        table.c.sender_id,
        table.c.recipient_id,
        table.c.pair_low_user_id,
        table.c.pair_high_user_id,
        table.c.message,
        table.c.status,
        table.c.expires_at,
        table.c.responded_at,
        table.c.cancelled_at,
        table.c.expired_at,
        table.c.sender_hidden_at,
        table.c.version,
    }
    assert foreign_keys["fk_matching_invitations_sender_id_users"].ondelete == "CASCADE"
    assert foreign_keys["fk_matching_invitations_recipient_id_users"].ondelete == "CASCADE"
    assert isinstance(table.c.status.type, Enum)
    assert table.c.status.type.name == "invitation_status"
    assert table.c.status.type.enums == [status.value for status in InvitationStatus]
    assert table.c.pair_low_user_id.computed is not None
    assert table.c.pair_high_user_id.computed is not None
    assert inspect(MatchingInvitation).version_id_col is table.c.version


def test_postgresql_ddl_enforces_pair_lifecycle_expiry_and_query_indexes() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    table = cast(Table, MatchingInvitation.__table__)
    table_ddl = str(CreateTable(table).compile(dialect=dialect)).lower()
    index_ddl = {
        str(index.name): str(CreateIndex(index).compile(dialect=dialect)).lower()
        for index in table.indexes
    }

    assert "create table app_private.matching_invitations" in table_ddl
    assert "generated always as (least(sender_id, recipient_id)) stored" in table_ddl
    assert "generated always as (greatest(sender_id, recipient_id)) stored" in table_ddl
    assert "sender_id <> recipient_id" in table_ddl
    assert "expires_at = created_at + interval '7 days'" in table_ddl
    assert "char_length(message) <= 10000" in table_ddl
    assert "status = 'pending'" in table_ddl
    assert "status = 'accepted'" in table_ddl
    assert "status = 'declined'" in table_ddl
    assert "status = 'cancelled'" in table_ddl
    assert "status = 'expired'" in table_ddl
    assert "version >= 1" in table_ddl
    assert "where status = 'pending'" in index_ddl["uq_matching_invitations_pending_pair"]
    assert "unique" in index_ddl["uq_matching_invitations_pending_pair"]
    assert "where status = 'pending'" in index_ddl["ix_matching_invitations_pending_expires_at"]
    assert set(index_ddl) == {
        "uq_matching_invitations_pending_pair",
        "ix_matching_invitations_sender_status_created_at",
        "ix_matching_invitations_recipient_status_created_at",
        "ix_matching_invitations_pending_expires_at",
    }
