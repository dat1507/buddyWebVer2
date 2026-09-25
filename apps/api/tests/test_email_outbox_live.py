"""Opt-in MAIL-001 acceptance against an empty disposable PostgreSQL database."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    MigrationDatabaseSettings,
    get_migration_database_settings,
)
from app.core.database import migration_database_url
from app.models import TransactionalOutbox, User
from app.services.email_outbox import (
    EmailTemplateRegistry,
    RenderedEmailContent,
    enqueue_transactional_email,
    process_transactional_outbox_batch,
)
from app.services.email_provider import (
    EmailDelivery,
    EmailDeliveryError,
    OutboundEmail,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


class _TestRenderer:
    event_type = "TEST_EVENT"

    def render(self, payload: Mapping[str, object]) -> RenderedEmailContent:
        return RenderedEmailContent(
            subject="Buddy Website notification",
            text_body=f"Hello {payload['display_name']}",
        )


class _FakeProvider:
    def __init__(
        self,
        outcomes: list[EmailDelivery | EmailDeliveryError] | None = None,
    ) -> None:
        self.outcomes = list(outcomes or [])
        self.idempotency_keys: list[str] = []

    async def send(
        self,
        message: OutboundEmail,
        *,
        idempotency_key: str,
    ) -> EmailDelivery:
        assert "Buddy Website" in message.subject
        self.idempotency_keys.append(idempotency_key)
        outcome = self.outcomes.pop(0) if self.outcomes else EmailDelivery("fake-message")
        if isinstance(outcome, EmailDeliveryError):
            raise outcome
        return outcome


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _retryable_failure() -> EmailDeliveryError:
    return EmailDeliveryError(retryable=True, error_code="provider_unavailable")


def _clock(value: datetime) -> Callable[[], datetime]:
    return lambda: value


async def _enqueue(
    factory: async_sessionmaker[AsyncSession],
    *,
    user_id: UUID,
    event_type: str,
    key: str,
    at: datetime,
) -> UUID:
    async with factory() as session:
        row = await enqueue_transactional_email(
            session,
            event_type=event_type,
            aggregate_id=uuid4(),
            recipient_user_id=user_id,
            recipient_email="mail001-user@example.invalid",
            idempotency_key=key,
            payload={"display_name": "Ada"},
            clock=lambda: at,
        )
        await session.commit()
        return row.id


async def _assert_delivery_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    templates = EmailTemplateRegistry((_TestRenderer(),))
    user_id = uuid4()
    origin_key = "TEST_EVENT/origin"
    try:
        async with factory() as session:
            session.add(
                User(
                    id=user_id,
                    email="mail001-user@example.invalid",
                    password_hash="test-only-hash",
                )
            )
            await session.flush()
            origin = await enqueue_transactional_email(
                session,
                event_type="TEST_EVENT",
                aggregate_id=user_id,
                recipient_user_id=user_id,
                recipient_email="mail001-user@example.invalid",
                idempotency_key=origin_key,
                payload={"display_name": "Ada"},
                clock=lambda: NOW,
            )
            origin_id = origin.id
            await session.commit()

        provider = _FakeProvider(
            [_retryable_failure(), EmailDelivery(provider_message_id="fake-success")]
        )
        first = await process_transactional_outbox_batch(
            factory,
            worker_id="mail001-worker",
            provider=provider,
            templates=templates,
            clock=lambda: NOW,
        )
        assert (first.claimed, first.retry_scheduled) == (1, 1)
        async with factory() as session:
            assert await session.get(User, user_id) is not None
            stored = await session.get(TransactionalOutbox, origin_id)
            assert stored is not None
            assert stored.attempts == 1
            assert stored.next_attempt_at == NOW + timedelta(minutes=1)
            assert stored.lease_owner is None

        second = await process_transactional_outbox_batch(
            factory,
            worker_id="mail001-worker",
            provider=provider,
            templates=templates,
            clock=lambda: NOW + timedelta(minutes=1),
        )
        assert (second.claimed, second.sent) == (1, 1)
        assert provider.idempotency_keys == [origin_key, origin_key]
        duplicate_pass = await process_transactional_outbox_batch(
            factory,
            worker_id="mail001-worker",
            provider=provider,
            templates=templates,
            clock=lambda: NOW + timedelta(minutes=1),
        )
        assert duplicate_pass.claimed == 0
        assert provider.idempotency_keys == [origin_key, origin_key]

        async with factory() as session:
            with pytest.raises(IntegrityError):
                await enqueue_transactional_email(
                    session,
                    event_type="TEST_EVENT",
                    aggregate_id=uuid4(),
                    recipient_user_id=user_id,
                    recipient_email="mail001-user@example.invalid",
                    idempotency_key=origin_key,
                    payload={"display_name": "Ada"},
                    clock=lambda: NOW,
                )
                await session.commit()
            await session.rollback()

        bounded_id = await _enqueue(
            factory,
            user_id=user_id,
            event_type="TEST_EVENT",
            key="TEST_EVENT/bounded",
            at=NOW + timedelta(minutes=2),
        )
        bounded_provider = _FakeProvider([_retryable_failure() for _ in range(5)])
        for elapsed_minutes in (2, 3, 5, 9, 17):
            attempt_time = NOW + timedelta(minutes=elapsed_minutes)
            await process_transactional_outbox_batch(
                factory,
                worker_id="bounded-worker",
                provider=bounded_provider,
                templates=templates,
                clock=_clock(attempt_time),
            )
        async with factory() as session:
            bounded = await session.get(TransactionalOutbox, bounded_id)
            assert bounded is not None
            assert bounded.attempts == 5
            assert bounded.failed_at == NOW + timedelta(minutes=17)
            assert bounded.last_error_code == "provider_unavailable"
            assert bounded.lease_owner is None

        lease_time = NOW + timedelta(minutes=20)
        lease_id = await _enqueue(
            factory,
            user_id=user_id,
            event_type="TEST_EVENT",
            key="TEST_EVENT/stale-lease",
            at=lease_time,
        )
        async with factory() as session:
            leased = await session.get(TransactionalOutbox, lease_id)
            assert leased is not None
            leased.lease_owner = "dead-worker"
            leased.lease_expires_at = lease_time - timedelta(seconds=1)
            await session.commit()
        recovered = await process_transactional_outbox_batch(
            factory,
            worker_id="replacement-worker",
            provider=_FakeProvider(),
            templates=templates,
            clock=lambda: lease_time,
        )
        assert (recovered.claimed, recovered.sent) == (1, 1)

        concurrent_time = NOW + timedelta(minutes=21)
        await _enqueue(
            factory,
            user_id=user_id,
            event_type="TEST_EVENT",
            key="TEST_EVENT/concurrent",
            at=concurrent_time,
        )
        concurrent_provider = _FakeProvider()
        reports = await asyncio.gather(
            process_transactional_outbox_batch(
                factory,
                worker_id="worker-one",
                provider=concurrent_provider,
                templates=templates,
                clock=lambda: concurrent_time,
            ),
            process_transactional_outbox_batch(
                factory,
                worker_id="worker-two",
                provider=concurrent_provider,
                templates=templates,
                clock=lambda: concurrent_time,
            ),
        )
        assert sum(report.claimed for report in reports) == 1
        assert concurrent_provider.idempotency_keys == ["TEST_EVENT/concurrent"]

        unknown_time = NOW + timedelta(minutes=22)
        unknown_id = await _enqueue(
            factory,
            user_id=user_id,
            event_type="UNKNOWN_EVENT",
            key="UNKNOWN_EVENT/blocked",
            at=unknown_time,
        )
        unused_provider = _FakeProvider()
        unknown = await process_transactional_outbox_batch(
            factory,
            worker_id="template-worker",
            provider=unused_provider,
            templates=templates,
            clock=lambda: unknown_time,
        )
        assert (unknown.claimed, unknown.terminal_failed) == (1, 1)
        assert unused_provider.idempotency_keys == []
        async with factory() as session:
            blocked = await session.get(TransactionalOutbox, unknown_id)
            assert blocked is not None
            assert blocked.last_error_code == "template_unregistered"
            assert blocked.failed_at == unknown_time
            persisted_columns = set(TransactionalOutbox.__table__.columns.keys())
            assert {"subject", "body", "provider_response"}.isdisjoint(persisted_columns)
    finally:
        await engine.dispose()


async def _assert_downgrade(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT to_regclass('app_private.transactional_outbox')")
                )
                is None
            )
    finally:
        await engine.dispose()


async def _claim_edge_jobs(
    factory: async_sessionmaker[AsyncSession],
    worker_id: str,
) -> list[Mapping[str, object]]:
    async with factory() as session:
        await session.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
        result = await session.execute(
            text(
                "SELECT id, event_type, recipient_email, idempotency_key, payload "
                "FROM app_private.claim_transactional_email_outbox(:worker_id, 20)"
            ),
            {"worker_id": worker_id},
        )
        rows: list[Mapping[str, object]] = [dict(row) for row in result.mappings().all()]
        await session.commit()
        return rows


async def _assert_edge_database_claim_contract(database_url: str) -> None:
    """Prove two database-backed Edge claims cannot acquire the same ready row."""
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            user_id = await session.scalar(select(User.id).limit(1))
        assert user_id is not None

        empty = await _claim_edge_jobs(factory, "edge-empty-live")
        assert empty == []

        outbox_id = await _enqueue(
            factory,
            user_id=user_id,
            event_type="TEST_EVENT",
            key="TEST_EVENT/edge-concurrent-live",
            at=datetime.now(UTC) - timedelta(minutes=1),
        )
        claims = await asyncio.gather(
            _claim_edge_jobs(factory, "edge-live-one"),
            _claim_edge_jobs(factory, "edge-live-two"),
        )
        claimed = [row for worker_rows in claims for row in worker_rows]
        assert [row["id"] for row in claimed] == [outbox_id]

        owner = "edge-live-one" if claims[0] else "edge-live-two"
        async with factory() as session:
            await session.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            outcome = await session.scalar(
                text(
                    "SELECT app_private.complete_transactional_email_outbox("
                    ":outbox_id, :worker_id, :provider_message_id)"
                ),
                {
                    "outbox_id": outbox_id,
                    "worker_id": owner,
                    "provider_message_id": "edge-live-provider-message",
                },
            )
            await session.commit()
        assert outcome == "sent"
        assert await _claim_edge_jobs(factory, "edge-live-after-complete") == []
    finally:
        await engine.dispose()


def test_live_outbox_upgrade_delivery_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("MAIL001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set MAIL001_TEST_DATABASE_URL for disposable MAIL-001 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "mail001_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "MAIL-001 requires the privileged postgres role in the isolated loopback "
            "mail001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = migration_database_url(
        MigrationDatabaseSettings(url=SecretStr(database_url))
    ).render_as_string(hide_password=False)
    failed_stage: str | None = None
    stage = "upgrade MAIL-001"
    try:
        command.upgrade(config, "head")
        stage = "verify MAIL-001 delivery contract"
        asyncio.run(_assert_delivery_contract(async_database_url))
        stage = "verify Edge worker atomic claim contract"
        asyncio.run(_assert_edge_database_claim_contract(async_database_url))
        stage = "downgrade MAIL-001"
        command.downgrade(config, "0008_email_verification")
        asyncio.run(_assert_downgrade(async_database_url))
        stage = "re-upgrade MAIL-001"
        command.upgrade(config, "head")
    except Exception as error:
        failed_stage = f"{stage} ({type(error).__name__})"
    finally:
        try:
            command.downgrade(config, "0008_email_verification")
        except Exception:
            failed_stage = failed_stage or "final MAIL-001 cleanup"
        get_migration_database_settings.cache_clear()
    if failed_stage is not None:
        pytest.fail(
            f"MAIL-001 disposable acceptance failed during {failed_stage}; "
            "database details were suppressed.",
            pytrace=False,
        )
