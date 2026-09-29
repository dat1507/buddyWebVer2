"""Opt-in INV-002 acceptance against an isolated loopback PostgreSQL database.

Set INV002_TEST_DATABASE_URL to the disposable ``inv002_runner`` role in a
loopback-only database named ``inv002_acceptance``. The test upgrades that
database to the existing head and exercises real row locks and constraints.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import (
    InvitationExpiredError,
    InvitationStatus,
    InvitationTransitionError,
    MatchingInvitation,
)
from app.services.invitation_expiry import (
    effective_invitation_status,
    effective_pending_predicate,
    expire_invitation_batch,
    process_invitation_expiry_batch,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 6, 8, 30, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _invitation(
    sender_id: UUID,
    recipient_id: UUID,
    *,
    expires_at: datetime,
    status: InvitationStatus = InvitationStatus.PENDING,
) -> MatchingInvitation:
    created_at = expires_at - timedelta(days=7)
    invitation = MatchingInvitation(
        sender_id=sender_id,
        recipient_id=recipient_id,
        message="INV-002 acceptance",
        status=status,
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
        version=1,
    )
    if status in {InvitationStatus.ACCEPTED, InvitationStatus.DECLINED}:
        invitation.responded_at = created_at + timedelta(hours=1)
    elif status is InvitationStatus.CANCELLED:
        invitation.cancelled_at = created_at + timedelta(hours=1)
    elif status is InvitationStatus.EXPIRED:
        invitation.expired_at = expires_at
    return invitation


async def _create_users(engine: AsyncEngine, count: int) -> list[UUID]:
    user_ids = [uuid4() for _ in range(count)]
    async with engine.begin() as connection:
        for position, user_id in enumerate(user_ids):
            await connection.execute(
                text(
                    "INSERT INTO app_private.users (id, email, password_hash) "
                    "VALUES (:user_id, :email, 'test-only-hash')"
                ),
                {
                    "user_id": user_id,
                    "email": f"inv002-{user_id}-{position}@example.invalid",
                },
            )
    return user_ids


async def _load_status(
    factory: async_sessionmaker[AsyncSession],
    invitation_id: UUID,
) -> tuple[InvitationStatus, datetime | None, int]:
    async with factory() as session:
        row = await session.get(MatchingInvitation, invitation_id)
        assert row is not None
        return row.status, row.expired_at, row.version


async def _assert_expiry_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    user_ids = await _create_users(engine, 24)
    try:
        delayed = _invitation(
            user_ids[0], user_ids[1], expires_at=NOW - timedelta(days=2)
        )
        due_second = _invitation(
            user_ids[2], user_ids[3], expires_at=NOW - timedelta(seconds=1)
        )
        exact = _invitation(user_ids[4], user_ids[5], expires_at=NOW)
        future = _invitation(
            user_ids[6], user_ids[7], expires_at=NOW + timedelta(microseconds=1)
        )
        terminal_rows = [
            _invitation(
                user_ids[8],
                user_ids[9],
                expires_at=NOW - timedelta(days=1),
                status=status,
            )
            for status in (
                InvitationStatus.ACCEPTED,
                InvitationStatus.DECLINED,
                InvitationStatus.CANCELLED,
                InvitationStatus.EXPIRED,
            )
        ]
        # Give every terminal row a distinct pair.
        terminal_rows[1].sender_id, terminal_rows[1].recipient_id = user_ids[10], user_ids[11]
        terminal_rows[2].sender_id, terminal_rows[2].recipient_id = user_ids[12], user_ids[13]
        terminal_rows[3].sender_id, terminal_rows[3].recipient_id = user_ids[14], user_ids[15]

        async with factory() as session:
            session.add_all([delayed, due_second, exact, future, *terminal_rows])
            await session.commit()

        async with factory() as session:
            exact_before_cleanup = await session.get(MatchingInvitation, exact.id)
            assert exact_before_cleanup is not None
            assert exact_before_cleanup.status is InvitationStatus.PENDING
            assert (
                effective_invitation_status(exact_before_cleanup, at=NOW)
                is InvitationStatus.EXPIRED
            )
            with pytest.raises(InvitationExpiredError):
                exact_before_cleanup.accept(at=NOW)
            usable_count = await session.scalar(
                select(func.count())
                .select_from(MatchingInvitation)
                .where(effective_pending_predicate(at=NOW))
            )
            assert usable_count == 1

        first_report = await process_invitation_expiry_batch(
            factory,
            batch_size=2,
            clock=lambda: NOW,
        )
        assert first_report.selected == first_report.expired == 2
        assert (await _load_status(factory, delayed.id))[0] is InvitationStatus.EXPIRED
        assert (await _load_status(factory, due_second.id))[0] is InvitationStatus.EXPIRED
        assert (await _load_status(factory, exact.id))[0] is InvitationStatus.PENDING

        second_report = await process_invitation_expiry_batch(
            factory,
            batch_size=2,
            clock=lambda: NOW,
        )
        assert second_report.selected == second_report.expired == 1
        exact_status, exact_expired_at, exact_version = await _load_status(factory, exact.id)
        assert (exact_status, exact_expired_at, exact_version) == (
            InvitationStatus.EXPIRED,
            NOW,
            2,
        )
        assert (await _load_status(factory, future.id))[0] is InvitationStatus.PENDING
        assert [
            (await _load_status(factory, row.id))[0] for row in terminal_rows
        ] == [
            InvitationStatus.ACCEPTED,
            InvitationStatus.DECLINED,
            InvitationStatus.CANCELLED,
            InvitationStatus.EXPIRED,
        ]
        retry_report = await process_invitation_expiry_batch(
            factory,
            batch_size=20,
            clock=lambda: NOW,
        )
        assert retry_report.selected == retry_report.expired == 0

        async with factory() as session:
            reinvite = _invitation(
                exact.recipient_id,
                exact.sender_id,
                expires_at=NOW + timedelta(days=7),
            )
            session.add(reinvite)
            await session.commit()
            assert reinvite.status is InvitationStatus.PENDING

        worker_race = _invitation(user_ids[16], user_ids[17], expires_at=NOW)
        async with factory() as seed_session:
            seed_session.add(worker_race)
            await seed_session.commit()
        async with factory() as first_worker, factory() as second_worker:
            assert await expire_invitation_batch(
                first_worker, batch_size=1, clock=lambda: NOW
            ) == (worker_race.id,)
            assert await expire_invitation_batch(
                second_worker, batch_size=1, clock=lambda: NOW
            ) == ()
            await first_worker.commit()
            await second_worker.rollback()
        assert (
            await process_invitation_expiry_batch(factory, batch_size=1, clock=lambda: NOW)
        ).expired == 0

        accepted_race = _invitation(user_ids[18], user_ids[19], expires_at=NOW)
        async with factory() as seed_session:
            seed_session.add(accepted_race)
            await seed_session.commit()
        async with factory() as accept_session, factory() as expiry_session:
            accepting = await accept_session.scalar(
                select(MatchingInvitation)
                .where(MatchingInvitation.id == accepted_race.id)
                .with_for_update()
            )
            assert accepting is not None
            accepting.accept(at=NOW - timedelta(microseconds=1))
            await accept_session.flush()
            assert await expire_invitation_batch(
                expiry_session, batch_size=1, clock=lambda: NOW
            ) == ()
            await accept_session.commit()
            await expiry_session.rollback()
        assert (await _load_status(factory, accepted_race.id))[0] is InvitationStatus.ACCEPTED

        expiry_wins = _invitation(user_ids[20], user_ids[21], expires_at=NOW)
        async with factory() as seed_session:
            seed_session.add(expiry_wins)
            await seed_session.commit()
        async with factory() as expiry_session:
            assert await expire_invitation_batch(
                expiry_session, batch_size=1, clock=lambda: NOW
            ) == (expiry_wins.id,)
            await expiry_session.commit()
        async with factory() as late_accept_session:
            expired = await late_accept_session.get(MatchingInvitation, expiry_wins.id)
            assert expired is not None
            with pytest.raises(InvitationTransitionError):
                expired.accept(at=NOW)
            await late_accept_session.rollback()
    finally:
        await engine.dispose()


def test_live_expiry_boundary_batches_retries_and_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("INV002_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV002_TEST_DATABASE_URL for disposable INV-002 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv002_acceptance"
        or parsed_url.username != "inv002_runner"
    ):
        pytest.fail(
            "INV-002 requires the disposable inv002_runner role in the isolated "
            "loopback inv002_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "head")
        asyncio.run(_assert_expiry_contract(async_database_url))
    finally:
        get_migration_database_settings.cache_clear()
