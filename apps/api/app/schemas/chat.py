"""Strict privacy-safe HTTP contracts for one-to-one Buddy chat."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictStr

from app.models import MAX_BUDDY_MESSAGE_CODE_POINTS


class ChatMessageCreateRequest(BaseModel):
    """One plain-text send attempt with a sender-scoped retry identity."""

    model_config = ConfigDict(extra="forbid")

    client_message_id: UUID
    body: StrictStr = Field(max_length=MAX_BUDDY_MESSAGE_CODE_POINTS)


class ChatMessageResponse(BaseModel):
    """Minimal message projection without persisted participant identifiers."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    sender: Literal["self", "buddy"]
    body: StrictStr
    created_at: AwareDatetime
    read_at: AwareDatetime | None


class ChatMessagePageResponse(BaseModel):
    """Chronological page with an opaque cursor for the next older page."""

    model_config = ConfigDict(extra="forbid")

    items: list[ChatMessageResponse]
    next_before: StrictStr | None
    page_size: int = Field(ge=1, le=100)


class ChatReadRequest(BaseModel):
    """Acknowledge incoming messages up to one authorized message boundary."""

    model_config = ConfigDict(extra="forbid")

    through_message_id: UUID


class ChatUnreadConversationResponse(BaseModel):
    """Unread count for one authorized conversation."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    unread_count: int = Field(ge=1)


class ChatUnreadSummaryResponse(BaseModel):
    """Recoverable aggregate backed by persisted message read state."""

    model_config = ConfigDict(extra="forbid")

    total_unread_messages: int = Field(ge=0)
    conversations: list[ChatUnreadConversationResponse]


class ChatWebSocketSendEvent(BaseModel):
    """The only client-authored realtime event accepted by CHAT-003."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["message.send"]
    client_message_id: UUID
    body: StrictStr = Field(max_length=MAX_BUDDY_MESSAGE_CODE_POINTS)


class ChatWebSocketReadyEvent(BaseModel):
    """Confirms live subscription while naming REST as the gap-recovery source."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.ready"] = "chat.ready"
    recovery: Literal["history"] = "history"


class ChatUnreadWebSocketReadyEvent(BaseModel):
    """Confirms workspace notification coverage while naming REST recovery."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.unread.ready"] = "chat.unread.ready"
    recovery: Literal["unread-summary"] = "unread-summary"


class ChatUnreadWebSocketChangedEvent(BaseModel):
    """A content-free hint to reconcile authoritative unread state."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.unread.changed"] = "chat.unread.changed"
    recovery: Literal["unread-summary"] = "unread-summary"


class ChatWebSocketMessageEvent(BaseModel):
    """One privacy-safe committed message projected for the receiving participant."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.message.created"] = "chat.message.created"
    message: ChatMessageResponse


class ChatWebSocketSendAcceptedEvent(BaseModel):
    """Transport acknowledgement that never substitutes for persisted history."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.message.accepted"] = "chat.message.accepted"
    message_id: UUID
    realtime_delivery: Literal["published", "already_published", "unavailable"]
    recovery: Literal["history"] = "history"


class ChatWebSocketErrorEvent(BaseModel):
    """Stable sanitized protocol failure without reflected request content."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["chat.error"] = "chat.error"
    code: Literal[
        "CHAT_EVENT_INVALID",
        "CHAT_MESSAGE_INVALID",
        "CHAT_IDEMPOTENCY_KEY_REUSED",
        "CHAT_RATE_LIMITED",
        "CHAT_REALTIME_UNAVAILABLE",
    ]
    recoverable: bool


def chat_message_response(
    *,
    message_id: UUID,
    sender_id: UUID,
    current_user_id: UUID,
    body: str,
    created_at: datetime,
    read_at: datetime | None,
) -> ChatMessageResponse:
    """Project a persisted message without exposing either participant UUID."""
    return ChatMessageResponse(
        id=message_id,
        sender="self" if sender_id == current_user_id else "buddy",
        body=body,
        created_at=created_at,
        read_at=read_at,
    )
