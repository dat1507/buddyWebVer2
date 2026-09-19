"""Unit and security tests for transactional audit staging and redaction."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.services.audit_logs import (
    REDACTED_AUDIT_VALUE,
    AuditLogActorError,
    AuditLogValidationError,
    record_audit_log,
)

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
RESOURCE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _actor(
    *,
    role: UserRole = UserRole.ADMIN,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=is_active,
        email_verified=True,
        deleted_at=deleted_at,
    )


@pytest.mark.anyio
async def test_record_stages_redacted_json_with_actor_and_resource_identity() -> None:
    mock, session = _session()
    signed_url = "https://storage.example.test/object?token=private-link-value"
    alternate_signed_url = "https://cdn.example.test/object?sig=alternate-link-value"
    request_id = uuid4()

    audit = await record_audit_log(
        session,
        _actor(),
        action=" event.update ",
        resource_type=" event ",
        resource_id=RESOURCE_ID,
        old_value={
            "title": "Original title",
            "password_hash": "credential-value",
            "cover_url": signed_url,
            "nested": {"access_token": "token-value", "capacity": Decimal("24.5")},
        },
        new_value={
            "title": "Updated title",
            "starts_at": datetime(2026, 10, 1, 10, 30, tzinfo=UTC),
        },
        metadata={
            "request_id": request_id,
            "signed_url": signed_url,
            "temporary_url": alternate_signed_url,
            "student_profile": {"bio": "Nested private biography"},
        },
    )

    mock.add.assert_called_once_with(audit)
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()
    assert audit.admin_id == ADMIN_ID
    assert audit.action == "event.update"
    assert audit.resource_type == "event"
    assert audit.resource_id == RESOURCE_ID
    assert audit.old_value == {
        "title": "Original title",
        "password_hash": REDACTED_AUDIT_VALUE,
        "cover_url": REDACTED_AUDIT_VALUE,
        "nested": {
            "access_token": REDACTED_AUDIT_VALUE,
            "capacity": "24.5",
        },
    }
    assert audit.new_value == {
        "title": "Updated title",
        "starts_at": "2026-10-01T10:30:00+00:00",
    }
    assert audit.context == {
        "request_id": str(request_id),
        "signed_url": REDACTED_AUDIT_VALUE,
        "temporary_url": REDACTED_AUDIT_VALUE,
        "student_profile": REDACTED_AUDIT_VALUE,
    }
    serialized = json.dumps(
        {"old": audit.old_value, "new": audit.new_value, "metadata": audit.context}
    )
    for forbidden in (
        "credential-value",
        "token-value",
        "private-link-value",
        "alternate-link-value",
        "Nested private biography",
    ):
        assert forbidden not in serialized


@pytest.mark.anyio
async def test_profile_changes_retain_operational_state_without_profile_content() -> None:
    _, session = _session()

    audit = await record_audit_log(
        session,
        _actor(),
        action="profile.admin_read",
        resource_type="student_profile",
        resource_id=RESOURCE_ID,
        old_value={
            "status": "DRAFT",
            "bio": "Private biography",
            "languages": ["de", "en"],
            "nested": {"major": "Computer Science"},
        },
        new_value={"status": "COMPLETE", "matching_eligible": True},
    )

    assert audit.old_value == {
        "status": "DRAFT",
        "bio": REDACTED_AUDIT_VALUE,
        "languages": REDACTED_AUDIT_VALUE,
        "nested": REDACTED_AUDIT_VALUE,
    }
    assert audit.new_value == {"status": "COMPLETE", "matching_eligible": True}
    assert "Private biography" not in json.dumps(audit.old_value)
    assert "Computer Science" not in json.dumps(audit.old_value)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "actor",
    [
        _actor(role=UserRole.USER),
        _actor(is_active=False),
        _actor(deleted_at=datetime(2026, 9, 19, tzinfo=UTC)),
    ],
)
async def test_non_admin_inactive_or_deleted_actor_is_rejected(actor: User) -> None:
    mock, session = _session()

    with pytest.raises(AuditLogActorError, match="current active Admin"):
        await record_audit_log(
            session,
            actor,
            action="event.update",
            resource_type="event",
            resource_id=RESOURCE_ID,
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("action", "resource_type", "resource_id"),
    [
        (" ", "event", RESOURCE_ID),
        ("x" * 101, "event", RESOURCE_ID),
        ("event.update", " ", RESOURCE_ID),
        ("event.update", "x" * 101, RESOURCE_ID),
        ("event.update", "event", "not-a-uuid"),
    ],
)
async def test_invalid_event_identity_is_rejected(
    action: str, resource_type: str, resource_id: object
) -> None:
    mock, session = _session()

    with pytest.raises(AuditLogValidationError):
        await record_audit_log(
            session,
            _actor(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,  # type: ignore[arg-type]
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [{1: "value"}, {"unsupported": object()}])
async def test_non_json_payloads_are_rejected(payload: object) -> None:
    mock, session = _session()

    with pytest.raises(AuditLogValidationError):
        await record_audit_log(
            session,
            _actor(),
            action="event.update",
            resource_type="event",
            resource_id=RESOURCE_ID,
            new_value=cast(dict[str, object], payload),
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_cyclic_payload_is_rejected() -> None:
    payload: dict[str, object] = {}
    payload["self"] = payload
    _, session = _session()

    with pytest.raises(AuditLogValidationError, match="cycles"):
        await record_audit_log(
            session,
            _actor(),
            action="event.update",
            resource_type="event",
            resource_id=RESOURCE_ID,
            new_value=payload,
        )


@pytest.mark.anyio
async def test_flush_failure_propagates_without_commit_or_rollback() -> None:
    mock, session = _session()
    mock.flush.side_effect = RuntimeError("audit persistence failed")

    with pytest.raises(RuntimeError, match="audit persistence failed"):
        await record_audit_log(
            session,
            _actor(),
            action="event.update",
            resource_type="event",
            resource_id=RESOURCE_ID,
        )

    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()
