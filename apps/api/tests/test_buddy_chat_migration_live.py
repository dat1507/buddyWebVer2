"""Opt-in CHAT-001 migration, integrity, and concurrency acceptance on PostgreSQL.

Set CHAT001_TEST_DATABASE_URL to the disposable ``chat001_runner`` role in a
loopback-only database named ``chat001_acceptance``. The test returns that
database to revision 0013 and must never target development or production data.
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
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import BuddyConversation, BuddyMessage, StudentType
from app.services.buddy_chat import (
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    get_or_create_buddy_conversation,
    persist_buddy_message,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 6, 0, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_contract_rows(
    engine: AsyncEngine,
) -> tuple[list[UUID], list[UUID]]:
    user_ids = [uuid4() for _ in range(4)]
    profile_ids = [uuid4() for _ in range(4)]
    invitation_ids = [uuid4() for _ in range(2)]
    match_ids = [uuid4() for _ in range(2)]
    student_types = (
        StudentType.VIETNAMESE,
        StudentType.INTERNATIONAL,
        StudentType.INTERNATIONAL,
        StudentType.INTERNATIONAL,
    )
    pairs = ((user_ids[0], user_ids[1]), (user_ids[0], user_ids[2]))
    created_at = NOW - timedelta(hours=1)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users (id, email, password_hash) "
                "VALUES (:id, :email, 'test-only-hash')"
            ),
            [
                {"id": user_id, "email": f"chat001-{user_id}@example.invalid"}
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
                    "id": profile_ids[index],
                    "user_id": user_id,
                    "full_name": f"Chat participant {index}",
                    "student_type": student_types[index].value,
                }
                for index, user_id in enumerate(user_ids)
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, :message, 'ACCEPTED', :created_at, "
                ":updated_at, :expires_at, :responded_at)"
            ),
            [
                {
                    "id": invitation_ids[index],
                    "sender_id": pair[0],
                    "recipient_id": pair[1],
                    "message": f"Accepted chat invitation {index}",
                    "created_at": created_at,
                    "updated_at": NOW,
                    "expires_at": created_at + timedelta(days=7),
                    "responded_at": NOW,
                }
                for index, pair in enumerate(pairs)
            ],
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
            [
                {
                    "id": match_ids[index],
                    "first_user_id": pair[0],
                    "second_user_id": pair[1],
                    "first_profile_id": profile_ids[0],
                    "second_profile_id": profile_ids[index + 1],
                    "invitation_id": invitation_ids[index],
                    "activated_at": NOW,
                }
                for index, pair in enumerate(pairs)
            ],
        )
    return user_ids, match_ids


async def _conversation(
    factory: async_sessionmaker[AsyncSession],
    match_id: UUID,
) -> BuddyConversation:
    async with factory() as session:
        conversation = await get_or_create_buddy_conversation(
            session,
            match_id=match_id,
            clock=lambda: NOW,
        )
        await session.commit()
        return conversation


async def _message(
    factory: async_sessionmaker[AsyncSession],
    *,
    conversation_id: UUID,
    sender_id: UUID,
    body: str,
) -> BuddyMessage:
    async with factory() as session:
        message = await persist_buddy_message(
            session,
            conversation_id=conversation_id,
            authenticated_sender_id=sender_id,
            body=body,
            clock=lambda: NOW,
        )
        await session.commit()
        return message


async def _expect_integrity_error(
    engine: AsyncEngine,
    statement: str,
    parameters: dict[str, object],
) -> None:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        with pytest.raises(IntegrityError):
            await connection.execute(text(statement), parameters)
        await transaction.rollback()


async def _assert_schema_security_and_indexes(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        rls = {
            row.relname: row.relrowsecurity
            for row in (
                await connection.execute(
                    text(
                        "SELECT pg_class.relname, pg_class.relrowsecurity "
                        "FROM pg_class JOIN pg_namespace "
                        "ON pg_namespace.oid = pg_class.relnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND pg_class.relname IN ('buddy_conversations', 'buddy_messages')"
                    )
                )
            )
        }
        assert rls == {"buddy_conversations": True, "buddy_messages": True}

        privileges = (
            await connection.execute(
                text(
                    "SELECT "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_conversations', 'SELECT'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_conversations', 'UPDATE'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_conversations', 'DELETE'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_messages', 'SELECT'), "
                    "has_table_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_messages', 'DELETE'), "
                    "has_column_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_messages', 'read_at', 'UPDATE'), "
                    "has_column_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_messages', 'expires_at', 'UPDATE'), "
                    "has_column_privilege('vgu_buddy_runtime', "
                    "'app_private.buddy_messages', 'body', 'UPDATE')"
                )
            )
        ).one()
        assert privileges == (True, False, False, True, False, True, True, False)
        assert (
            await connection.scalar(
                text(
                    "SELECT has_function_privilege("
                    "'vgu_buddy_runtime', "
                    "'app_private.enforce_buddy_message_sender()', 'EXECUTE')"
                )
            )
            is False
        )

        indexes = {
            row.relname: row.indisunique
            for row in (
                await connection.execute(
                    text(
                        "SELECT index_class.relname, pg_index.indisunique "
                        "FROM pg_index "
                        "JOIN pg_class AS table_class ON table_class.oid = indrelid "
                        "JOIN pg_class AS index_class ON index_class.oid = indexrelid "
                        "JOIN pg_namespace ON pg_namespace.oid = table_class.relnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND table_class.relname IN "
                        "('buddy_conversations', 'buddy_messages')"
                    )
                )
            )
        }
        assert indexes["uq_buddy_conversations_match_id"] is True
        assert indexes["ix_buddy_messages_conversation_created_at_id"] is False
        assert indexes["ix_buddy_messages_expires_at"] is False
        assert indexes["ix_buddy_messages_sender_id"] is False

        trigger = (
            await connection.execute(
                text(
                    "SELECT pg_trigger.tgname, pg_proc.prosecdef, pg_proc.proconfig "
                    "FROM pg_trigger "
                    "JOIN pg_proc ON pg_proc.oid = pg_trigger.tgfoid "
                    "JOIN pg_class ON pg_class.oid = pg_trigger.tgrelid "
                    "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                    "WHERE NOT pg_trigger.tgisinternal "
                    "AND pg_namespace.nspname = 'app_private' "
                    "AND pg_class.relname = 'buddy_messages'"
                )
            )
        ).one()
        assert trigger.tgname == "trg_buddy_messages_sender_active_participant"
        assert trigger.prosecdef is False
        assert trigger.proconfig == ['search_path=""']


async def _assert_upgrade_concurrency_and_isolation(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        user_ids, match_ids = await _seed_contract_rows(engine)
        await _assert_schema_security_and_indexes(engine)

        first, second = await asyncio.wait_for(
            asyncio.gather(
                _conversation(factory, match_ids[0]),
                _conversation(factory, match_ids[0]),
            ),
            timeout=10,
        )
        assert first.id == second.id
        # Participant direction cannot create another conversation because the
        # canonical Match row, not an ordered pair supplied by a caller, is the key.
        reciprocal_retry = await _conversation(factory, match_ids[0])
        assert reciprocal_retry.id == first.id

        other_conversation = await _conversation(factory, match_ids[1])
        assert other_conversation.id != first.id
        async with factory() as session:
            conversations = tuple(
                (
                    await session.scalars(
                        select(BuddyConversation).order_by(BuddyConversation.match_id)
                    )
                ).all()
            )
            assert len(conversations) == 2
            assert {item.match_id for item in conversations} == set(match_ids)

        first_message, second_message = await asyncio.wait_for(
            asyncio.gather(
                _message(
                    factory,
                    conversation_id=first.id,
                    sender_id=user_ids[0],
                    body="message from A",
                ),
                _message(
                    factory,
                    conversation_id=first.id,
                    sender_id=user_ids[1],
                    body="message from B",
                ),
            ),
            timeout=10,
        )
        assert first_message.created_at == second_message.created_at == NOW
        assert first_message.expires_at == second_message.expires_at == NOW + timedelta(days=90)

        other_message = await _message(
            factory,
            conversation_id=other_conversation.id,
            sender_id=user_ids[2],
            body="separate A-C stream",
        )
        async with factory() as session:
            ordered = tuple(
                (
                    await session.scalars(
                        select(BuddyMessage)
                        .where(BuddyMessage.conversation_id == first.id)
                        .order_by(BuddyMessage.created_at, BuddyMessage.id)
                    )
                ).all()
            )
            assert [message.id for message in ordered] == sorted(
                (first_message.id, second_message.id)
            )
            assert {message.body for message in ordered} == {
                "message from A",
                "message from B",
            }
            assert all(message.conversation_id == first.id for message in ordered)
            other_stream = tuple(
                (
                    await session.scalars(
                        select(BuddyMessage).where(
                            BuddyMessage.conversation_id == other_conversation.id
                        )
                    )
                ).all()
            )
            assert [message.id for message in other_stream] == [other_message.id]

        async with factory() as session:
            with pytest.raises(BuddyMessagePersistenceError) as raised:
                await persist_buddy_message(
                    session,
                    conversation_id=first.id,
                    authenticated_sender_id=user_ids[3],
                    body="must stay private",
                    clock=lambda: NOW,
                )
            assert raised.value.reason is BuddyMessagePersistenceReason.SENDER_NOT_PARTICIPANT

        message_insert = (
            "INSERT INTO app_private.buddy_messages "
            "(conversation_id, sender_id, client_message_id, body, created_at, expires_at) "
            "VALUES (:conversation_id, :sender_id, :client_message_id, :body, "
            ":created_at, :expires_at)"
        )
        await _expect_integrity_error(
            engine,
            message_insert,
            {
                "conversation_id": first.id,
                "sender_id": user_ids[3],
                "client_message_id": uuid4(),
                "body": "direct outsider write",
                "created_at": NOW,
                "expires_at": NOW + timedelta(days=90),
            },
        )
        await _expect_integrity_error(
            engine,
            message_insert,
            {
                "conversation_id": uuid4(),
                "sender_id": user_ids[0],
                "client_message_id": uuid4(),
                "body": "unknown conversation",
                "created_at": NOW,
                "expires_at": NOW + timedelta(days=90),
            },
        )
        await _expect_integrity_error(
            engine,
            message_insert,
            {
                "conversation_id": first.id,
                "sender_id": user_ids[0],
                "client_message_id": uuid4(),
                "body": "\t\n",
                "created_at": NOW,
                "expires_at": NOW + timedelta(days=90),
            },
        )
        await _expect_integrity_error(
            engine,
            message_insert,
            {
                "conversation_id": first.id,
                "sender_id": user_ids[0],
                "client_message_id": uuid4(),
                "body": "x" * 10_001,
                "created_at": NOW,
                "expires_at": NOW + timedelta(days=90),
            },
        )
        await _expect_integrity_error(
            engine,
            message_insert,
            {
                "conversation_id": first.id,
                "sender_id": user_ids[0],
                "client_message_id": uuid4(),
                "body": "wrong retention",
                "created_at": NOW,
                "expires_at": NOW + timedelta(days=89),
            },
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.buddy_conversations (match_id) VALUES (:match_id)",
            {"match_id": match_ids[0]},
        )
        await _expect_integrity_error(
            engine,
            "INSERT INTO app_private.buddy_conversations (match_id) VALUES (:match_id)",
            {"match_id": uuid4()},
        )

        runtime_message_id = uuid4()
        async with engine.begin() as connection:
            await connection.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            await connection.execute(
                text(
                    "INSERT INTO app_private.buddy_messages "
                    "(id, conversation_id, sender_id, client_message_id, body, "
                    "created_at, expires_at) "
                    "VALUES (:id, :conversation_id, :sender_id, :client_message_id, :body, "
                    ":created_at, :expires_at)"
                ),
                {
                    "id": runtime_message_id,
                    "conversation_id": other_conversation.id,
                    "sender_id": user_ids[0],
                    "client_message_id": runtime_message_id,
                    "body": "runtime trigger path",
                    "created_at": NOW,
                    "expires_at": NOW + timedelta(days=90),
                },
            )
        async with engine.connect() as connection:
            transaction = await connection.begin()
            await connection.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            with pytest.raises(DBAPIError):
                await connection.execute(
                    text("UPDATE app_private.buddy_messages SET body = 'forbidden' WHERE id = :id"),
                    {"id": runtime_message_id},
                )
            await transaction.rollback()

        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM app_private.matches WHERE id = :match_id"),
                {"match_id": match_ids[0]},
            )
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.buddy_conversations "
                        "WHERE match_id = :match_id"
                    ),
                    {"match_id": match_ids[0]},
                )
                == 0
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.buddy_messages "
                        "WHERE conversation_id = :conversation_id"
                    ),
                    {"conversation_id": first.id},
                )
                == 0
            )
            assert await connection.scalar(text("SELECT count(*) FROM app_private.matches")) == 1
    finally:
        await engine.dispose()


async def _assert_downgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            conversation_table, message_table, match_table, guard_function = (
                await connection.execute(
                    text(
                        "SELECT to_regclass('app_private.buddy_conversations'), "
                        "to_regclass('app_private.buddy_messages'), "
                        "to_regclass('app_private.matches'), "
                        "to_regprocedure('app_private.enforce_buddy_message_sender()')"
                    )
                )
            ).one()
            assert conversation_table is None
            assert message_table is None
            assert guard_function is None
            assert match_table == "app_private.matches"
            assert await connection.scalar(text("SELECT count(*) FROM app_private.matches")) == 1
    finally:
        await engine.dispose()


async def _assert_reupgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT to_regclass('app_private.buddy_conversations')")
                )
                == "app_private.buddy_conversations"
            )
            assert (
                await connection.scalar(text("SELECT to_regclass('app_private.buddy_messages')"))
                == "app_private.buddy_messages"
            )
            assert await connection.scalar(select(func.count()).select_from(BuddyConversation)) == 0
            assert await connection.scalar(select(func.count()).select_from(BuddyMessage)) == 0
            assert await connection.scalar(text("SELECT count(*) FROM app_private.matches")) == 1
    finally:
        await engine.dispose()


def test_live_chat_upgrade_races_constraints_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("CHAT001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CHAT001_TEST_DATABASE_URL for disposable CHAT-001 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "chat001_acceptance"
        or parsed_url.username != "chat001_runner"
    ):
        pytest.fail(
            "CHAT-001 requires the disposable chat001_runner role in the isolated "
            "loopback chat001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "0013_active_match_persistence")
        command.upgrade(config, "head")
        asyncio.run(_assert_upgrade_concurrency_and_isolation(async_database_url))
        command.check(config)
        command.downgrade(config, "0013_active_match_persistence")
        asyncio.run(_assert_downgraded(async_database_url))
        command.upgrade(config, "head")
        asyncio.run(_assert_reupgraded(async_database_url))
    finally:
        command.downgrade(config, "0013_active_match_persistence")
        get_migration_database_settings.cache_clear()
