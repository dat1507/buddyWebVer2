"""CHAT-003 Redis channel, payload, dedupe, and cleanup tests."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from redis.asyncio import Redis

from app.services.chat_realtime import (
    ChatPublishDisposition,
    ChatRealtimeTransport,
)

CONVERSATION_ID = UUID("10000000-0000-4000-8000-000000000001")
MESSAGE_ID = UUID("20000000-0000-4000-8000-000000000001")
PREFIX = "vgu-buddy:test:ops:v1"
CHANNEL = f"{PREFIX}:chat:{{{CONVERSATION_ID.hex}}}:events:v1"


@pytest.mark.anyio
async def test_publish_uses_private_channel_minimal_payload_and_distributed_dedupe() -> None:
    redis = MagicMock(spec=Redis)
    redis.eval = AsyncMock(side_effect=[2, -1, 0])
    transport = ChatRealtimeTransport(cast(Redis, redis), PREFIX)

    published = await transport.publish_committed(
        conversation_id=CONVERSATION_ID,
        message_id=MESSAGE_ID,
    )
    duplicate = await transport.publish_committed(
        conversation_id=CONVERSATION_ID,
        message_id=MESSAGE_ID,
    )
    unavailable = await transport.publish_committed(
        conversation_id=CONVERSATION_ID,
        message_id=UUID(int=3),
    )

    assert published.disposition is ChatPublishDisposition.PUBLISHED
    assert published.subscriber_count == 2
    assert duplicate.disposition is ChatPublishDisposition.ALREADY_PUBLISHED
    assert unavailable.disposition is ChatPublishDisposition.UNAVAILABLE
    arguments = redis.eval.await_args_list[0].args
    assert arguments[2].startswith(f"{PREFIX}:chat:{{{CONVERSATION_ID.hex}}}:published:")
    assert arguments[3] == CHANNEL
    notification = arguments[4]
    assert str(MESSAGE_ID) in notification
    assert str(CONVERSATION_ID) not in notification
    assert "private body" not in notification
    assert "sender" not in notification


@pytest.mark.anyio
async def test_subscription_filters_untrusted_payload_and_releases_only_pubsub() -> None:
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()
    pubsub.get_message = AsyncMock(
        side_effect=[
            {"type": "message", "channel": "other", "data": b"{}"},
            {"type": "message", "channel": CHANNEL, "data": b"not-json"},
            {
                "type": "message",
                "channel": CHANNEL.encode(),
                "data": (
                    b'{"version":1,"event":"message.committed",'
                    b'"message_id":"20000000-0000-4000-8000-000000000001"}'
                ),
            },
        ]
    )
    redis = MagicMock(spec=Redis)
    redis.pubsub.return_value = pubsub
    transport = ChatRealtimeTransport(cast(Redis, redis), PREFIX)

    subscription = await transport.subscribe(CONVERSATION_ID)
    notification = await subscription.next_notification()
    await subscription.close()
    await subscription.close()

    assert notification.message_id == MESSAGE_ID
    pubsub.subscribe.assert_awaited_once_with(CHANNEL)
    pubsub.unsubscribe.assert_awaited_once_with(CHANNEL)
    pubsub.aclose.assert_awaited_once()
    redis.aclose.assert_not_called()
