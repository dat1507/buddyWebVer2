"""Authenticated conversation-scoped WebSocket transport for Buddy chat."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, WebSocketException, status
from pydantic import BaseModel, ValidationError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.websockets import WebSocketState

from app.api.dependencies import (
    authenticate_verified_buddy_websocket,
    require_verified_chat_websocket,
)
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_session_factory
from app.core.observability import emit_chat_realtime_event
from app.core.rate_limits import (
    RateLimitExceeded,
    RateLimitUnavailable,
    check_websocket_connection_rate_limit,
    check_websocket_send_rate_limit,
)
from app.schemas.chat import (
    ChatWebSocketErrorEvent,
    ChatWebSocketMessageEvent,
    ChatWebSocketReadyEvent,
    ChatWebSocketSendAcceptedEvent,
    ChatWebSocketSendEvent,
    chat_message_response,
)
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.buddy_chat import (
    BuddyChatReadError,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    authorize_buddy_conversation,
    get_realtime_buddy_message,
    send_buddy_message,
)
from app.services.chat_realtime import (
    ChatPublishDisposition,
    ChatRealtimeTransport,
    ChatRedisSubscription,
    get_chat_realtime_transport,
)

router = APIRouter(prefix="/api/ws/chat", tags=["chat-realtime"])

_MAX_CLIENT_EVENT_BYTES: Final = 131_072
_CLIENT_SEND_TIMEOUT_SECONDS: Final = 5.0
_POLICY_CLOSE: Final = status.WS_1008_POLICY_VIOLATION
_UNAVAILABLE_CLOSE: Final = status.WS_1013_TRY_AGAIN_LATER


@dataclass(frozen=True, slots=True)
class _SocketClosure(Exception):
    code: int
    reason: str


class _SocketSender:
    """Serialize bounded socket writes from receiver and Redis listener tasks."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket
        self._lock = asyncio.Lock()

    async def send(self, event: BaseModel) -> None:
        try:
            async with self._lock:
                await asyncio.wait_for(
                    self._websocket.send_text(event.model_dump_json()),
                    timeout=_CLIENT_SEND_TIMEOUT_SECONDS,
                )
        except TimeoutError:
            raise _SocketClosure(status.WS_1011_INTERNAL_ERROR, "CHAT_CLIENT_TOO_SLOW") from None
        except RuntimeError:
            raise WebSocketDisconnect(code=status.WS_1006_ABNORMAL_CLOSURE) from None


def _as_socket_closure(error: WebSocketException) -> _SocketClosure:
    return _SocketClosure(error.code, error.reason or "CHAT_ACCESS_DENIED")


async def _receive_client_event(websocket: WebSocket) -> ChatWebSocketSendEvent:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(
            code=int(message.get("code", status.WS_1000_NORMAL_CLOSURE)),
            reason=str(message.get("reason", "")),
        )
    binary = message.get("bytes")
    if binary is not None:
        raise _SocketClosure(status.WS_1003_UNSUPPORTED_DATA, "CHAT_TEXT_EVENTS_REQUIRED")
    text = message.get("text")
    if not isinstance(text, str):
        raise _SocketClosure(status.WS_1003_UNSUPPORTED_DATA, "CHAT_TEXT_EVENTS_REQUIRED")
    if len(text.encode("utf-8")) > _MAX_CLIENT_EVENT_BYTES:
        raise _SocketClosure(status.WS_1009_MESSAGE_TOO_BIG, "CHAT_EVENT_TOO_LARGE")
    try:
        return ChatWebSocketSendEvent.model_validate_json(text)
    except ValidationError:
        raise ValueError("CHAT_EVENT_INVALID") from None


async def _forward_committed_messages(
    *,
    websocket: WebSocket,
    sender: _SocketSender,
    subscription: ChatRedisSubscription,
    session_factory: async_sessionmaker[AsyncSession],
    auth_settings: AuthTokenSettings,
    conversation_id: UUID,
) -> None:
    while True:
        notification = await subscription.next_notification()
        try:
            async with session_factory() as session:
                principal = await authenticate_verified_buddy_websocket(
                    websocket,
                    auth_settings,
                    session,
                )
                message = await get_realtime_buddy_message(
                    session,
                    conversation_id=conversation_id,
                    authenticated_user_id=principal.user.id,
                    message_id=notification.message_id,
                )
        except WebSocketException as error:
            raise _as_socket_closure(error) from None
        except BuddyChatReadError:
            raise _SocketClosure(_POLICY_CLOSE, "CHAT_CONVERSATION_NOT_FOUND") from None
        if message is None:
            # An expired/deleted identifier is never reflected to the browser.
            continue
        await sender.send(
            ChatWebSocketMessageEvent(
                message=chat_message_response(
                    message_id=message.id,
                    sender_id=message.sender_id,
                    current_user_id=principal.user.id,
                    body=message.body,
                    created_at=message.created_at,
                    read_at=message.read_at,
                )
            )
        )


async def _send_error(
    sender: _SocketSender,
    *,
    code: str,
    recoverable: bool,
) -> None:
    await sender.send(
        ChatWebSocketErrorEvent.model_validate({"code": code, "recoverable": recoverable})
    )


async def _receive_and_persist(
    *,
    websocket: WebSocket,
    sender: _SocketSender,
    transport: ChatRealtimeTransport,
    session_factory: async_sessionmaker[AsyncSession],
    auth_settings: AuthTokenSettings,
    conversation_id: UUID,
) -> None:
    while True:
        try:
            payload = await _receive_client_event(websocket)
        except ValueError:
            await _send_error(sender, code="CHAT_EVENT_INVALID", recoverable=True)
            continue

        try:
            async with session_factory() as session:
                try:
                    principal = await authenticate_verified_buddy_websocket(
                        websocket,
                        auth_settings,
                        session,
                    )
                    await check_websocket_send_rate_limit(websocket, principal.user)
                    message = await send_buddy_message(
                        session,
                        conversation_id=conversation_id,
                        authenticated_sender_id=principal.user.id,
                        client_message_id=payload.client_message_id,
                        body=payload.body,
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        except WebSocketException as error:
            raise _as_socket_closure(error) from None
        except RateLimitExceeded:
            await _send_error(sender, code="CHAT_RATE_LIMITED", recoverable=False)
            raise _SocketClosure(_POLICY_CLOSE, "CHAT_RATE_LIMITED") from None
        except RateLimitUnavailable:
            await _send_error(sender, code="CHAT_REALTIME_UNAVAILABLE", recoverable=True)
            raise _SocketClosure(_UNAVAILABLE_CLOSE, "CHAT_REALTIME_UNAVAILABLE") from None
        except ValueError:
            await _send_error(sender, code="CHAT_MESSAGE_INVALID", recoverable=True)
            continue
        except BuddyMessagePersistenceError as error:
            if error.reason is BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED:
                await _send_error(
                    sender,
                    code="CHAT_IDEMPOTENCY_KEY_REUSED",
                    recoverable=False,
                )
                continue
            raise _SocketClosure(_POLICY_CLOSE, "CHAT_CONVERSATION_NOT_FOUND") from None

        try:
            published = await transport.publish_committed(
                conversation_id=conversation_id,
                message_id=message.id,
            )
        except RedisError:
            await sender.send(
                ChatWebSocketSendAcceptedEvent(
                    message_id=message.id,
                    realtime_delivery="unavailable",
                )
            )
            raise _SocketClosure(_UNAVAILABLE_CLOSE, "CHAT_REALTIME_UNAVAILABLE") from None

        await sender.send(
            ChatWebSocketSendAcceptedEvent(
                message_id=message.id,
                realtime_delivery=published.disposition.value,
            )
        )
        if published.disposition is ChatPublishDisposition.UNAVAILABLE:
            raise _SocketClosure(_UNAVAILABLE_CLOSE, "CHAT_REALTIME_UNAVAILABLE")


async def _close_if_connected(websocket: WebSocket, closure: _SocketClosure) -> None:
    if websocket.application_state is WebSocketState.CONNECTED:
        try:
            await websocket.close(code=closure.code, reason=closure.reason)
        except RuntimeError:
            pass


@router.websocket("/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
    principal: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_chat_websocket),
    ],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
    auth_settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    transport: Annotated[ChatRealtimeTransport, Depends(get_chat_realtime_transport)],
) -> None:
    """Persist-before-publish realtime enhancement over CHAT-002 recovery APIs."""
    try:
        await check_websocket_connection_rate_limit(websocket)
        async with session_factory() as session:
            await authorize_buddy_conversation(
                session,
                conversation_id=conversation_id,
                authenticated_user_id=principal.user.id,
            )
    except RateLimitExceeded:
        raise WebSocketException(code=_POLICY_CLOSE, reason="CHAT_RATE_LIMITED") from None
    except RateLimitUnavailable:
        raise WebSocketException(
            code=_UNAVAILABLE_CLOSE,
            reason="CHAT_REALTIME_UNAVAILABLE",
        ) from None
    except BuddyChatReadError:
        raise WebSocketException(
            code=_POLICY_CLOSE,
            reason="CHAT_CONVERSATION_NOT_FOUND",
        ) from None

    try:
        subscription = await transport.subscribe(conversation_id)
    except RedisError:
        raise WebSocketException(
            code=_UNAVAILABLE_CLOSE,
            reason="CHAT_REALTIME_UNAVAILABLE",
        ) from None

    sender = _SocketSender(websocket)
    tasks: set[asyncio.Task[None]] = set()
    closure: _SocketClosure | None = None
    accepted = False
    try:
        await websocket.accept()
        accepted = True
        emit_chat_realtime_event(lifecycle="connected", close_code=status.WS_1000_NORMAL_CLOSURE)
        await sender.send(ChatWebSocketReadyEvent())
        tasks = {
            asyncio.create_task(
                _forward_committed_messages(
                    websocket=websocket,
                    sender=sender,
                    subscription=subscription,
                    session_factory=session_factory,
                    auth_settings=auth_settings,
                    conversation_id=conversation_id,
                )
            ),
            asyncio.create_task(
                _receive_and_persist(
                    websocket=websocket,
                    sender=sender,
                    transport=transport,
                    session_factory=session_factory,
                    auth_settings=auth_settings,
                    conversation_id=conversation_id,
                )
            ),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except WebSocketDisconnect:
                pass
            except _SocketClosure as error:
                closure = error
            except RedisError:
                closure = _SocketClosure(_UNAVAILABLE_CLOSE, "CHAT_REALTIME_UNAVAILABLE")
            except Exception:
                closure = _SocketClosure(
                    status.WS_1011_INTERNAL_ERROR,
                    "CHAT_REALTIME_INTERNAL_ERROR",
                )
    except WebSocketDisconnect:
        pass
    except _SocketClosure as error:
        closure = error
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await subscription.close()
        if closure is not None:
            await _close_if_connected(websocket, closure)
        if accepted:
            emit_chat_realtime_event(
                lifecycle="disconnected",
                close_code=(closure.code if closure is not None else status.WS_1000_NORMAL_CLOSURE),
            )
