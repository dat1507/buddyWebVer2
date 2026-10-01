"""Opt-in CHAT-005 acceptance on an isolated loopback PostgreSQL database.

Set CHAT005_TEST_DATABASE_URL to the disposable ``chat005_runner`` role in a
database named ``chat005_acceptance``. The test exercises real row locks,
physical deletion, relationship safety, and the migration cycle.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import BuddyConversation, BuddyMatch, BuddyMessage, StudentType
from app.services.buddy_chat import list_buddy_messages
from app.services.chat_cleanup import (
    cleanup_expired_buddy_message_batch,
    process_chat_cleanup_batch,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _current_revision(database_url: str) -> str | None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(text("SELECT to_regclass('alembic_version')"))
            if exists is None:
                return None
            return cast(
                str | None,
                await connection.scalar(text("SELECT version_num FROM alembic_version")),
            )
    finally:
        await engine.dispose()


def _message_values(
    *,
    conversation_id: UUID,
    sender_id: UUID,
    expires_at: datetime,
    body: str,
    read: bool = False,
) -> dict[str, object]:
    if read:
        created_at = expires_at - timedelta(days=60)
        read_at: datetime | None = expires_at - timedelta(days=30)
    else:
        created_at = expires_at - timedelta(days=90)
        read_at = None
    return {
        "id": uuid4(),
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "client_message_id": uuid4(),
        "body": body,
        "created_at": created_at,
        "read_at": read_at,
        "expires_at": expires_at,
    }


async def _seed_relationship(
    engine: AsyncEngine,
) -> tuple[list[UUID], UUID, UUID, datetime, dict[str, dict[str, object]]]:
    user_ids = [uuid4(), uuid4()]
    profile_ids = [uuid4(), uuid4()]
    invitation_id = uuid4()
    match_id = uuid4()
    conversation_id = uuid4()
    async with engine.begin() as connection:
        cleanup_now = await connection.scalar(
            text("SELECT statement_timestamp() - interval '1 hour'")
        )
        assert isinstance(cleanup_now, datetime)
        await connection.execute(
            text(
                "INSERT INTO app_private.users (id, email, password_hash) "
                "VALUES (:id, :email, 'test-only-hash')"
            ),
            [
                {"id": user_id, "email": f"chat005-{user_id}@example.invalid"}
                for user_id in user_ids
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, student_type) "
                "VALUES (:id, :user_id, :full_name, :student_type)"
            ),
            [
                {
                    "id": profile_ids[0],
                    "user_id": user_ids[0],
                    "full_name": "CHAT-005 Vietnamese participant",
                    "student_type": StudentType.VIETNAMESE.value,
                },
                {
                    "id": profile_ids[1],
                    "user_id": user_ids[1],
                    "full_name": "CHAT-005 international participant",
                    "student_type": StudentType.INTERNATIONAL.value,
                },
            ],
        )
        accepted_at = cleanup_now - timedelta(days=1)
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, 'CHAT-005 acceptance', 'ACCEPTED', "
                ":created_at, :updated_at, :expires_at, :responded_at)"
            ),
            {
                "id": invitation_id,
                "sender_id": user_ids[0],
                "recipient_id": user_ids[1],
                "created_at": accepted_at - timedelta(days=1),
                "updated_at": accepted_at,
                "expires_at": accepted_at + timedelta(days=6),
                "responded_at": accepted_at,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matches "
                "(id, participant_one_user_id, participant_two_user_id, "
                "participant_one_profile_id, participant_two_profile_id, "
                "accepted_invitation_id, score, score_breakdown, activated_at) VALUES "
                "(:id, :first_user_id, :second_user_id, :first_profile_id, "
                ":second_profile_id, :invitation_id, 80, '{}'::jsonb, :activated_at)"
            ),
            {
                "id": match_id,
                "first_user_id": user_ids[0],
                "second_user_id": user_ids[1],
                "first_profile_id": profile_ids[0],
                "second_profile_id": profile_ids[1],
                "invitation_id": invitation_id,
                "activated_at": accepted_at,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_conversations (id, match_id, created_at) "
                "VALUES (:id, :match_id, :created_at)"
            ),
            {"id": conversation_id, "match_id": match_id, "created_at": accepted_at},
        )

        messages = {
            "initial": _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[0],
                expires_at=cleanup_now - timedelta(hours=3),
                body="initial 90-day expiry",
            ),
            "read_shortened": _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[1],
                expires_at=cleanup_now - timedelta(hours=2),
                body="first-read shortened expiry",
                read=True,
            ),
            "exact": _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[0],
                expires_at=cleanup_now,
                body="exact cleanup boundary",
            ),
            "after_boundary": _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[1],
                expires_at=cleanup_now + timedelta(microseconds=1),
                body="one microsecond after cleanup boundary",
            ),
            "future": _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[0],
                expires_at=cleanup_now + timedelta(days=2),
                body="unexpired message",
            ),
        }
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_messages "
                "(id, conversation_id, sender_id, client_message_id, body, created_at, "
                "read_at, expires_at) VALUES "
                "(:id, :conversation_id, :sender_id, :client_message_id, :body, "
                ":created_at, :read_at, :expires_at)"
            ),
            list(messages.values()),
        )
    return user_ids, match_id, conversation_id, cleanup_now, messages


async def _insert_messages(
    engine: AsyncEngine,
    values: list[dict[str, object]],
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_messages "
                "(id, conversation_id, sender_id, client_message_id, body, created_at, "
                "read_at, expires_at) VALUES "
                "(:id, :conversation_id, :sender_id, :client_message_id, :body, "
                ":created_at, :read_at, :expires_at)"
            ),
            values,
        )


async def _remaining_message_ids(
    factory: async_sessionmaker[AsyncSession],
    conversation_id: UUID,
) -> set[UUID]:
    async with factory() as session:
        return set(
            (
                await session.scalars(
                    select(BuddyMessage.id).where(BuddyMessage.conversation_id == conversation_id)
                )
            ).all()
        )


async def _assert_cleanup_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    user_ids: list[UUID] = []
    try:
        user_ids, match_id, conversation_id, cleanup_now, messages = await _seed_relationship(
            engine
        )

        async with engine.connect() as connection:
            privileges = (
                await connection.execute(
                    text(
                        "SELECT "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.buddy_messages', 'DELETE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.buddy_conversations', 'DELETE'), "
                        "has_function_privilege('vgu_buddy_runtime', "
                        "'app_private.cleanup_expired_buddy_messages(integer, timestamp with time zone)', "
                        "'EXECUTE')"
                    )
                )
            ).one()
            assert privileges == (False, False, True)
            function_security = (
                await connection.execute(
                    text(
                        "SELECT pg_proc.prosecdef, pg_proc.proconfig "
                        "FROM pg_proc JOIN pg_namespace "
                        "ON pg_namespace.oid = pg_proc.pronamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND pg_proc.proname = 'cleanup_expired_buddy_messages'"
                    )
                )
            ).one()
            assert function_security.prosecdef is True
            assert function_security.proconfig == ['search_path=""']

        async with engine.connect() as runtime_connection:
            transaction = await runtime_connection.begin()
            await runtime_connection.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            runtime_deleted = await runtime_connection.scalar(
                text(
                    "SELECT count(*) FROM "
                    "app_private.cleanup_expired_buddy_messages(:batch_size, :cleanup_now)"
                ),
                {
                    "batch_size": 1,
                    "cleanup_now": cleanup_now - timedelta(hours=4),
                },
            )
            assert runtime_deleted == 0
            await transaction.rollback()

        async with engine.connect() as runtime_connection:
            transaction = await runtime_connection.begin()
            await runtime_connection.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            with pytest.raises(DBAPIError):
                await runtime_connection.execute(
                    text("DELETE FROM app_private.buddy_messages WHERE id = :message_id"),
                    {"message_id": messages["future"]["id"]},
                )
            await transaction.rollback()

        async with factory() as session:
            before_cleanup = await list_buddy_messages(
                session,
                conversation_id=conversation_id,
                authenticated_user_id=user_ids[0],
                page_size=20,
                clock=lambda: cleanup_now,
            )
            visible_ids = {message.id for message in before_cleanup.items}
            assert messages["exact"]["id"] not in visible_ids
            assert messages["after_boundary"]["id"] in visible_ids

        first = await process_chat_cleanup_batch(
            factory,
            batch_size=2,
            cleanup_now=cleanup_now,
        )
        assert first.selected == first.deleted == 2
        remaining = await _remaining_message_ids(factory, conversation_id)
        assert messages["initial"]["id"] not in remaining
        assert messages["read_shortened"]["id"] not in remaining
        assert messages["exact"]["id"] in remaining

        second = await process_chat_cleanup_batch(
            factory,
            batch_size=2,
            cleanup_now=cleanup_now,
        )
        assert second.selected == second.deleted == 1
        assert (
            await process_chat_cleanup_batch(
                factory,
                batch_size=20,
                cleanup_now=cleanup_now,
            )
        ).deleted == 0
        remaining = await _remaining_message_ids(factory, conversation_id)
        assert messages["exact"]["id"] not in remaining
        assert messages["after_boundary"]["id"] in remaining
        assert messages["future"]["id"] in remaining

        race_values = [
            _message_values(
                conversation_id=conversation_id,
                sender_id=user_ids[position % 2],
                expires_at=cleanup_now - timedelta(minutes=50 - position),
                body=f"concurrent cleanup {position}",
            )
            for position in range(4)
        ]
        await _insert_messages(engine, race_values)
        expected_race_ids = {value["id"] for value in race_values}
        async with factory() as first_worker, factory() as second_worker:
            first_ids = await cleanup_expired_buddy_message_batch(
                first_worker,
                batch_size=2,
                cleanup_now=cleanup_now,
            )
            second_ids = await asyncio.wait_for(
                cleanup_expired_buddy_message_batch(
                    second_worker,
                    batch_size=2,
                    cleanup_now=cleanup_now,
                ),
                timeout=5,
            )
            assert set(first_ids).isdisjoint(second_ids)
            assert set(first_ids).union(second_ids) == expected_race_ids
            await second_worker.commit()
            await first_worker.commit()

        resumed = _message_values(
            conversation_id=conversation_id,
            sender_id=user_ids[0],
            expires_at=cleanup_now - timedelta(minutes=5),
            body="rollback and resume",
        )
        await _insert_messages(engine, [resumed])
        async with factory() as failed_worker:
            assert await cleanup_expired_buddy_message_batch(
                failed_worker,
                batch_size=1,
                cleanup_now=cleanup_now,
            ) == (resumed["id"],)
            await failed_worker.rollback()
        assert (
            await process_chat_cleanup_batch(
                factory,
                batch_size=1,
                cleanup_now=cleanup_now,
            )
        ).deleted == 1

        default_clock_message = _message_values(
            conversation_id=conversation_id,
            sender_id=user_ids[0],
            expires_at=cleanup_now + timedelta(minutes=30),
            body="database default clock",
        )
        await _insert_messages(engine, [default_clock_message])
        assert (await process_chat_cleanup_batch(factory, batch_size=2)).deleted == 2

        async with factory() as invalid_clock:
            with pytest.raises(DBAPIError):
                await cleanup_expired_buddy_message_batch(
                    invalid_clock,
                    cleanup_now=cleanup_now + timedelta(days=7),
                )
            await invalid_clock.rollback()

        async with factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(BuddyConversation)
                    .where(BuddyConversation.id == conversation_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(BuddyMatch).where(BuddyMatch.id == match_id)
                )
                == 1
            )
            final_ids = await _remaining_message_ids(factory, conversation_id)
            assert messages["after_boundary"]["id"] not in final_ids
            assert default_clock_message["id"] not in final_ids
            assert messages["future"]["id"] in final_ids
    finally:
        if user_ids:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM app_private.users WHERE id = ANY(:user_ids)"),
                    {"user_ids": user_ids},
                )
        await engine.dispose()


async def _assert_function_absent_and_chat_preserved(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text(
                        "SELECT to_regprocedure("
                        "'app_private.cleanup_expired_buddy_messages(integer, timestamp with time zone)')"
                    )
                )
                is None
            )
            assert (
                await connection.scalar(text("SELECT to_regclass('app_private.buddy_messages')"))
                == "app_private.buddy_messages"
            )
    finally:
        await engine.dispose()


def test_live_cleanup_boundary_batches_concurrency_and_migration_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("CHAT005_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CHAT005_TEST_DATABASE_URL for disposable CHAT-005 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "chat005_acceptance"
        or parsed_url.username != "chat005_runner"
    ):
        pytest.fail(
            "CHAT-005 requires the disposable chat005_runner role in the isolated "
            "loopback chat005_acceptance database."
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
        command.check(config)
        asyncio.run(_assert_cleanup_contract(async_database_url))
        command.downgrade(config, "0015_chat_send_idempotency")
        asyncio.run(_assert_function_absent_and_chat_preserved(async_database_url))
        command.upgrade(config, "head")
        command.check(config)
    finally:
        if asyncio.run(_current_revision(async_database_url)) == "0016_chat_message_cleanup":
            command.downgrade(config, "0015_chat_send_idempotency")
        get_migration_database_settings.cache_clear()
