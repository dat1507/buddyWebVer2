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
