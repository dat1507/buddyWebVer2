"""Opt-in CHAT-002 migration, concurrency, retention, and isolation acceptance.

Set CHAT002_TEST_DATABASE_URL to the disposable ``chat002_runner`` role in a
loopback-only database named ``chat002_acceptance``. The test returns that
database to revision 0014 and must never target development or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select, text
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
from app.models import BuddyMessage, StudentType
from app.services.buddy_chat import (
    BuddyChatReadError,
    BuddyChatReadReason,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    acknowledge_buddy_messages_read,
    list_buddy_messages,
    send_buddy_message,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
AB_CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000001")
AC_CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000002")
LEGACY_MESSAGE_ID = UUID("20000000-0000-4000-8000-000000000001")


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_at_chat001(engine: AsyncEngine) -> tuple[list[UUID], UUID]:
    user_ids = [uuid4() for _ in range(4)]
    profile_ids = [uuid4() for _ in range(4)]
    invitation_ids = [uuid4() for _ in range(2)]
    match_ids = [uuid4() for _ in range(2)]
    pairs = ((user_ids[0], user_ids[1]), (user_ids[0], user_ids[2]))
    old_created_at = NOW - timedelta(days=80)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, email_verified, email_verified_at) "
                "VALUES (:id, :email, 'test-only-hash', true, :verified_at)"
            ),
            [
                {
                    "id": user_id,
                    "email": f"chat002-{index}@example.invalid",
                    "verified_at": NOW,
                }
                for index, user_id in enumerate(user_ids)
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
                    "student_type": (
                        StudentType.VIETNAMESE.value
                        if index == 0
                        else StudentType.INTERNATIONAL.value
                    ),
                }
                for index, user_id in enumerate(user_ids)
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, 'accepted', 'ACCEPTED', :created_at, "
                ":updated_at, :expires_at, :responded_at)"
            ),
            [
                {
                    "id": invitation_ids[index],
                    "sender_id": pair[0],
                    "recipient_id": pair[1],
                    "created_at": NOW - timedelta(hours=1),
                    "updated_at": NOW,
                    "expires_at": NOW - timedelta(hours=1) + timedelta(days=7),
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
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_conversations (id, match_id, created_at) "
                "VALUES (:ab_id, :ab_match, :created_at), (:ac_id, :ac_match, :created_at)"
            ),
            {
                "ab_id": AB_CONVERSATION_ID,
                "ab_match": match_ids[0],
                "ac_id": AC_CONVERSATION_ID,
                "ac_match": match_ids[1],
                "created_at": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_messages "
                "(id, conversation_id, sender_id, body, created_at, expires_at) "
                "VALUES (:id, :conversation_id, :sender_id, 'legacy-near-cap', "
                ":created_at, :expires_at)"
            ),
            {
                "id": LEGACY_MESSAGE_ID,
                "conversation_id": AB_CONVERSATION_ID,
                "sender_id": user_ids[1],
                "created_at": old_created_at,
                "expires_at": old_created_at + timedelta(days=90),
            },
        )
    return user_ids, match_ids[0]


async def _send_and_commit(
    factory: async_sessionmaker[AsyncSession],
    *,
    conversation_id: UUID,
    sender_id: UUID,
    client_message_id: UUID,
    body: str,
    created_at: datetime,
) -> BuddyMessage:
    async with factory() as session:
        message = await send_buddy_message(
            session,
            conversation_id=conversation_id,
            authenticated_sender_id=sender_id,
            client_message_id=client_message_id,
            body=body,
            clock=lambda: created_at,
        )
        await session.commit()
        return message


async def _ack_and_commit(
    factory: async_sessionmaker[AsyncSession],
    *,
    reader_id: UUID,
    through_message_id: UUID,
    read_at: datetime,
) -> int:
    async with factory() as session:
        result = await acknowledge_buddy_messages_read(
            session,
            conversation_id=AB_CONVERSATION_ID,
            authenticated_reader_id=reader_id,
            through_message_id=through_message_id,
            clock=lambda: read_at,
        )
        await session.commit()
        return result.marked_read_count


async def _assert_chat002_acceptance(
    engine: AsyncEngine,
    user_ids: list[UUID],
) -> None:
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    sender_id, buddy_id, other_buddy_id, outsider_id = user_ids

    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT client_message_id = id FROM app_private.buddy_messages WHERE id = :id"
                ),
                {"id": LEGACY_MESSAGE_ID},
            )
            is True
        )
        unique_columns = tuple(
            (
                await connection.execute(
                    text(
                        "SELECT attribute.attname "
                        "FROM pg_constraint "
                        "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
                        "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                        "JOIN unnest(pg_constraint.conkey) WITH ORDINALITY AS key(attnum, ord) "
                        "ON true "
                        "JOIN pg_attribute AS attribute ON attribute.attrelid = pg_class.oid "
                        "AND attribute.attnum = key.attnum "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND pg_constraint.conname = "
                        "'uq_buddy_messages_sender_id_client_message_id' "
                        "ORDER BY key.ord"
                    )
                )
            ).scalars()
        )
        assert unique_columns == ("sender_id", "client_message_id")
        assert await connection.scalar(
            text(
                "SELECT has_column_privilege('vgu_buddy_runtime', "
                "'app_private.buddy_messages', 'client_message_id', 'INSERT')"
            )
        )

    retry_key = uuid4()
    first, replay = await asyncio.wait_for(
        asyncio.gather(
            _send_and_commit(
                factory,
                conversation_id=AB_CONVERSATION_ID,
                sender_id=sender_id,
                client_message_id=retry_key,
                body="concurrent retry",
                created_at=NOW - timedelta(minutes=5),
            ),
            _send_and_commit(
                factory,
                conversation_id=AB_CONVERSATION_ID,
                sender_id=sender_id,
                client_message_id=retry_key,
                body="concurrent retry",
                created_at=NOW - timedelta(minutes=5),
            ),
        ),
        timeout=10,
    )
    assert first.id == replay.id
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM app_private.buddy_messages "
                    "WHERE sender_id = :sender_id AND client_message_id = :client_message_id"
                ),
                {"sender_id": sender_id, "client_message_id": retry_key},
            )
            == 1
        )

    for conversation_id, body in (
        (AB_CONVERSATION_ID, "changed body"),
        (AC_CONVERSATION_ID, "concurrent retry"),
    ):
        async with factory() as session:
            with pytest.raises(BuddyMessagePersistenceError) as idempotency_error:
                await send_buddy_message(
                    session,
                    conversation_id=conversation_id,
                    authenticated_sender_id=sender_id,
                    client_message_id=retry_key,
                    body=body,
                    clock=lambda: NOW,
                )
            assert (
                idempotency_error.value.reason
                is BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED
            )

    async with factory() as session:
        with pytest.raises(BuddyMessagePersistenceError):
            await send_buddy_message(
                session,
                conversation_id=AB_CONVERSATION_ID,
                authenticated_sender_id=outsider_id,
                client_message_id=uuid4(),
                body="outsider",
                clock=lambda: NOW,
            )

    same_time_messages = await asyncio.wait_for(
        asyncio.gather(
            *(
                _send_and_commit(
                    factory,
                    conversation_id=AB_CONVERSATION_ID,
                    sender_id=sender_id,
                    client_message_id=uuid4(),
                    body=f"same-time-{index}",
                    created_at=NOW - timedelta(minutes=4),
                )
                for index in range(3)
            )
        ),
        timeout=10,
    )
    cross_conversation = await _send_and_commit(
        factory,
        conversation_id=AC_CONVERSATION_ID,
        sender_id=other_buddy_id,
        client_message_id=uuid4(),
        body="must-not-leak-from-ac",
        created_at=NOW - timedelta(minutes=3),
    )
    assert cross_conversation.conversation_id == AC_CONVERSATION_ID

    recent_incoming = await _send_and_commit(
        factory,
        conversation_id=AB_CONVERSATION_ID,
        sender_id=buddy_id,
        client_message_id=uuid4(),
        body="incoming-before-boundary",
        created_at=NOW - timedelta(minutes=2),
    )
    own_boundary = await _send_and_commit(
        factory,
        conversation_id=AB_CONVERSATION_ID,
        sender_id=sender_id,
        client_message_id=uuid4(),
        body="own-boundary",
        created_at=NOW - timedelta(minutes=1),
    )
    newer_incoming = await _send_and_commit(
        factory,
        conversation_id=AB_CONVERSATION_ID,
        sender_id=buddy_id,
        client_message_id=uuid4(),
        body="incoming-after-boundary",
        created_at=NOW,
    )
    expired_created_at = NOW - timedelta(days=91)
    async with factory() as session:
        expired = await send_buddy_message(
            session,
            conversation_id=AB_CONVERSATION_ID,
            authenticated_sender_id=buddy_id,
            client_message_id=uuid4(),
            body="expired-effective-filter",
            clock=lambda: expired_created_at,
        )
        await session.commit()

    async with factory() as session:
        page = await list_buddy_messages(
            session,
            conversation_id=AB_CONVERSATION_ID,
            authenticated_user_id=sender_id,
            page_size=100,
            clock=lambda: NOW,
        )
        ordering = [(item.created_at, item.id) for item in page.items]
        assert ordering == sorted(ordering)
        same_time_ids = [
            item.id for item in page.items if item.created_at == NOW - timedelta(minutes=4)
        ]
        assert same_time_ids == sorted(message.id for message in same_time_messages)
        assert cross_conversation.id not in {item.id for item in page.items}
        assert expired.id not in {item.id for item in page.items}
        with pytest.raises(BuddyChatReadError) as read_error:
            await list_buddy_messages(
                session,
                conversation_id=AB_CONVERSATION_ID,
                authenticated_user_id=outsider_id,
                clock=lambda: NOW,
            )
        assert read_error.value.reason is BuddyChatReadReason.CONVERSATION_NOT_FOUND

    read_counts = await asyncio.wait_for(
        asyncio.gather(
            _ack_and_commit(
                factory,
                reader_id=sender_id,
                through_message_id=own_boundary.id,
                read_at=NOW,
            ),
            _ack_and_commit(
                factory,
                reader_id=sender_id,
                through_message_id=own_boundary.id,
                read_at=NOW + timedelta(microseconds=1),
            ),
        ),
        timeout=10,
    )
    # Exactly the legacy near-cap row and recent incoming row are first-read once.
    assert sum(read_counts) == 2
    async with factory() as session:
        rows = {
            row.id: row
            for row in (
                (
                    await session.scalars(
                        select(BuddyMessage).where(
                            BuddyMessage.id.in_(
                                (
                                    LEGACY_MESSAGE_ID,
                                    recent_incoming.id,
                                    own_boundary.id,
                                    newer_incoming.id,
                                )
                            )
                        )
                    )
                ).all()
            )
        }
        canonical_read_at = rows[LEGACY_MESSAGE_ID].read_at
        assert canonical_read_at in {NOW, NOW + timedelta(microseconds=1)}
        assert rows[recent_incoming.id].read_at == canonical_read_at
        assert rows[LEGACY_MESSAGE_ID].expires_at == NOW + timedelta(days=10)
        assert rows[recent_incoming.id].expires_at == canonical_read_at + timedelta(days=30)
        assert rows[own_boundary.id].read_at is None
        assert rows[newer_incoming.id].read_at is None

    repeated = await _ack_and_commit(
        factory,
        reader_id=sender_id,
        through_message_id=own_boundary.id,
        read_at=NOW + timedelta(days=1),
    )
    assert repeated == 0
    async with factory() as session:
        legacy_after_repeat = await session.get(BuddyMessage, LEGACY_MESSAGE_ID)
        recent_after_repeat = await session.get(BuddyMessage, recent_incoming.id)
        assert legacy_after_repeat is not None and recent_after_repeat is not None
        assert legacy_after_repeat.read_at == canonical_read_at
        assert legacy_after_repeat.expires_at == NOW + timedelta(days=10)
        assert recent_after_repeat.read_at == canonical_read_at
        assert recent_after_repeat.expires_at == canonical_read_at + timedelta(days=30)


async def _message_count(database_url: str) -> int:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return int(
                await connection.scalar(text("SELECT count(*) FROM app_private.buddy_messages"))
                or 0
            )
    finally:
        await engine.dispose()


async def _current_revision(database_url: str) -> str | None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            version_table = await connection.scalar(text("SELECT to_regclass('alembic_version')"))
            if version_table is None:
                return None
            value = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            return str(value) if value is not None else None
    finally:
        await engine.dispose()


async def _assert_downgraded(database_url: str, expected_count: int) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    item["name"]
                    for item in inspect(sync_connection).get_columns(
                        "buddy_messages", schema="app_private"
                    )
                }
            )
            assert "client_message_id" not in columns
            assert (
                await connection.scalar(text("SELECT count(*) FROM app_private.buddy_messages"))
                == expected_count
            )
    finally:
        await engine.dispose()


async def _assert_reupgraded(database_url: str, expected_count: int) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM app_private.buddy_messages "
                        "WHERE client_message_id IS NULL"
                    )
                )
                == 0
            )
            assert (
                await connection.scalar(text("SELECT count(*) FROM app_private.buddy_messages"))
                == expected_count
            )
    finally:
        await engine.dispose()


def _assert_downgrade_and_reupgrade(
    database_url: str,
    config: Config,
) -> None:
    message_count = asyncio.run(_message_count(database_url))

    command.downgrade(config, "0014_buddy_chat_persistence")
    asyncio.run(_assert_downgraded(database_url, message_count))

    command.upgrade(config, "head")
    command.check(config)
    asyncio.run(_assert_reupgraded(database_url, message_count))


async def _seed_database(database_url: str) -> list[UUID]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        user_ids, _match_id = await _seed_at_chat001(engine)
        return user_ids
    finally:
        await engine.dispose()


async def _run_acceptance(database_url: str, user_ids: list[UUID]) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        await _assert_chat002_acceptance(engine, user_ids)
    finally:
        await engine.dispose()


def test_live_chat002_migration_concurrency_retention_and_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("CHAT002_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CHAT002_TEST_DATABASE_URL for disposable CHAT-002 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "chat002_acceptance"
        or parsed_url.username != "chat002_runner"
    ):
        pytest.fail(
            "CHAT-002 requires chat002_runner in the isolated loopback chat002_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        # The validated target is disposable; reset prior acceptance residue so
        # repeated local/CI runs prove the same migration path deterministically.
        # Keep the cluster-wide runtime role owned by migration 0001: other
        # isolated acceptance databases can legitimately grant it privileges.
        current_revision = asyncio.run(_current_revision(async_database_url))
        if current_revision is None:
            command.upgrade(config, "0001_private_app_schema")
        else:
            command.downgrade(config, "0001_private_app_schema")
        command.upgrade(config, "0014_buddy_chat_persistence")
        user_ids = asyncio.run(_seed_database(async_database_url))
        command.upgrade(config, "head")
        command.check(config)
        asyncio.run(_run_acceptance(async_database_url, user_ids))
        _assert_downgrade_and_reupgrade(async_database_url, config)
    finally:
        if asyncio.run(_current_revision(async_database_url)) == "0015_chat_send_idempotency":
            command.downgrade(config, "0014_buddy_chat_persistence")
        get_migration_database_settings.cache_clear()
