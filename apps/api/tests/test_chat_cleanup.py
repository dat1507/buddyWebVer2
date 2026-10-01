"""CHAT-005 bounded cleanup service contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.chat_cleanup as cleanup_service
from app.services.chat_cleanup import (
    ChatCleanupReport,
    ChatCleanupValidationError,
    cleanup_expired_buddy_message_batch,
    process_chat_cleanup_batch,
)

NOW = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _session(*message_ids: UUID) -> tuple[MagicMock, AsyncSession]:
    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = list(message_ids)
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock(return_value=scalar_result)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_cleanup_calls_the_bounded_database_operation_and_returns_ids() -> None:
    first, second = uuid4(), uuid4()
    mock, session = _session(first, second)

    deleted_ids = await cleanup_expired_buddy_message_batch(
        session,
        batch_size=2,
        cleanup_now=NOW,
    )

    assert deleted_ids == (first, second)
    statement, parameters = mock.execute.await_args.args
    assert "app_private.cleanup_expired_buddy_messages" in str(statement)
    assert parameters == {"batch_size": 2, "cleanup_now": NOW}


@pytest.mark.anyio
async def test_cleanup_omits_timestamp_so_postgresql_owns_production_clock() -> None:
    mock, session = _session()

    assert await cleanup_expired_buddy_message_batch(session) == ()

    statement, parameters = mock.execute.await_args.args
    assert str(statement).count(":") == 1
    assert parameters == {"batch_size": 20}


@pytest.mark.anyio
@pytest.mark.parametrize("batch_size", (0, 101))
async def test_cleanup_rejects_unbounded_work(batch_size: int) -> None:
    mock, session = _session()

    with pytest.raises(ChatCleanupValidationError, match="batch size"):
        await cleanup_expired_buddy_message_batch(session, batch_size=batch_size)

    mock.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_cleanup_rejects_naive_test_timestamp_before_database_call() -> None:
    mock, session = _session()

    with pytest.raises(ChatCleanupValidationError, match="timezone-aware"):
        await cleanup_expired_buddy_message_batch(
            session,
            cleanup_now=datetime(2026, 10, 1, 6, 0),
        )

    mock.execute.assert_not_awaited()


def _factory(session: AsyncSession) -> MagicMock:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=context)


@pytest.mark.anyio
async def test_process_batch_commits_once_and_zero_is_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cleanup = AsyncMock(return_value=())
    monkeypatch.setattr(cleanup_service, "cleanup_expired_buddy_message_batch", cleanup)

    report = await process_chat_cleanup_batch(
        cast(async_sessionmaker[AsyncSession], _factory(session)),
        batch_size=7,
        cleanup_now=NOW,
    )

    assert report == ChatCleanupReport(selected=0, deleted=0)
    cleanup.assert_awaited_once_with(session, batch_size=7, cleanup_now=NOW)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_process_batch_rolls_back_and_reraises_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_error = RuntimeError("private message or database detail")
    mock, session = _session()
    monkeypatch.setattr(
        cleanup_service,
        "cleanup_expired_buddy_message_batch",
        AsyncMock(side_effect=private_error),
    )

    with pytest.raises(RuntimeError) as raised:
        await process_chat_cleanup_batch(cast(async_sessionmaker[AsyncSession], _factory(session)))

    assert raised.value is private_error
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


def test_report_contains_aggregate_counts_only() -> None:
    assert set(ChatCleanupReport.__dataclass_fields__) == {"selected", "deleted"}
    assert not {"message_id", "conversation_id", "body", "sender_id"}.intersection(
        ChatCleanupReport.__dataclass_fields__
    )
