"""Admin Event cover lifecycle and audience-authorized media delivery endpoints."""

from __future__ import annotations

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_image_storage_service,
    optional_auth,
    require_role,
    require_session_csrf,
)
from app.api.multipart import MultipartUploadError, read_multipart_image_upload
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.event import (
    AdminEventMediaResponse,
    EventCoverUploadFields,
    EventCoverUploadResponse,
    EventMediaDeleteResponse,
    EventMediaUpdate,
    EventMediaUrlResponse,
)
from app.services.audit_logs import record_audit_log
from app.services.csrf import CsrfTokenClaims
from app.services.event_media import (
    EventCoverReplacement,
    EventMediaConflictError,
    EventMediaNotFoundError,
    cleanup_deleted_media,
    cleanup_replaced_cover,
    compensate_cover_replacement,
    delete_event_media,
    get_authorized_event_media,
    project_admin_event_media,
    stage_event_cover_replacement,
    update_event_media_metadata,
)
from app.services.events import (
    EventAccessError,
    EventNotFoundError,
    EventValidationError,
    EventVersionConflictError,
    project_admin_event,
)
from app.services.image_storage import (
    MAX_SIGNED_URL_SECONDS,
    ImageStorageService,
    ImageValidationError,
    StorageOperationError,
)

_PRIVATE_HEADERS: Final = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}
_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
require_admin = require_role(UserRole.ADMIN)

admin_router = APIRouter(
    prefix="/api/admin/events",
    tags=["admin-event-media"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "An ADMIN session is required."},
    },
)
public_router = APIRouter(prefix="/api/events", tags=["event-media"])


def _mark(response: Response, headers: dict[str, str]) -> None:
    for name, value in headers.items():
        response.headers[name] = value


def _error(code: int, detail: str, *, private: bool = True) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail=detail,
        headers=_PRIVATE_HEADERS if private else _NO_STORE_HEADERS,
    )


def _map_domain_error(error: Exception) -> HTTPException:
    if isinstance(error, (EventNotFoundError, EventMediaNotFoundError)):
        return _error(status.HTTP_404_NOT_FOUND, "Event media not found.")
    if isinstance(error, EventVersionConflictError):
        return _error(status.HTTP_409_CONFLICT, "Event version is stale.")
    if isinstance(error, EventMediaConflictError):
        return _error(status.HTTP_409_CONFLICT, "Event media is still required.")
    if isinstance(error, EventValidationError):
        return _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "Event media is invalid.")
    if isinstance(error, EventAccessError):
        return _error(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    raise error


async def _rollback_replacement(
    session: AsyncSession,
    storage: ImageStorageService,
    replacement: EventCoverReplacement | None,
) -> None:
    try:
        await session.rollback()
    finally:
        if replacement is not None:
            await compensate_cover_replacement(storage, replacement)


@admin_router.post(
    "/{event_id}/media",
    response_model=EventCoverUploadResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["version", "alt_en", "alt_de", "file"],
                        "properties": {
                            "version": {"type": "integer", "minimum": 1},
                            "alt_en": {"type": "string", "maxLength": 200},
                            "alt_de": {"type": "string", "maxLength": 200},
                            "file": {"type": "string", "format": "binary"},
                        },
                    }
                }
            },
        }
    },
)
async def upload_admin_event_cover(
    event_id: UUID,
    request: Request,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> EventCoverUploadResponse:
    """Stream, validate, attach, audit, and commit one Event cover replacement."""
    replacement: EventCoverReplacement | None = None
    try:
        upload = await read_multipart_image_upload(request)
        fields = EventCoverUploadFields.model_validate(upload.fields)
        replacement = await stage_event_cover_replacement(
            session,
            storage,
            current_admin,
            event_id,
            version=fields.version,
            original_name=upload.file_name,
            declared_content_type=upload.content_type,
            content=upload.content,
            alt_en=fields.alt_en,
            alt_de=fields.alt_de,
        )
        await record_audit_log(
            session,
            current_admin,
            action="event.media_replace",
            resource_type="event",
            resource_id=event_id,
            old_value={"version": fields.version},
            new_value={
                "version": replacement.event.version,
                "media_id": replacement.media.id,
                "mime_type": replacement.media.mime_type,
                "byte_size": replacement.media.byte_size,
            },
        )
        await session.commit()
    except (MultipartUploadError, ImageValidationError, ValidationError) as error:
        await _rollback_replacement(session, storage, replacement)
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "Event media is invalid.") from error
    except StorageOperationError as error:
        await _rollback_replacement(session, storage, replacement)
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Event media storage is unavailable."
        ) from error
    except (
        EventAccessError,
        EventMediaConflictError,
        EventMediaNotFoundError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await _rollback_replacement(session, storage, replacement)
        raise _map_domain_error(error) from error
    except Exception:
        await _rollback_replacement(session, storage, replacement)
        raise

    cleanup_succeeded = await cleanup_replaced_cover(storage, replacement)
    _mark(response, _PRIVATE_HEADERS)
    return EventCoverUploadResponse(
        event=project_admin_event(replacement.event),
        media=project_admin_event_media(replacement.media),
        cleanup_pending=not cleanup_succeeded,
    )


@admin_router.patch(
    "/{event_id}/media/{media_id}",
    response_model=AdminEventMediaResponse,
)
async def update_admin_event_media(
    event_id: UUID,
    media_id: UUID,
    payload: EventMediaUpdate,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminEventMediaResponse:
    """Update same-Event cover metadata under parent Event optimistic concurrency."""
    try:
        event, media = await update_event_media_metadata(
            session,
            current_admin,
            event_id,
            media_id,
            payload,
        )
        await record_audit_log(
            session,
            current_admin,
            action="event.media_update",
            resource_type="event",
            resource_id=event_id,
            old_value={"version": payload.version},
            new_value={"version": event.version, "media_id": media.id},
        )
        await session.commit()
    except (
        EventAccessError,
        EventMediaConflictError,
        EventMediaNotFoundError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise
    _mark(response, _PRIVATE_HEADERS)
    return project_admin_event_media(media)


@admin_router.delete(
    "/{event_id}/media/{media_id}",
    response_model=EventMediaDeleteResponse,
)
async def delete_admin_event_media(
    event_id: UUID,
    media_id: UUID,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    version: Annotated[int, Query(ge=1)],
) -> EventMediaDeleteResponse:
    """Delete eligible cover metadata atomically, then clean its private object."""
    try:
        deletion = await delete_event_media(
            session,
            current_admin,
            event_id,
            media_id,
            version=version,
        )
        await record_audit_log(
            session,
            current_admin,
            action="event.media_delete",
            resource_type="event",
            resource_id=event_id,
            old_value={"version": version, "media_id": media_id},
            new_value={"version": deletion.event_version},
        )
        await session.commit()
    except (
        EventAccessError,
        EventMediaConflictError,
        EventMediaNotFoundError,
        EventNotFoundError,
        EventValidationError,
        EventVersionConflictError,
    ) as error:
        await session.rollback()
        raise _map_domain_error(error) from error
    except Exception:
        await session.rollback()
        raise

    cleanup_succeeded = await cleanup_deleted_media(storage, deletion)
    _mark(response, _PRIVATE_HEADERS)
    return EventMediaDeleteResponse(
        event_id=deletion.event_id,
        media_id=deletion.media_id,
        event_version=deletion.event_version,
        cleanup_pending=not cleanup_succeeded,
    )


@public_router.get(
    "/{event_id}/media/{media_id}/url",
    response_model=EventMediaUrlResponse,
)
async def read_event_media_url(
    event_id: UUID,
    media_id: UUID,
    response: Response,
    viewer: Annotated[User | None, Depends(optional_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> EventMediaUrlResponse:
    """Issue a short URL only after parent Event audience authorization."""
    authorized = await get_authorized_event_media(
        session,
        event_id,
        media_id,
        viewer=viewer,
    )
    if authorized is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Event media not found.", private=False)
    try:
        url = await storage.create_signed_url(
            authorized.reference,
            expires_in=MAX_SIGNED_URL_SECONDS,
        )
    except StorageOperationError as error:
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Event media storage is unavailable.",
            private=False,
        ) from error
    _mark(response, _NO_STORE_HEADERS)
    return EventMediaUrlResponse(
        id=authorized.media.id,
        event_id=authorized.media.event_id,
        url=url,
        expires_in=MAX_SIGNED_URL_SECONDS,
    )
