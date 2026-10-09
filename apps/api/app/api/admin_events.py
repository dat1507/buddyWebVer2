"""ADMIN-only Event inventory, CRUD, editorial status, and guarded deletion endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_image_storage_service,
    require_role,
    require_session_csrf,
)
from app.core.database import get_database_session
from app.models import EventPhase, EventStatus, EventVisibility, User, UserRole
from app.schemas.event import (
    AdminEventListResponse,
    AdminEventResponse,
    EventDeleteResponse,
    EventDraftCreate,
    EventDraftUpdate,
    EventStatusUpdate,
)
from app.services.admin_event_queries import (
    AdminEventFilters,
    AdminEventQueryValidationError,
    get_admin_event_detail,
    list_admin_events,
)
from app.services.audit_logs import record_audit_log
from app.services.csrf import CsrfTokenClaims
from app.services.events import (
    EventAccessError,
    EventDependencyConflictError,
    EventNotFoundError,
    EventValidationError,
    EventVersionConflictError,
    cleanup_deleted_event_media,
    create_event_draft,
    delete_event,
    project_admin_event,
    set_event_status,
    update_event_draft,
)
from app.services.image_storage import ImageStorageService

_PRIVATE_HEADERS: Final = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(
    prefix="/api/admin/events",
    tags=["admin-events"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "An ADMIN session is required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _PRIVATE_HEADERS.items():
        response.headers[name] = value


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail, headers=_PRIVATE_HEADERS)


def _map_domain_error(error: Exception) -> HTTPException:
    if isinstance(error, EventNotFoundError):
        return _error(status.HTTP_404_NOT_FOUND, "Event not found.")
    if isinstance(error, EventVersionConflictError):
        return _error(status.HTTP_409_CONFLICT, "Event version is stale.")
    if isinstance(error, EventDependencyConflictError):
        return _error(status.HTTP_409_CONFLICT, "Event has dependent records.")
    if isinstance(error, EventValidationError):
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "Event is invalid.")
    if isinstance(error, EventAccessError):
        return _error(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    raise error


@router.get("", response_model=AdminEventListResponse)
async def read_admin_events(
    response: Response,
    _current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    event_status: Annotated[EventStatus | None, Query(alias="status")] = None,
    visibility: Annotated[EventVisibility | None, Query()] = None,
    phase: Annotated[EventPhase | None, Query()] = None,
    from_instant: Annotated[datetime | None, Query(alias="from")] = None,
    to_instant: Annotated[datetime | None, Query(alias="to")] = None,
) -> AdminEventListResponse:
    """List every active editorial state for authorized coordinators."""
    try:
        result = await list_admin_events(
            session,
            filters=AdminEventFilters(
                page=page,
                page_size=page_size,
                search=search,
                status=event_status,
                visibility=visibility,
                phase=phase,
                from_instant=from_instant,
                to_instant=to_instant,
            ),
        )
    except AdminEventQueryValidationError as error:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "Event query is invalid.") from error
    _mark_private(response)
    return result


@router.get("/{event_id}", response_model=AdminEventResponse)
async def read_admin_event_detail(
    event_id: UUID,
    response: Response,
    _current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminEventResponse:
    """Read one Event without exposing actor IDs or Storage object keys."""
    event = await get_admin_event_detail(session, event_id)
    if event is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Event not found.")
    _mark_private(response)
    return event


@router.post("", response_model=AdminEventResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_event(
    payload: EventDraftCreate,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminEventResponse:
    """Create one private draft with a session-derived creator and atomic audit."""
    try:
        event = await create_event_draft(session, current_admin, payload)
        await record_audit_log(
            session,
            current_admin,
            action="event.create",
            resource_type="event",
            resource_id=event.id,
            new_value={
                "status": event.status,
                "visibility": event.visibility,
                "version": event.version,
            },
        )
        await session.commit()
    except (
        EventAccessError,
        EventDependencyConflictError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return project_admin_event(event)


@router.put("/{event_id}", response_model=AdminEventResponse)
async def update_admin_event(
    event_id: UUID,
    payload: EventDraftUpdate,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminEventResponse:
    """Apply one optimistic Event content update with atomic audit."""
    try:
        event = await update_event_draft(session, current_admin, event_id, payload)
        await record_audit_log(
            session,
            current_admin,
            action="event.update",
            resource_type="event",
            resource_id=event.id,
            old_value={"version": payload.version},
            new_value={
                "status": event.status,
                "visibility": event.visibility,
                "version": event.version,
            },
        )
        await session.commit()
    except (
        EventAccessError,
        EventDependencyConflictError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return project_admin_event(event)


@router.patch("/{event_id}/status", response_model=AdminEventResponse)
async def update_admin_event_status(
    event_id: UUID,
    payload: EventStatusUpdate,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminEventResponse:
    """Publish, unpublish, or cancel an Event as a separate editorial action."""
    try:
        event = await set_event_status(session, current_admin, event_id, payload)
        await record_audit_log(
            session,
            current_admin,
            action="event.status_update",
            resource_type="event",
            resource_id=event.id,
            old_value={"version": payload.version},
            new_value={"status": event.status, "version": event.version},
        )
        await session.commit()
    except (
        EventAccessError,
        EventDependencyConflictError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return project_admin_event(event)


@router.delete("/{event_id}", response_model=EventDeleteResponse)
async def delete_admin_event(
    event_id: UUID,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    version: Annotated[int, Query(ge=1)],
) -> EventDeleteResponse:
    """Delete an eligible Event atomically, then attempt non-transactional object cleanup."""
    try:
        plan = await delete_event(session, current_admin, event_id, version=version)
        await record_audit_log(
            session,
            current_admin,
            action="event.delete",
            resource_type="event",
            resource_id=plan.event_id,
            old_value={"version": version},
        )
        await session.commit()
    except (
        EventAccessError,
        EventDependencyConflictError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise

    failed = await cleanup_deleted_event_media(storage, plan)
    _mark_private(response)
    return EventDeleteResponse(
        event_id=plan.event_id,
        cleanup_pending=bool(failed),
        failed_object_count=len(failed),
    )
