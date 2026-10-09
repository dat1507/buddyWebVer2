"""Audience-aware public and member Event list/detail endpoints."""

from datetime import datetime
from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_image_storage_service, optional_auth
from app.core.database import get_database_session
from app.models import EventPhase, User
from app.schemas.event import EventLocale, PublicEventListResponse, PublicEventResponse
from app.services.event_queries import (
    EventQueryValidationError,
    PublicEventFilters,
    get_public_event_detail,
    list_public_events,
)
from app.services.image_storage import ImageStorageService, StorageOperationError

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}

router = APIRouter(prefix="/api/events", tags=["events"])


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


def _query_invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Event query is invalid.",
        headers=_NO_STORE_HEADERS,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Event not found.",
        headers=_NO_STORE_HEADERS,
    )


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Event media is unavailable.",
        headers=_NO_STORE_HEADERS,
    )


@router.get("", response_model=PublicEventListResponse)
async def read_events(
    response: Response,
    viewer: Annotated[User | None, Depends(optional_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    locale: Annotated[EventLocale, Query()] = "en",
    category: Annotated[str | None, Query(max_length=80)] = None,
    phase: Annotated[EventPhase | None, Query()] = None,
    from_instant: Annotated[datetime | None, Query(alias="from")] = None,
    to_instant: Annotated[datetime | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PublicEventListResponse:
    """List authoritative Events visible to the anonymous or verified-member audience."""
    try:
        result = await list_public_events(
            session,
            storage,
            viewer=viewer,
            filters=PublicEventFilters(
                locale=locale,
                category=category,
                phase=phase,
                from_instant=from_instant,
                to_instant=to_instant,
                page=page,
                page_size=page_size,
            ),
        )
    except EventQueryValidationError as error:
        raise _query_invalid() from error
    except StorageOperationError as error:
        raise _storage_unavailable() from error
    _mark_private(response)
    return result


@router.get("/{event_id}", response_model=PublicEventResponse)
async def read_event_detail(
    event_id: UUID,
    response: Response,
    viewer: Annotated[User | None, Depends(optional_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    locale: Annotated[EventLocale, Query()] = "en",
) -> PublicEventResponse:
    """Read one Event without distinguishing hidden, deleted, and unknown identifiers."""
    try:
        event = await get_public_event_detail(
            session,
            storage,
            event_id,
            viewer=viewer,
            locale=locale,
        )
    except StorageOperationError as error:
        raise _storage_unavailable() from error
    if event is None:
        raise _not_found()
    _mark_private(response)
    return event
