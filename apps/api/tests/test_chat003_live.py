"""Opt-in real Redis and PostgreSQL/WebSocket acceptance for CHAT-003."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretBytes
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from starlette.websockets import WebSocketDisconnect

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    AuthTokenSettings,
    CorsSettings,
    get_auth_token_settings,
    get_cors_settings,
    get_migration_database_settings,
)
from app.core.database import get_database_session, get_session_factory
from app.main import app
from app.models import BuddyMessage, UserRole
from app.services.chat_realtime import (
    ChatPublishDisposition,
    ChatRealtimeTransport,
    ChatRedisSubscription,
    get_chat_realtime_transport,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRUSTED_ORIGIN = "https://localhost:5173"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000031")
USER_A_ID = UUID("20000000-0000-4000-8000-000000000031")
USER_B_ID = UUID("20000000-0000-4000-8000-000000000032")
OUTSIDER_ID = UUID("20000000-0000-4000-8000-000000000033")
UNVERIFIED_ID = UUID("20000000-0000-4000-8000-000000000034")
PROFILE_IDS = tuple(UUID(f"30000000-0000-4000-8000-{index:012d}") for index in range(31, 35))
INVITATION_ID = UUID("40000000-0000-4000-8000-000000000031")
MATCH_ID = UUID("50000000-0000-4000-8000-000000000031")


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)


async def _close_redis(client: Redis) -> None:
    close = cast(Callable[[], Awaitable[None]], client.aclose)
    await close()


async def _clear_prefix(client: Redis, prefix: str) -> None:
    keys = [key async for key in client.scan_iter(match=f"{prefix}:*")]
    if keys:
        await client.delete(*keys)


async def _clear_prefix_at_url(redis_url: str, prefix: str) -> None:
    client = Redis.from_url(redis_url, decode_responses=False)
    try:
        await _clear_prefix(client, prefix)
    finally:
        await _close_redis(client)


def _validated_redis_url() -> str:
    redis_url = os.getenv("CHAT003_TEST_REDIS_URL", "")
    if not redis_url:
        pytest.skip("Set CHAT003_TEST_REDIS_URL for disposable CHAT-003 Redis acceptance.")
    parsed = urlsplit(redis_url)
    if parsed.scheme != "redis" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("CHAT-003 live Redis acceptance requires an explicit loopback redis:// URL.")
    return redis_url


@pytest.mark.anyio
async def test_live_redis_multi_connection_isolation_dedupe_cleanup_and_reconnect() -> None:
    redis_url = _validated_redis_url()
    prefix = f"vgu-buddy:test:chat003:{uuid4().hex}"
    clients = [Redis.from_url(redis_url, decode_responses=False) for _ in range(4)]
    conversation_id = uuid4()
    other_conversation_id = uuid4()
    subscriptions: list[ChatRedisSubscription] = []
    try:
        for client in clients:
            assert bool(await cast(Awaitable[bool], client.ping()))
        publisher = ChatRealtimeTransport(clients[0], prefix)
        first_worker = ChatRealtimeTransport(clients[1], prefix)
        second_worker = ChatRealtimeTransport(clients[2], prefix)
        isolated_worker = ChatRealtimeTransport(clients[3], prefix)
        first = await first_worker.subscribe(conversation_id)
        second = await second_worker.subscribe(conversation_id)
        isolated = await isolated_worker.subscribe(other_conversation_id)
        subscriptions.extend((first, second, isolated))

        message_id = uuid4()
        published = await publisher.publish_committed(
            conversation_id=conversation_id,
            message_id=message_id,
        )
        first_event, second_event = await asyncio.gather(
            asyncio.wait_for(first.next_notification(), timeout=2),
            asyncio.wait_for(second.next_notification(), timeout=2),
        )
        assert published.disposition is ChatPublishDisposition.PUBLISHED
        assert published.subscriber_count == 2
        assert first_event.message_id == second_event.message_id == message_id
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(isolated.next_notification(), timeout=0.2)

        duplicate = await publisher.publish_committed(
            conversation_id=conversation_id,
            message_id=message_id,
        )
        assert duplicate.disposition is ChatPublishDisposition.ALREADY_PUBLISHED

        await first.close()
        subscriptions.remove(first)
        missed_id = uuid4()
        await publisher.publish_committed(
            conversation_id=conversation_id,
            message_id=missed_id,
        )
        assert (
            await asyncio.wait_for(second.next_notification(), timeout=2)
        ).message_id == missed_id

        reconnected = await first_worker.subscribe(conversation_id)
        subscriptions.append(reconnected)
        current_id = uuid4()
        await publisher.publish_committed(
            conversation_id=conversation_id,
            message_id=current_id,
        )
        assert (
            await asyncio.wait_for(reconnected.next_notification(), timeout=2)
        ).message_id == current_id
        assert (
            await asyncio.wait_for(second.next_notification(), timeout=2)
        ).message_id == current_id
    finally:
        for subscription in subscriptions:
            await subscription.close()
        await _clear_prefix(clients[0], prefix)
        for client in clients:
            await _close_redis(client)


async def _seed_chat003(engine: AsyncEngine) -> None:
    user_ids = (USER_A_ID, USER_B_ID, OUTSIDER_ID, UNVERIFIED_ID)
    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM app_private.users WHERE email LIKE 'chat003-live-%'"),
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, email_verified, email_verified_at) "
                "VALUES (:id, :email, 'test-only-hash', :verified, :verified_at)"
            ),
            [
                {
                    "id": user_id,
                    "email": f"chat003-live-{index}@example.invalid",
                    "verified": index != 3,
                    "verified_at": NOW if index != 3 else None,
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
                    "id": PROFILE_IDS[index],
                    "user_id": user_id,
                    "full_name": f"Chat003 participant {index}",
                    "student_type": "VIETNAMESE" if index in {0, 2, 3} else "INTERNATIONAL",
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
            {
                "id": INVITATION_ID,
                "sender_id": USER_A_ID,
                "recipient_id": USER_B_ID,
                "created_at": NOW - timedelta(hours=1),
                "updated_at": NOW,
                "expires_at": NOW - timedelta(hours=1) + timedelta(days=7),
                "responded_at": NOW,
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
                "id": MATCH_ID,
                "first_user_id": USER_A_ID,
                "second_user_id": USER_B_ID,
                "first_profile_id": PROFILE_IDS[0],
                "second_profile_id": PROFILE_IDS[1],
                "invitation_id": INVITATION_ID,
                "activated_at": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_conversations (id, match_id, created_at) "
                "VALUES (:id, :match_id, :created_at)"
            ),
            {"id": CONVERSATION_ID, "match_id": MATCH_ID, "created_at": NOW},
        )


async def _message_count(engine: AsyncEngine, client_message_id: UUID) -> int:
    async with async_sessionmaker(engine)() as session:
        return int(
            await session.scalar(
                select(func.count(BuddyMessage.id)).where(
                    BuddyMessage.sender_id == USER_A_ID,
                    BuddyMessage.client_message_id == client_message_id,
                )
            )
            or 0
        )


def _cookie_header(user_id: UUID, settings: AuthTokenSettings) -> str:
    pair = create_token_pair(user_id, UserRole.USER, settings)
    return f"{DEVELOPMENT_ACCESS_COOKIE_NAME}={pair.access_token}"


def test_live_authenticated_websocket_persists_then_cross_connection_fans_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("CHAT003_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CHAT003_TEST_DATABASE_URL for disposable CHAT-003 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "chat003_acceptance"
        or parsed_url.username != "chat003_runner"
    ):
        pytest.fail(
            "CHAT-003 requires chat003_runner in the isolated loopback chat003_acceptance database."
        )
    redis_url = _validated_redis_url()

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    command.upgrade(_migration_config(), "head")
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    engine = create_async_engine(async_database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    asyncio.run(_seed_chat003(engine))

    prefix = f"vgu-buddy:test:chat003:{uuid4().hex}"
    settings = _auth_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    async def realtime_transport() -> AsyncIterator[ChatRealtimeTransport]:
        redis_client = Redis.from_url(redis_url, decode_responses=False)
        try:
            yield ChatRealtimeTransport(redis_client, prefix)
        finally:
            await _close_redis(redis_client)

    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    app.dependency_overrides[get_cors_settings] = lambda: CorsSettings(
        allowed_origins=(TRUSTED_ORIGIN,)
    )
    app.dependency_overrides[get_chat_realtime_transport] = realtime_transport
    client_message_id = uuid4()
    try:
        with TestClient(app) as client:
            headers_a = {
                "origin": TRUSTED_ORIGIN,
                "cookie": _cookie_header(USER_A_ID, settings),
            }
            headers_b = {
                "origin": TRUSTED_ORIGIN,
                "cookie": _cookie_header(USER_B_ID, settings),
            }
            with client.websocket_connect(
                f"/api/ws/chat/{CONVERSATION_ID}", headers=headers_a
            ) as socket_a:
                assert socket_a.receive_json()["type"] == "chat.ready"
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}", headers=headers_b
                ) as socket_b:
                    assert socket_b.receive_json()["type"] == "chat.ready"
                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(client_message_id),
                            "body": "real postgres then redis",
                        }
                    )
                    sender_events = {socket_a.receive_json()["type"] for _ in range(2)}
                    buddy_event = socket_b.receive_json()
                    assert sender_events == {
                        "chat.message.accepted",
                        "chat.message.created",
                    }
                    assert buddy_event["type"] == "chat.message.created"
                    assert buddy_event["message"]["sender"] == "buddy"
                    assert buddy_event["message"]["body"] == "real postgres then redis"
                    assert asyncio.run(_message_count(engine, client_message_id)) == 1

                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(client_message_id),
                            "body": "real postgres then redis",
                        }
                    )
                    assert socket_a.receive_json()["realtime_delivery"] == "already_published"
                    assert asyncio.run(_message_count(engine, client_message_id)) == 1

            history = client.get(
                f"/api/chat/conversations/{CONVERSATION_ID}/messages",
                headers={"cookie": _cookie_header(USER_B_ID, settings)},
            )
            assert history.status_code == 200
            assert any(
                item["body"] == "real postgres then redis" for item in history.json()["items"]
            )

            for denied_user in (OUTSIDER_ID, UNVERIFIED_ID):
                with pytest.raises(WebSocketDisconnect) as denied:
                    with client.websocket_connect(
                        f"/api/ws/chat/{CONVERSATION_ID}",
                        headers={
                            "origin": TRUSTED_ORIGIN,
                            "cookie": _cookie_header(denied_user, settings),
                        },
                    ):
                        pass
                assert denied.value.code == 1008
    finally:
        app.dependency_overrides.clear()
        asyncio.run(_clear_prefix_at_url(redis_url, prefix))
        asyncio.run(engine.dispose())
        get_migration_database_settings.cache_clear()
