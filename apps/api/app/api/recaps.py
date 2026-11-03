"""Recap APIs: private ADMIN mutations, public eligibility and short media capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_image_storage_service, require_role, require_session_csrf
from app.api.multipart import MultipartUploadError, read_multipart_image_upload
from app.core.database import get_database_session
from app.models import User, UserRole
from app.models.recap import RecapImage, RecapPhoto
from app.schemas.event import EventCoverUploadFields
from app.schemas.recap import (
    PhotoOrderUpdate,
    RecapContent,
    RecapDeleteResponse,
    RecapListResponse,
    RecapResponse,
    RecapStatusUpdate,
    RecapUpdate,
    RecapUrlResponse,
)
from app.services import recaps as service
from app.services.csrf import CsrfTokenClaims
from app.services.image_storage import (
    MAX_SIGNED_URL_SECONDS,
    ImageBucket,
    ImageStorageService,
    ImageValidationError,
    StorageObjectRef,
    StorageOperationError,
)
from app.services.recap_images import RECAP_UPLOAD_GATE

Admin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
Session = Annotated[AsyncSession, Depends(get_database_session)]
Storage = Annotated[ImageStorageService, Depends(get_image_storage_service)]
Csrf = Annotated[CsrfTokenClaims, Depends(require_session_csrf)]


def private_response(response: Response) -> None:
    response.headers.update(
        {"Cache-Control": "private, no-store", "Vary": "Cookie", "Pragma": "no-cache"}
    )


public_router = APIRouter(
    prefix="/api/recaps", tags=["recaps"], dependencies=[Depends(private_response)]
)
admin_router = APIRouter(
    prefix="/api/admin/recaps", tags=["admin-recaps"], dependencies=[Depends(private_response)]
)


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[None]:
    try:
        yield
        await session.commit()
    except Exception:
        await session.rollback()
        raise


@public_router.get("", response_model=RecapListResponse)
async def public_list(
    session: Session,
    page: Annotated[int, Query(ge=1)] = 1,
    year: Annotated[int | None, Query(ge=1900, le=9999)] = None,
) -> RecapListResponse:
    return await service.list_recaps(session, page=page, year=year, admin=False)


@public_router.get("/{recap_id}", response_model=RecapResponse)
async def public_detail(recap_id: UUID, session: Session) -> RecapResponse:
    recap = await service.get_recap(session, recap_id)
    return (await service.project_many(session, [recap]))[0]


async def media_url(
    session: AsyncSession,
    storage: ImageStorageService,
    recap_id: UUID,
    photo_id: UUID,
    variant: str,
    *,
    admin: bool,
) -> RecapUrlResponse:
    await service.get_recap(session, recap_id, admin=admin)
    image = await session.scalar(
        select(RecapImage)
        .join(RecapPhoto, RecapImage.photo_id == RecapPhoto.id)
        .where(
            RecapPhoto.id == photo_id,
            RecapPhoto.recap_id == recap_id,
            RecapPhoto.deleted_at.is_(None),
            RecapImage.variant == variant,
        )
    )
    if image is None:
        raise service.fail(404, "Photo not found.")
    try:
        url = await storage.create_signed_url(
            StorageObjectRef(ImageBucket.EVENT_MEDIA, image.object_key),
            expires_in=MAX_SIGNED_URL_SECONDS,
        )
    except StorageOperationError:
        raise service.fail(503, "Photo storage is unavailable.") from None
    return RecapUrlResponse(url=url, expires_in=MAX_SIGNED_URL_SECONDS)


@public_router.get("/{recap_id}/photos/{photo_id}/url", response_model=RecapUrlResponse)
async def public_photo_url(
    recap_id: UUID,
    photo_id: UUID,
    session: Session,
    storage: Storage,
    variant: Literal["thumbnail", "display"] = "thumbnail",
) -> RecapUrlResponse:
    return await media_url(session, storage, recap_id, photo_id, variant, admin=False)


@admin_router.get("", response_model=RecapListResponse)
async def admin_list(
    actor: Admin,
    session: Session,
    page: Annotated[int, Query(ge=1)] = 1,
    year: Annotated[int | None, Query(ge=1900, le=9999)] = None,
) -> RecapListResponse:
    return await service.list_recaps(session, page=page, year=year, admin=True)


@admin_router.get("/{recap_id}", response_model=RecapResponse)
async def admin_detail(recap_id: UUID, actor: Admin, session: Session) -> RecapResponse:
    return await service.project(session, await service.get_recap(session, recap_id, admin=True))


@admin_router.get("/{recap_id}/photos/{photo_id}/url", response_model=RecapUrlResponse)
async def admin_photo_url(
    recap_id: UUID,
    photo_id: UUID,
    actor: Admin,
    session: Session,
    storage: Storage,
    variant: Literal["thumbnail", "display"] = "thumbnail",
) -> RecapUrlResponse:
    return await media_url(session, storage, recap_id, photo_id, variant, admin=True)


@admin_router.post("", response_model=RecapResponse, status_code=201)
async def create_recap(
    payload: RecapContent, actor: Admin, csrf: Csrf, session: Session
) -> RecapResponse:
    async with transaction(session):
        recap = await service.save_content(session, actor, payload)
        await service.audit(session, actor, recap, "create")
        result = await service.project(session, recap)
    return result


@admin_router.put("/{recap_id}", response_model=RecapResponse)
async def update_recap(
    recap_id: UUID, payload: RecapUpdate, actor: Admin, csrf: Csrf, session: Session
) -> RecapResponse:
    async with transaction(session):
        recap = await service.get_recap(session, recap_id, admin=True, lock=True)
        service.require_version(recap, payload.version)
        recap = await service.save_content(session, actor, payload, recap)
        await service.audit(session, actor, recap, "update")
        result = await service.project(session, recap)
    return result


@admin_router.patch("/{recap_id}/status", response_model=RecapResponse)
async def status_recap(
    recap_id: UUID, payload: RecapStatusUpdate, actor: Admin, csrf: Csrf, session: Session
) -> RecapResponse:
    async with transaction(session):
        recap = await service.get_recap(session, recap_id, admin=True, lock=True)
        service.require_version(recap, payload.version)
        if payload.status == "PUBLISHED":
            await service.validate_publication(session, recap)
        recap.status = payload.status
        service.touch(recap, actor)
        await service.audit(session, actor, recap, "status")
        result = await service.project(session, recap)
    return result


@admin_router.put("/{recap_id}/photos", response_model=RecapResponse)
async def order_photos(
    recap_id: UUID, payload: PhotoOrderUpdate, actor: Admin, csrf: Csrf, session: Session
) -> RecapResponse:
    async with transaction(session):
        recap = await service.get_recap(session, recap_id, admin=True, lock=True)
        await service.save_photos(session, actor, recap, payload)
        await service.audit(session, actor, recap, "photos_update")
        result = await service.project(session, recap)
    return result


@admin_router.post("/{recap_id}/photos", response_model=RecapResponse)
async def upload_photo(
    recap_id: UUID,
    request: Request,
    actor: Admin,
    csrf: Csrf,
    session: Session,
    storage: Storage,
    upload_id: UUID,
) -> RecapResponse:
    if RECAP_UPLOAD_GATE.locked():
        raise service.fail(429, "Photo processing is busy. Retry shortly.")
    staged: list[StorageObjectRef] = []
    committed = False
    async with RECAP_UPLOAD_GATE:
        try:
            async with transaction(session):
                recap = await service.get_recap(session, recap_id, admin=True, lock=True)
                upload = await read_multipart_image_upload(request)
                fields = EventCoverUploadFields.model_validate(upload.fields)
                await service.upload_photo(
                    session,
                    storage,
                    actor,
                    recap,
                    upload_id=upload_id,
                    version=fields.version,
                    content=upload.content,
                    original_name=upload.file_name,
                    content_type=upload.content_type,
                    alt_en=fields.alt_en,
                    alt_de=fields.alt_de,
                    staged=staged,
                )
                await service.audit(session, actor, recap, "photo_upload")
                result = await service.project(session, recap)
            committed = True
            return result
        except (MultipartUploadError, ImageValidationError, ValidationError):
            raise service.fail(422, "Photo is invalid.") from None
        except StorageOperationError:
            raise service.fail(503, "Photo storage is unavailable.") from None
        finally:
            # Committed refs are protected by DB ownership; failed staged uploads become unreferenced
            # and are also recoverable through the existing age-gated orphan reconciler.
            if staged and not committed:
                for reference in staged:
                    try:
                        await storage.delete_image(reference)
                    except StorageOperationError:
                        pass


@admin_router.delete("/{recap_id}/photos/{photo_id}", response_model=RecapDeleteResponse)
async def delete_photo(
    recap_id: UUID,
    photo_id: UUID,
    actor: Admin,
    csrf: Csrf,
    session: Session,
    storage: Storage,
    version: Annotated[int, Query(ge=1)],
) -> RecapDeleteResponse:
    async with transaction(session):
        recap = await service.get_recap(session, recap_id, admin=True, lock=True)
        service.require_version(recap, version)
        changed = await service.mark_deleted(session, actor, recap, photo_id)
        await service.audit(session, actor, recap, "photo_delete")
    pending = await service.cleanup_photos(session, storage, recap)
    return RecapDeleteResponse(
        cleanup_pending=pending,
        thumbnail_changed=changed,
        recap=await service.project(session, recap),
    )


@admin_router.delete("/{recap_id}", response_model=RecapDeleteResponse)
async def delete_recap(
    recap_id: UUID,
    actor: Admin,
    csrf: Csrf,
    session: Session,
    storage: Storage,
    version: Annotated[int, Query(ge=1)],
) -> RecapDeleteResponse:
    async with transaction(session):
        recap = await service.get_recap(session, recap_id, admin=True, lock=True)
        service.require_version(recap, version)
        await service.mark_deleted(session, actor, recap)
        await service.audit(session, actor, recap, "delete")
    return RecapDeleteResponse(
        cleanup_pending=await service.cleanup_photos(session, storage, recap)
    )


@admin_router.post("/{recap_id}/cleanup", response_model=RecapDeleteResponse)
async def retry_cleanup(
    recap_id: UUID, actor: Admin, csrf: Csrf, session: Session, storage: Storage
) -> RecapDeleteResponse:
    recap = await service.get_recap(session, recap_id, admin=True, include_deleted=True, lock=True)
    await service.audit(session, actor, recap, "cleanup")
    return RecapDeleteResponse(
        cleanup_pending=await service.cleanup_photos(session, storage, recap)
    )
