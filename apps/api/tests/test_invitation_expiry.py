"""INV-002 authoritative expiry predicates and bounded transition job tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.invitation_expiry as expiry_service
from app.models import InvitationStatus, MatchingInvitation
from app.services.invitation_expiry import (
    InvitationExpiryReport,
    InvitationExpiryValidationError,
    effective_invitation_status,
    effective_pending_predicate,
    expire_invitation_batch,
    expired_pending_predicate,
    process_invitation_expiry_batch,
)

NOW = datetime(2026, 10, 6, 8, 30, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _invitation(*, expires_at: datetime, status: InvitationStatus) -> MatchingInvitation:
    return MatchingInvitation(
        id=uuid4(),
        sender_id=uuid4(),
        recipient_id=uuid4(),
        message="Hello",
        status=status,
        created_at=expires_at - timedelta(days=7),
        expires_at=expires_at,
    )


@pytest.mark.parametrize(
    ("offset", "expected"),
    (
        (timedelta(microseconds=1), InvitationStatus.PENDING),
        (timedelta(0), InvitationStatus.EXPIRED),
        (-timedelta(microseconds=1), InvitationStatus.EXPIRED),
    ),
)
def test_effective_status_uses_exact_inclusive_deadline(
    offset: timedelta,
    expected: InvitationStatus,
) -> None:
    invitation = _invitation(expires_at=NOW + offset, status=InvitationStatus.PENDING)

    assert effective_invitation_status(invitation, at=NOW) is expected


def test_effective_status_is_timezone_safe_and_never_rewrites_terminal_status() -> None:
    local_time = NOW.astimezone(timezone(timedelta(hours=7)))
    pending = _invitation(expires_at=NOW, status=InvitationStatus.PENDING)
    accepted = _invitation(expires_at=NOW - timedelta(days=1), status=InvitationStatus.ACCEPTED)

    assert effective_invitation_status(pending, at=local_time) is InvitationStatus.EXPIRED
    assert effective_invitation_status(accepted, at=local_time) is InvitationStatus.ACCEPTED
    with pytest.raises(ValueError, match="timezone-aware"):
        effective_invitation_status(pending, at=NOW.replace(tzinfo=None))


def test_shared_query_predicates_encode_usable_and_due_boundaries() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    usable_sql = str(effective_pending_predicate(at=NOW).compile(dialect=dialect)).upper()
    due_sql = str(expired_pending_predicate(at=NOW).compile(dialect=dialect)).upper()

    assert "STATUS" in usable_sql
    assert "EXPIRES_AT >" in usable_sql
    assert "STATUS" in due_sql
    assert "EXPIRES_AT <=" in due_sql


class _ScalarRows:
    def __init__(self, rows: list[MatchingInvitation]) -> None:
        self._rows = rows

    def all(self) -> list[MatchingInvitation]:
        return self._rows


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalars = AsyncMock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_expiry_batch_is_bounded_deterministic_and_uses_skip_locked() -> None:
    first = _invitation(expires_at=NOW - timedelta(seconds=1), status=InvitationStatus.PENDING)
    second = _invitation(expires_at=NOW, status=InvitationStatus.PENDING)
    mock, session = _session()
    mock.scalars.return_value = _ScalarRows([first, second])

    expired_ids = await expire_invitation_batch(
        session,
        batch_size=2,
        clock=lambda: NOW,
    )

    assert expired_ids == (first.id, second.id)
    assert first.status is second.status is InvitationStatus.EXPIRED
    assert first.expired_at == second.expired_at == NOW
    mock.flush.assert_awaited_once_with()
    statement = mock.scalars.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    sql = str(statement.compile(dialect=dialect)).upper()
    assert "ORDER BY" in sql
    assert "EXPIRES_AT" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "LIMIT" in sql


@pytest.mark.anyio
@pytest.mark.parametrize("batch_size", (0, 101))
async def test_expiry_batch_rejects_unbounded_work(batch_size: int) -> None:
    mock, session = _session()

    with pytest.raises(InvitationExpiryValidationError, match="batch size"):
        await expire_invitation_batch(session, batch_size=batch_size, clock=lambda: NOW)

    mock.scalars.assert_not_awaited()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_process_batch_commits_once_and_is_retry_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invitation_ids = (uuid4(), uuid4())
    expire = AsyncMock(return_value=invitation_ids)
    mock, session = _session()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)
    monkeypatch.setattr(expiry_service, "expire_invitation_batch", expire)

    report = await process_invitation_expiry_batch(
        cast(async_sessionmaker[AsyncSession], factory),
        batch_size=7,
        clock=lambda: NOW,
    )

    assert report == InvitationExpiryReport(selected=2, expired=2)
    expire.assert_awaited_once_with(session, batch_size=7, clock=ANY)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_process_batch_rolls_back_and_reraises_without_partial_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_error = RuntimeError("private database detail")
    expire = AsyncMock(side_effect=private_error)
    mock, session = _session()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)
    monkeypatch.setattr(expiry_service, "expire_invitation_batch", expire)

    with pytest.raises(RuntimeError) as raised:
        await process_invitation_expiry_batch(
            cast(async_sessionmaker[AsyncSession], factory),
            clock=lambda: NOW,
        )

    assert raised.value is private_error
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
