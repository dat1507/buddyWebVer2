"""Actual FastAPI WebSocket coverage for CHAT-003 protocol and failure behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocket, WebSocketException, status
from pydantic import SecretBytes
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.api.chat_realtime as chat_ws
import app.api.dependencies as auth_dependencies
from app.core.config import (
    AuthTokenSettings,
    CorsSettings,
    get_auth_token_settings,
    get_cors_settings,
)
from app.core.database import get_session_factory
from app.main import app
from app.models import BuddyMessage, StudentProfile, StudentType, User, UserRole
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.buddy_chat import (
    BuddyChatReadError,
    BuddyChatReadReason,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
)
from app.services.chat_realtime import (
    ChatPublishDisposition,
    ChatPublishResult,
    ChatRedisNotification,
    get_chat_realtime_transport,
)

TRUSTED_ORIGIN = "https://localhost:5173"
CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000001")
OTHER_CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
USER_A_ID = UUID("20000000-0000-4000-8000-000000000001")
USER_B_ID = UUID("20000000-0000-4000-8000-000000000002")
OUTSIDER_ID = UUID("20000000-0000-4000-8000-000000000003")


def _principal(user_id: UUID) -> VerifiedBuddyPrincipal:
    user = User(
        id=user_id,
        email=f"{user_id}@example.invalid",
        password_hash="test-only",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )
    profile = StudentProfile(
        id=uuid4(),
        user_id=user_id,
        full_name="Realtime Test",
        student_type=(
            StudentType.VIETNAMESE if user_id == USER_A_ID else StudentType.INTERNATIONAL
        ),
    )
    return VerifiedBuddyPrincipal(user=user, profile=profile)


PRINCIPALS = {
    "a": _principal(USER_A_ID),
    "b": _principal(USER_B_ID),
    "outsider": _principal(OUTSIDER_ID),
}


def _cookie_actor(websocket: WebSocket) -> str | None:
    return websocket.cookies.get("chat-test-session")


class _SessionContext:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *_args: object) -> None:
        return None


class _SessionFactory:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def __call__(self) -> _SessionContext:
        mock = MagicMock(spec=AsyncSession)

        async def commit() -> None:
            self.order.append("commit")

        mock.commit = AsyncMock(side_effect=commit)
        mock.rollback = AsyncMock()
        return _SessionContext(cast(AsyncSession, mock))


class _FakeSubscription:
    def __init__(self, owner: _FakeTransport, conversation_id: UUID) -> None:
        self.owner = owner
        self.conversation_id = conversation_id
        self.queue: asyncio.Queue[ChatRedisNotification] = asyncio.Queue(maxsize=8)
        self.closed = False

    async def next_notification(self) -> ChatRedisNotification:
        if self.owner.fail_listener:
            await asyncio.sleep(0)
            raise RedisError("private redis endpoint")
        return await self.queue.get()

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.owner.cleanup_count += 1
        self.owner.subscriptions[self.conversation_id].remove(self)


class _FakeTransport:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.subscriptions: dict[UUID, list[_FakeSubscription]] = {}
        self.published: set[UUID] = set()
        self.cleanup_count = 0
        self.fail_subscribe = False
        self.fail_publish = False
        self.fail_listener = False

    async def subscribe(self, conversation_id: UUID) -> _FakeSubscription:
        if self.fail_subscribe:
            raise RedisError("private redis endpoint")
        subscription = _FakeSubscription(self, conversation_id)
        self.subscriptions.setdefault(conversation_id, []).append(subscription)
        return subscription

    async def publish_committed(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
    ) -> ChatPublishResult:
        self.order.append("publish")
        if self.fail_publish:
            raise RedisError("private redis endpoint")
        if message_id in self.published:
            return ChatPublishResult(ChatPublishDisposition.ALREADY_PUBLISHED, 0)
        self.published.add(message_id)
        subscriptions = tuple(self.subscriptions.get(conversation_id, ()))
        notification = ChatRedisNotification(
            version=1,
            event="message.committed",
            message_id=message_id,
        )
        for subscription in subscriptions:
            subscription.queue.put_nowait(notification)
        return ChatPublishResult(
            ChatPublishDisposition.PUBLISHED
            if subscriptions
            else ChatPublishDisposition.UNAVAILABLE,
            len(subscriptions),
        )


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)


def _cookie(actor: str) -> str:
    return f"chat-test-session={actor}"


@contextmanager
def _installed_route(
    monkeypatch: pytest.MonkeyPatch,
    *,
    transport: _FakeTransport,
    order: list[str],
    messages: dict[UUID, BuddyMessage],
) -> Iterator[None]:
    factory = _SessionFactory(order)

    async def handshake(websocket: WebSocket) -> VerifiedBuddyPrincipal:
        actor = _cookie_actor(websocket)
        if actor not in PRINCIPALS:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        return PRINCIPALS[actor]

    async def reauthenticate(
        websocket: WebSocket,
        _settings: AuthTokenSettings,
        _session: AsyncSession,
    ) -> VerifiedBuddyPrincipal:
        return await handshake(websocket)

    async def authorize(
        _session: AsyncSession,
        *,
        conversation_id: UUID,
        authenticated_user_id: UUID,
    ) -> MagicMock:
        if conversation_id == CONVERSATION_ID and authenticated_user_id in {
            USER_A_ID,
            USER_B_ID,
        }:
            return MagicMock()
        if conversation_id == OTHER_CONVERSATION_ID and authenticated_user_id == USER_B_ID:
            return MagicMock()
        raise BuddyChatReadError(BuddyChatReadReason.CONVERSATION_NOT_FOUND)

    retries: dict[tuple[UUID, UUID], BuddyMessage] = {}

    async def persist(
        _session: AsyncSession,
        *,
        conversation_id: UUID,
        authenticated_sender_id: UUID,
        client_message_id: UUID,
        body: str,
    ) -> BuddyMessage:
        if not body.strip() or len(body) > 10_000:
            raise ValueError
        key = (authenticated_sender_id, client_message_id)
        existing = retries.get(key)
        if existing is not None:
            if existing.conversation_id != conversation_id or existing.body != body:
                raise BuddyMessagePersistenceError(
                    BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED
                )
            return existing
        order.append("persist")
        message = BuddyMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            sender_id=authenticated_sender_id,
            client_message_id=client_message_id,
            body=body,
            created_at=NOW,
            expires_at=NOW + timedelta(days=90),
        )
        messages[message.id] = message
        retries[key] = message
        return message

    async def load(
        _session: AsyncSession,
        *,
        conversation_id: UUID,
        authenticated_user_id: UUID,
        message_id: UUID,
    ) -> BuddyMessage | None:
        await authorize(
            _session,
            conversation_id=conversation_id,
            authenticated_user_id=authenticated_user_id,
        )
        message = messages.get(message_id)
        if message is None or message.conversation_id != conversation_id:
            return None
        return message

    async def no_rate_limit(*_args: object) -> None:
        return None

    app.dependency_overrides[get_session_factory] = lambda: cast(
        async_sessionmaker[AsyncSession], factory
    )
    app.dependency_overrides[get_auth_token_settings] = _auth_settings
    app.dependency_overrides[get_cors_settings] = lambda: CorsSettings(
        allowed_origins=(TRUSTED_ORIGIN,)
    )
    app.dependency_overrides[get_chat_realtime_transport] = lambda: transport
    monkeypatch.setattr(
        auth_dependencies,
        "authenticate_verified_buddy_websocket",
        reauthenticate,
    )
    monkeypatch.setattr(chat_ws, "authenticate_verified_buddy_websocket", reauthenticate)
    monkeypatch.setattr(chat_ws, "authorize_buddy_conversation", authorize)
    monkeypatch.setattr(chat_ws, "send_buddy_message", persist)
    monkeypatch.setattr(chat_ws, "get_realtime_buddy_message", load)
    monkeypatch.setattr(chat_ws, "check_websocket_connection_rate_limit", no_rate_limit)
    monkeypatch.setattr(chat_ws, "check_websocket_send_rate_limit", no_rate_limit)
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def _receive_types(socket: object, count: int) -> dict[str, dict[str, object]]:
    received: dict[str, dict[str, object]] = {}
    for _ in range(count):
        event = socket.receive_json()  # type: ignore[attr-defined]
        received[cast(str, event["type"])] = cast(dict[str, object], event)
    return received


def test_websocket_two_participant_fanout_is_safe_idempotent_and_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)
    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            headers_a = {"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")}
            headers_b = {"origin": TRUSTED_ORIGIN, "cookie": _cookie("b")}
            with client.websocket_connect(
                f"/api/ws/chat/{CONVERSATION_ID}", headers=headers_a
            ) as socket_a:
                assert socket_a.receive_json() == {
                    "type": "chat.ready",
                    "recovery": "history",
                }
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}", headers=headers_b
                ) as socket_b:
                    assert socket_b.receive_json()["type"] == "chat.ready"
                    retry_key = uuid4()
                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(retry_key),
                            "body": "plain <b>Buddy</b> 😀",
                        }
                    )
                    sender_events = _receive_types(socket_a, 2)
                    buddy_event = socket_b.receive_json()

                    assert order.index("persist") < order.index("commit") < order.index("publish")
                    assert sender_events["chat.message.created"]["message"]["sender"] == "self"  # type: ignore[index]
                    assert buddy_event["message"]["sender"] == "buddy"
                    assert buddy_event["message"]["body"] == "plain <b>Buddy</b> 😀"
                    assert "sender_id" not in str(buddy_event)
                    assert "client_message_id" not in str(buddy_event)
                    assert "expires_at" not in str(buddy_event)
                    message_id = sender_events["chat.message.accepted"]["message_id"]
                    assert (
                        sender_events["chat.message.accepted"]["realtime_delivery"] == "published"
                    )

                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(retry_key),
                            "body": "plain <b>Buddy</b> 😀",
                        }
                    )
                    retry_ack = socket_a.receive_json()
                    assert retry_ack == {
                        "type": "chat.message.accepted",
                        "message_id": message_id,
                        "realtime_delivery": "already_published",
                        "recovery": "history",
                    }
                    assert len(messages) == 1

                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(retry_key),
                            "body": "changed",
                        }
                    )
                    assert socket_a.receive_json() == {
                        "type": "chat.error",
                        "code": "CHAT_IDEMPOTENCY_KEY_REUSED",
                        "recoverable": False,
                    }

                    socket_a.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(uuid4()),
                            "body": "spoof",
                            "conversation_id": str(OTHER_CONVERSATION_ID),
                            "sender_id": str(USER_B_ID),
                        }
                    )
                    assert socket_a.receive_json() == {
                        "type": "chat.error",
                        "code": "CHAT_EVENT_INVALID",
                        "recoverable": True,
                    }
                    assert len(messages) == 1
                    assert OTHER_CONVERSATION_ID not in transport.subscriptions
    assert transport.cleanup_count == 2


@pytest.mark.parametrize("failure", ["connect", "publish"])
def test_redis_outage_fails_closed_and_never_rolls_back_committed_message(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)
    transport.fail_subscribe = failure == "connect"
    transport.fail_publish = failure == "publish"

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            headers = {"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")}
            if failure == "connect":
                with pytest.raises(WebSocketDisconnect) as denied:
                    with client.websocket_connect(
                        f"/api/ws/chat/{CONVERSATION_ID}", headers=headers
                    ):
                        pass
                assert denied.value.code == status.WS_1013_TRY_AGAIN_LATER
                assert not messages
                return

            with pytest.raises(WebSocketDisconnect) as disconnected:
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}", headers=headers
                ) as socket:
                    assert socket.receive_json()["type"] == "chat.ready"
                    socket.send_json(
                        {
                            "type": "message.send",
                            "client_message_id": str(uuid4()),
                            "body": "persist despite redis outage",
                        }
                    )
                    accepted = socket.receive_json()
                    assert accepted["realtime_delivery"] == "unavailable"
                    socket.receive_json()
            assert disconnected.value.code == status.WS_1013_TRY_AGAIN_LATER
            assert len(messages) == 1
            assert order.index("commit") < order.index("publish")


def test_active_redis_disconnect_closes_and_cleans_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)
    transport.fail_listener = True

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as disconnected:
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}",
                    headers={"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")},
                ) as socket:
                    assert socket.receive_json()["type"] == "chat.ready"
                    socket.receive_json()
            assert disconnected.value.code == status.WS_1013_TRY_AGAIN_LATER

    assert transport.cleanup_count == 1
    assert transport.subscriptions[CONVERSATION_ID] == []


def test_repeated_connect_disconnect_releases_every_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            for _ in range(3):
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}",
                    headers={"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")},
                ) as socket:
                    assert socket.receive_json()["type"] == "chat.ready"
                    socket.close()

    assert transport.cleanup_count == 3
    assert transport.subscriptions[CONVERSATION_ID] == []


def test_origin_auth_participant_and_malformed_locator_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            cases = [
                (
                    f"/api/ws/chat/{CONVERSATION_ID}",
                    {"origin": "https://evil.example", "cookie": _cookie("a")},
                    status.WS_1008_POLICY_VIOLATION,
                ),
                (
                    f"/api/ws/chat/{CONVERSATION_ID}?access_token=must-not-authenticate",
                    {"origin": TRUSTED_ORIGIN},
                    status.WS_1008_POLICY_VIOLATION,
                ),
                (
                    f"/api/ws/chat/{CONVERSATION_ID}",
                    {"origin": TRUSTED_ORIGIN, "cookie": _cookie("outsider")},
                    status.WS_1008_POLICY_VIOLATION,
                ),
                (
                    "/api/ws/chat/not-a-uuid",
                    {"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")},
                    status.WS_1008_POLICY_VIOLATION,
                ),
            ]
            for path, headers, expected_code in cases:
                with pytest.raises(WebSocketDisconnect) as denied:
                    with client.websocket_connect(path, headers=headers):
                        pass
                assert denied.value.code == expected_code


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ("{not-json", "CHAT_EVENT_INVALID"),
        ('{"type":"unsupported"}', "CHAT_EVENT_INVALID"),
        ('{"type":"message.send","body":"missing id"}', "CHAT_EVENT_INVALID"),
        (
            '{"type":"message.send","client_message_id":"not-a-uuid","body":"valid"}',
            "CHAT_EVENT_INVALID",
        ),
        (
            '{"type":"message.send","client_message_id":'
            '"40000000-0000-4000-8000-000000000001","body":"   "}',
            "CHAT_MESSAGE_INVALID",
        ),
    ],
)
def test_malformed_events_return_stable_sanitized_errors(
    payload: str,
    expected_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/ws/chat/{CONVERSATION_ID}",
                headers={"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")},
            ) as socket:
                assert socket.receive_json()["type"] == "chat.ready"
                socket.send_text(payload)
                error = socket.receive_json()
                assert error == {
                    "type": "chat.error",
                    "code": expected_code,
                    "recoverable": True,
                }
                assert payload not in str(error)
                assert not messages
                socket.close()


def test_oversized_or_binary_event_closes_without_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    messages: dict[UUID, BuddyMessage] = {}
    transport = _FakeTransport(order)

    with _installed_route(
        monkeypatch,
        transport=transport,
        order=order,
        messages=messages,
    ):
        with TestClient(app) as client:
            headers = {"origin": TRUSTED_ORIGIN, "cookie": _cookie("a")}
            with pytest.raises(WebSocketDisconnect) as oversized:
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}", headers=headers
                ) as socket:
                    socket.receive_json()
                    socket.send_text("x" * 131_073)
                    socket.receive_json()
            assert oversized.value.code == status.WS_1009_MESSAGE_TOO_BIG

            with pytest.raises(WebSocketDisconnect) as binary:
                with client.websocket_connect(
                    f"/api/ws/chat/{CONVERSATION_ID}", headers=headers
                ) as socket:
                    socket.receive_json()
                    socket.send_bytes(b"not-supported")
                    socket.receive_json()
            assert binary.value.code == status.WS_1003_UNSUPPORTED_DATA
            assert not messages
