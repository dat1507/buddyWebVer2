"""Unit tests for transactional enqueue, template allowlisting, and lease claims."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TransactionalOutbox
from app.services.email_outbox import (
    OUTBOX_LEASE_TTL,
    EmailTemplateError,
    EmailTemplateRegistry,
    OutboxValidationError,
    RenderedEmailContent,
    claim_transactional_outbox,
    enqueue_transactional_email,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
AGGREGATE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.scalars = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_enqueue_stages_json_safe_metadata_without_committing_or_rendered_body() -> None:
    mock, session = _session()

    row = await enqueue_transactional_email(
        session,
        event_type="TEST_EVENT",
        aggregate_id=AGGREGATE_ID,
        recipient_user_id=USER_ID,
        recipient_email=" Student@Example.com ",
        idempotency_key="TEST_EVENT/aggregate",
        payload={"display_name": "Ada", "nested": {"count": 2}},
        clock=lambda: NOW,
    )

    mock.add.assert_called_once_with(row)
    mock.flush.assert_awaited_once_with()
    assert row.event_type == "TEST_EVENT"
    assert row.aggregate_id == AGGREGATE_ID
    assert row.recipient_user_id == USER_ID
    assert row.recipient_email == "student@example.com"
    assert row.idempotency_key == "TEST_EVENT/aggregate"
    assert row.payload == {"display_name": "Ada", "nested": {"count": 2}}
    assert row.attempts == 0
    assert row.next_attempt_at == NOW
    assert not hasattr(row, "subject")
    assert not hasattr(row, "body")
    assert not hasattr(mock, "commit") or mock.commit.await_count == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {"token": "plaintext"},
        {"verificationToken": "plaintext"},
        {"nested": {"password": "secret"}},
        {"nested": {"client_secret": "secret"}},
        {"items": [{"authorization": "bearer"}]},
        {"invalid": {1, 2, 3}},
        {"nan": float("nan")},
    ],
)
async def test_enqueue_rejects_secret_shaped_or_non_json_payloads(
    payload: dict[str, object],
) -> None:
    mock, session = _session()

    with pytest.raises(OutboxValidationError):
        await enqueue_transactional_email(
            session,
            event_type="TEST_EVENT",
            aggregate_id=AGGREGATE_ID,
            recipient_user_id=USER_ID,
            recipient_email="student@example.com",
            idempotency_key="TEST_EVENT/aggregate",
            payload=payload,
            clock=lambda: NOW,
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


def test_template_registry_is_an_explicit_allowlist_and_redacts_content() -> None:
    class TestRenderer:
        event_type = "TEST_EVENT"

        def render(self, payload: Mapping[str, object]) -> RenderedEmailContent:
            return RenderedEmailContent(
                subject="Hello",
                text_body=f"Welcome {payload['display_name']}",
            )

    registry = EmailTemplateRegistry((TestRenderer(),))
    content = registry.render("TEST_EVENT", {"display_name": "Ada"})

    assert content.subject == "Hello"
    assert content.text_body == "Welcome Ada"
    assert "Hello" not in repr(content)
    assert "Welcome Ada" not in repr(content)
    with pytest.raises(EmailTemplateError) as raised:
        registry.render("CLIENT_SELECTED_TEMPLATE", {})
    assert raised.value.error_code == "template_unregistered"
    assert "CLIENT_SELECTED_TEMPLATE" not in str(raised.value)


class _ScalarRows:
    def __init__(self, rows: list[TransactionalOutbox]) -> None:
        self._rows = rows

    def all(self) -> list[TransactionalOutbox]:
        return self._rows


@pytest.mark.anyio
async def test_claim_uses_skip_locked_and_recovers_expired_leases() -> None:
    first = TransactionalOutbox(
        id=uuid4(),
        event_type="TEST_EVENT",
        aggregate_id=AGGREGATE_ID,
        recipient_email="student@example.com",
        idempotency_key="TEST_EVENT/one",
        payload={},
        attempts=0,
        next_attempt_at=NOW,
    )
    first.lease_owner = "stale-worker"
    first.lease_expires_at = NOW - timedelta(seconds=1)
    second = TransactionalOutbox(
        id=uuid4(),
        event_type="TEST_EVENT",
        aggregate_id=AGGREGATE_ID,
        recipient_email="second@example.com",
        idempotency_key="TEST_EVENT/two",
        payload={},
        attempts=0,
        next_attempt_at=NOW,
    )
    mock, session = _session()
    mock.scalars.return_value = _ScalarRows([first, second])

    claimed = await claim_transactional_outbox(
        session,
        worker_id="worker-a",
        batch_size=2,
        clock=lambda: NOW,
    )

    assert claimed == (first.id, second.id)
    assert first.lease_owner == second.lease_owner == "worker-a"
    assert first.lease_expires_at == second.lease_expires_at == NOW + OUTBOX_LEASE_TTL
    mock.flush.assert_awaited_once_with()
    statement = mock.scalars.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    sql = str(statement.compile(dialect=dialect)).upper()
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "LEASE_EXPIRES_AT IS NULL OR" in sql
    assert "NEXT_ATTEMPT_AT" in sql


@pytest.mark.anyio
@pytest.mark.parametrize("batch_size", [0, 101])
async def test_claim_rejects_unbounded_batches(batch_size: int) -> None:
    mock, session = _session()

    with pytest.raises(OutboxValidationError, match="batch size"):
        await claim_transactional_outbox(
            session,
            worker_id="worker-a",
            batch_size=batch_size,
            clock=lambda: NOW,
        )

    mock.scalars.assert_not_awaited()
