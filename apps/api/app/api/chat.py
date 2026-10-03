"""Participant-authorized HTTP recovery transport for Buddy chat."""

from __future__ import annotations

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_session_csrf, require_verified_buddy_capability
from app.core.database import get_database_session
from app.core.rate_limits import check_user_rate_limit
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessagePageResponse,
    ChatMessageResponse,
    ChatReadRequest,
    ChatUnreadConversationResponse,
    ChatUnreadSummaryResponse,
    chat_message_response,
)
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.buddy_chat import (
    DEFAULT_CHAT_MESSAGE_PAGE_SIZE,
    MAX_CHAT_MESSAGE_PAGE_SIZE,
    BuddyChatReadError,
    BuddyChatReadReason,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
    acknowledge_buddy_messages_read,
    get_buddy_unread_summary,
    list_buddy_messages,
    send_buddy_message,
)
from app.services.csrf import CsrfTokenClaims

router = APIRouter(prefix="/api/chat", tags=["chat"])
_NO_STORE_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


def _chat_read_http_exception(error: BuddyChatReadError) -> HTTPException:
    status_code = (
        status.HTTP_422_UNPROCESSABLE_CONTENT
        if error.reason is BuddyChatReadReason.INVALID_CURSOR
        else status.HTTP_404_NOT_FOUND
    )
    return HTTPException(
        status_code=status_code,
        detail=error.reason.value,
        headers=_NO_STORE_HEADERS,
    )


@router.get("/unread-summary", response_model=ChatUnreadSummaryResponse)
async def read_chat_unread_summary(
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ChatUnreadSummaryResponse:
    """Return persisted unread counts for the current VERIFIED ACTIVE participant."""
    summary = await get_buddy_unread_summary(
        session,
        authenticated_user_id=current.user.id,
    )
    _mark_private(response)
    return ChatUnreadSummaryResponse(
        total_unread_messages=summary.total_unread_messages,
        conversations=[
            ChatUnreadConversationResponse(
                conversation_id=item.conversation_id,
                unread_count=item.unread_count,
            )
            for item in summary.conversations
        ],
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessagePageResponse,
)
async def read_chat_messages(
    conversation_id: UUID,
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    before: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_CHAT_MESSAGE_PAGE_SIZE),
    ] = DEFAULT_CHAT_MESSAGE_PAGE_SIZE,
) -> ChatMessagePageResponse:
    """Return one chronological newest/next-older page for an ACTIVE participant."""
    try:
        page = await list_buddy_messages(
            session,
            conversation_id=conversation_id,
            authenticated_user_id=current.user.id,
            before=before,
            page_size=page_size,
        )
    except BuddyChatReadError as error:
        raise _chat_read_http_exception(error) from None
    _mark_private(response)
    return ChatMessagePageResponse(
        items=[
            chat_message_response(
                message_id=message.id,
                sender_id=message.sender_id,
                current_user_id=current.user.id,
                body=message.body,
                created_at=message.created_at,
                read_at=message.read_at,
            )
            for message in page.items
        ],
        next_before=page.next_before,
        page_size=page_size,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_message(
    conversation_id: UUID,
    payload: ChatMessageCreateRequest,
    request: Request,
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ChatMessageResponse:
    """Idempotently send one plain-text message as the authenticated participant."""
    await check_user_rate_limit(request, current.user)
    try:
        message = await send_buddy_message(
            session,
            conversation_id=conversation_id,
            authenticated_sender_id=current.user.id,
            client_message_id=payload.client_message_id,
            body=payload.body,
        )
        result = chat_message_response(
            message_id=message.id,
            sender_id=message.sender_id,
            current_user_id=current.user.id,
            body=message.body,
            created_at=message.created_at,
            read_at=message.read_at,
        )
        await session.commit()
    except ValueError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CHAT_MESSAGE_INVALID",
            headers=_NO_STORE_HEADERS,
        ) from None
    except BuddyMessagePersistenceError as error:
        await session.rollback()
        if error.reason is BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED:
            status_code = status.HTTP_409_CONFLICT
            detail = error.reason.value
        else:
            status_code = status.HTTP_404_NOT_FOUND
            detail = BuddyChatReadReason.CONVERSATION_NOT_FOUND.value
        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers=_NO_STORE_HEADERS,
        ) from None
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return result


@router.post(
    "/conversations/{conversation_id}/messages/read",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def acknowledge_chat_messages_read(
    conversation_id: UUID,
    payload: ChatReadRequest,
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> None:
    """Apply first-read retention to incoming messages through one visible boundary."""
    try:
        await acknowledge_buddy_messages_read(
            session,
            conversation_id=conversation_id,
            authenticated_reader_id=current.user.id,
            through_message_id=payload.through_message_id,
        )
        await session.commit()
    except BuddyChatReadError as error:
        await session.rollback()
        raise _chat_read_http_exception(error) from None
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
