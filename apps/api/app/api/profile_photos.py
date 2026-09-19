"""Authenticated profile-avatar upload, removal, and private delivery endpoints."""

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_image_storage_service,
    require_auth,
    require_role,
    require_session_csrf,
)
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.profile_photo import ProfilePhotoResponse, ProfilePhotoUrlResponse
from app.services.audit_logs import record_audit_log
from app.services.csrf import CsrfTokenClaims
from app.services.image_storage import (
    MAX_IMAGE_BYTES,
    MAX_SIGNED_URL_SECONDS,
    ImageStorageService,
    ImageValidationError,
    StorageOperationError,
)
from app.services.profile_photos import (
    ProfilePhotoNotFoundError,
    get_authorized_profile_photo,
    profile_photo_reference,
    remove_own_avatar,
    replace_own_avatar,
)
from app.services.profiles import ProfileAccessError

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
_EXTENSION_BY_CONTENT_TYPE: Final = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
require_profile_user = require_role(UserRole.USER)

router = APIRouter(
    prefix="/api/profile/photos",
    tags=["profile-photos"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "Insufficient permissions."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Profile photo not found.",
        headers=_NO_STORE_HEADERS,
    )


def _invalid_image() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Profile photo is invalid.",
        headers=_NO_STORE_HEADERS,
    )


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Image storage is unavailable.",
        headers=_NO_STORE_HEADERS,
    )


async def _read_image(request: Request) -> tuple[str, str, bytes]:
    content_type = request.headers.get("content-type", "").strip().casefold()
    extension = _EXTENSION_BY_CONTENT_TYPE.get(content_type)
    if extension is None:
        raise ImageValidationError("Profile photo content type is unsupported.")

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise ImageValidationError("Profile photo exceeds the upload limit.")
        chunks.append(chunk)
    return f"avatar.{extension}", content_type, b"".join(chunks)


@router.post(
    "",
    response_model=ProfilePhotoResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
async def upload_profile_photo(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> ProfilePhotoResponse:
    """Validate and atomically replace the current USER's single private avatar."""
    try:
        original_name, content_type, content = await _read_image(request)
        mutation = await replace_own_avatar(
            session,
            storage,
            current_user,
            original_name=original_name,
            declared_content_type=content_type,
            content=content,
        )
    except ImageValidationError as error:
        await session.rollback()
        raise _invalid_image() from error
    except StorageOperationError as error:
        await session.rollback()
        raise _storage_unavailable() from error
    except ProfileAccessError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfilePhotoResponse.model_validate(mutation.photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_photo(
    photo_id: UUID,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> Response:
    """Remove only the current USER's avatar metadata and backing private object."""
    try:
        await remove_own_avatar(session, storage, current_user, photo_id)
    except ProfilePhotoNotFoundError as error:
        raise _not_found() from error
    except StorageOperationError as error:
        raise _storage_unavailable() from error
    except ProfileAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
            headers=_NO_STORE_HEADERS,
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=_NO_STORE_HEADERS)


@router.get("/{photo_id}/url", response_model=ProfilePhotoUrlResponse)
async def read_profile_photo_url(
    photo_id: UUID,
    response: Response,
    current_user: Annotated[User, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> ProfilePhotoUrlResponse:
    """Issue a five-minute URL to the owner or an audited coordinator."""
    try:
        photo = await get_authorized_profile_photo(session, current_user, photo_id)
        signed_url = await storage.create_signed_url(
            profile_photo_reference(photo),
            expires_in=MAX_SIGNED_URL_SECONDS,
        )
        if current_user.role is UserRole.ADMIN:
            await record_audit_log(
                session,
                current_user,
                action="profile_photo.admin_read",
                resource_type="profile_photo",
                resource_id=photo.id,
            )
            await session.commit()
    except ProfilePhotoNotFoundError as error:
        raise _not_found() from error
    except StorageOperationError as error:
        await session.rollback()
        raise _storage_unavailable() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfilePhotoUrlResponse(
        id=photo.id,
        url=signed_url,
        expires_in=MAX_SIGNED_URL_SECONDS,
    )
