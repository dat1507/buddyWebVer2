"""Ephemeral Redis Pub/Sub fan-out for committed Buddy message identifiers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from app.core.config import get_redis_settings
from app.core.redis import get_redis_client

_NOTIFICATION_VERSION: Final = 1
_PUBLISH_DEDUPE_SECONDS: Final = 86_400
_MAX_NOTIFICATION_BYTES: Final = 256
_PUBLISH_ONCE_SCRIPT: Final = """
if redis.call('EXISTS', KEYS[1]) == 1 then
  return -1
end
local receivers = redis.call('PUBLISH', KEYS[2], ARGV[1])
if receivers > 0 then
  redis.call('SET', KEYS[1], '1', 'EX', ARGV[2])
end
return receivers
""".strip()


class ChatRedisNotification(BaseModel):
    """Private minimal event; message content remains in PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    version: int
    event: str
    message_id: UUID


class ChatPublishDisposition(StrEnum):
    """Deterministic result of one publish-or-dedupe operation."""

    PUBLISHED = "published"
    ALREADY_PUBLISHED = "already_published"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ChatPublishResult:
    disposition: ChatPublishDisposition
    subscriber_count: int


def _conversation_channel(prefix: str, conversation_id: UUID) -> str:
    return f"{prefix}:chat:{{{conversation_id.hex}}}:events:v1"


def _published_key(prefix: str, conversation_id: UUID, message_id: UUID) -> str:
    # The shared hash tag keeps EVAL keys in one Redis Cluster slot.
    return f"{prefix}:chat:{{{conversation_id.hex}}}:published:{message_id.hex}:v1"


async def _close_pubsub(pubsub: PubSub) -> None:
    close = cast(Callable[[], Awaitable[None]], pubsub.aclose)
    await close()


class ChatRedisSubscription:
    """One bounded-pull Redis subscription owned by exactly one socket."""

    def __init__(self, pubsub: PubSub, channels: tuple[str, ...]) -> None:
        self._pubsub = pubsub
        self._channels = channels
        self._closed = False

    async def next_notification(self) -> ChatRedisNotification:
        """Wait for the next valid private event without allocating a local queue."""
        while True:
            raw = await self._pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if raw is None or raw.get("type") != "message":
                continue
            channel = raw.get("channel")
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8", errors="ignore")
            if channel not in self._channels:
                continue
            data = raw.get("data")
            if isinstance(data, str):
                encoded = data.encode("utf-8")
            elif isinstance(data, bytes):
                encoded = data
            else:
                continue
            if len(encoded) > _MAX_NOTIFICATION_BYTES:
                continue
            try:
                notification = ChatRedisNotification.model_validate_json(encoded)
            except ValidationError:
                continue
            if (
                notification.version != _NOTIFICATION_VERSION
                or notification.event != "message.committed"
            ):
                continue
            return notification

    async def close(self) -> None:
        """Release only this Pub/Sub connection even during an outage."""
        if self._closed:
            return
        self._closed = True
        with suppress(RedisError):
            await self._pubsub.unsubscribe(*self._channels)
        with suppress(RedisError):
            await _close_pubsub(self._pubsub)


class ChatRealtimeTransport:
    """Server-owned channels over the shared async Redis pool."""

    def __init__(self, redis: Redis, key_prefix: str) -> None:
        self._redis = redis
        self._key_prefix = key_prefix

    async def subscribe(self, conversation_id: UUID) -> ChatRedisSubscription:
        return await self.subscribe_many((conversation_id,))

    async def subscribe_many(
        self,
        conversation_ids: tuple[UUID, ...],
    ) -> ChatRedisSubscription:
        """Subscribe once to a verified USER's bounded ACTIVE conversation set."""
        channels = tuple(
            _conversation_channel(self._key_prefix, conversation_id)
            for conversation_id in dict.fromkeys(conversation_ids)
        )
        if not channels:
            raise ValueError("At least one Buddy conversation is required.")
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        try:
            await pubsub.subscribe(*channels)
        except Exception:
            await _close_pubsub(pubsub)
            raise
        return ChatRedisSubscription(pubsub, channels)

    async def publish_committed(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
    ) -> ChatPublishResult:
        notification = ChatRedisNotification(
            version=_NOTIFICATION_VERSION,
            event="message.committed",
            message_id=message_id,
        ).model_dump_json()
        result = await cast(
            Awaitable[int],
            self._redis.eval(
                _PUBLISH_ONCE_SCRIPT,
                2,
                _published_key(self._key_prefix, conversation_id, message_id),
                _conversation_channel(self._key_prefix, conversation_id),
                notification,
                _PUBLISH_DEDUPE_SECONDS,
            ),
        )
        if result < 0:
            return ChatPublishResult(ChatPublishDisposition.ALREADY_PUBLISHED, 0)
        if result == 0:
            return ChatPublishResult(ChatPublishDisposition.UNAVAILABLE, 0)
        return ChatPublishResult(ChatPublishDisposition.PUBLISHED, result)


def get_chat_realtime_transport() -> ChatRealtimeTransport:
    """Build a lightweight adapter over the process-wide Redis pool."""
    return ChatRealtimeTransport(get_redis_client(), get_redis_settings().key_prefix)
