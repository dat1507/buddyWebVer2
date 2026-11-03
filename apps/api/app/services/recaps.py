"""Transactional recap lifecycle, ownership, visibility and batched projections."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, exists, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.event import Event, EventStatus, EventVisibility
from app.models.recap import Recap, RecapImage, RecapPhoto
from app.models.user import User
from app.schemas.recap import (
    PhotoOrderUpdate,
    PhotoResponse,
    RecapContent,
    RecapListResponse,
    RecapResponse,
)
from app.services.audit_logs import record_audit_log
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
)
from app.services.recap_images import prepare_recap_images_async


def fail(code: int, message: str) -> HTTPException:
    return HTTPException(
        code, message, headers={"Cache-Control": "private, no-store", "Vary": "Cookie"}
    )


def public_clause() -> ColumnElement[bool]:
    related_public = exists(
        select(Event.id).where(
            Event.id == Recap.related_event_id,
            Event.deleted_at.is_(None),
            Event.visibility == EventVisibility.PUBLIC,
            Event.status.in_([EventStatus.PUBLISHED, EventStatus.CANCELLED]),
            Event.published_at.is_not(None),
        )
    )
    return and_(
        Recap.deleted_at.is_(None),
        Recap.status == "PUBLISHED",
        or_(Recap.related_event_id.is_(None), related_public),
    )


async def get_recap(
    session: AsyncSession,
    recap_id: UUID,
    *,
    admin: bool = False,
    lock: bool = False,
    include_deleted: bool = False,
) -> Recap:
    statement = select(Recap).where(Recap.id == recap_id)
    if not include_deleted:
        statement = statement.where(Recap.deleted_at.is_(None))
    if not admin:
        statement = statement.where(public_clause())
    if lock:
        statement = statement.with_for_update()
    recap = await session.scalar(statement)
    if recap is None:
        raise fail(404, "Recap not found.")
    return recap


def require_version(recap: Recap, version: int) -> None:
    if recap.version != version:
        raise fail(409, "Recap version is stale.")


async def photos_for(
    session: AsyncSession, recap_id: UUID, *, deleted: bool = False
) -> list[RecapPhoto]:
    statement = select(RecapPhoto).where(RecapPhoto.recap_id == recap_id)
    if not deleted:
        statement = statement.where(RecapPhoto.deleted_at.is_(None))
    return list(await session.scalars(statement.order_by(RecapPhoto.sort_order, RecapPhoto.id)))


async def project_many(
    session: AsyncSession, recaps: list[Recap], *, cards: bool = False, admin: bool = False
) -> list[RecapResponse]:
    if not recaps:
        return []
    ids = [recap.id for recap in recaps]
    photos = list(
        await session.scalars(
            select(RecapPhoto)
            .where(RecapPhoto.recap_id.in_(ids))
            .order_by(RecapPhoto.sort_order, RecapPhoto.id)
        )
    )
    images = (
        list(
            await session.scalars(
                select(RecapImage).where(
                    RecapImage.photo_id.in_([photo.id for photo in photos]),
                    RecapImage.variant.in_(["display", "thumbnail"]),
                )
            )
        )
        if photos
        else []
    )
    sizes = {
        image.photo_id: (image.width, image.height)
        for image in images
        if image.variant == "display"
    }
    projected: list[RecapResponse] = []
    for recap in recaps:
        active = [
            photo
            for photo in photos
            if photo.recap_id == recap.id and photo.deleted_at is None and photo.id in sizes
        ]
        thumbnail = next(
            (photo.id for photo in active if photo.id == recap.thumbnail_id),
            active[0].id if active else None,
        )
        selected = [photo for photo in active if photo.id == thumbnail] if cards else active
        projected.append(
            RecapResponse(
                **{field: getattr(recap, field) for field in RecapContent.model_fields},
                id=recap.id,
                version=recap.version,
                status=cast(Literal["DRAFT", "PUBLISHED", "ARCHIVED"], recap.status),
                thumbnail_id=thumbnail,
                photos=[
                    PhotoResponse(
                        id=photo.id,
                        alt_en=photo.alt_en,
                        alt_de=photo.alt_de,
                        caption_en=photo.caption_en,
                        caption_de=photo.caption_de,
                        sort_order=photo.sort_order,
                        width=sizes[photo.id][0],
                        height=sizes[photo.id][1],
                    )
                    for photo in selected
                ],
                cleanup_pending=admin
                and any(
                    photo.recap_id == recap.id
                    and photo.deleted_at is not None
                    and photo.id in {image.photo_id for image in images}
                    for photo in photos
                ),
            )
        )
    return projected


async def project(session: AsyncSession, recap: Recap) -> RecapResponse:
    return (await project_many(session, [recap], admin=True))[0]


async def list_recaps(
    session: AsyncSession, *, page: int, year: int | None, admin: bool
) -> RecapListResponse:
    base = select(Recap).where(Recap.deleted_at.is_(None))
    if not admin:
        base = base.where(public_clause())
    years = list(
        await session.scalars(
            select(extract("year", Recap.event_date))
            .where(Recap.id.in_(base.with_only_columns(Recap.id)), Recap.event_date.is_not(None))
            .distinct()
            .order_by(extract("year", Recap.event_date).desc())
        )
    )
    filtered = base.where(extract("year", Recap.event_date) == year) if year is not None else base
    total = await session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    order = (Recap.event_date.desc().nulls_last(), Recap.created_at.desc(), Recap.id.desc())
    rows = list(await session.scalars(filtered.order_by(*order).offset((page - 1) * 9).limit(9)))
    mosaic_rows = (
        []
        if admin
        else list(
            await session.scalars(
                base.where(
                    exists(
                        select(RecapPhoto.id).where(
                            RecapPhoto.recap_id == Recap.id, RecapPhoto.deleted_at.is_(None)
                        )
                    )
                )
                .order_by(*order)
                .limit(5)
            )
        )
    )
    return RecapListResponse(
        items=await project_many(session, rows, cards=True, admin=admin),
        page=page,
        total=total,
        total_pages=(total + 8) // 9,
        years=[int(value) for value in years],
        mosaic=await project_many(session, mosaic_rows, cards=True),
        pending_cleanup=list(
            await session.scalars(
                select(Recap.id).where(
                    exists(
                        select(RecapPhoto.id)
                        .join(RecapImage, RecapImage.photo_id == RecapPhoto.id)
                        .where(RecapPhoto.recap_id == Recap.id, RecapPhoto.deleted_at.is_not(None))
                    )
                )
            )
        )
        if admin
        else [],
    )


async def validate_related(session: AsyncSession, event_id: UUID | None) -> None:
    if (
        event_id is not None
        and await session.scalar(
            select(Event.id).where(Event.id == event_id, Event.deleted_at.is_(None))
        )
        is None
    ):
        raise fail(422, "Related Event is unavailable.")


async def validate_publication(session: AsyncSession, recap: Recap) -> None:
    if not all(
        getattr(recap, field) and getattr(recap, field).strip()
        for field in ("title_en", "title_de", "summary_en", "summary_de")
    ):
        raise fail(422, "Publishing requires localized titles and summaries.")
    photos = await photos_for(session, recap.id)
    if not 1 <= len(photos) <= 12 or any(
        not photo.alt_en.strip() or not photo.alt_de.strip() for photo in photos
    ):
        raise fail(422, "Publishing requires 1–12 photos with EN/DE alt text.")
    count = await session.scalar(
        select(func.count())
        .select_from(RecapImage)
        .where(RecapImage.photo_id.in_([photo.id for photo in photos]))
    )
    if count != len(photos) * 2:
        raise fail(422, "Photos are incomplete.")
    if recap.related_event_id is not None:
        event = await session.scalar(select(Event).where(Event.id == recap.related_event_id))
        if (
            event is None
            or event.deleted_at is not None
            or event.visibility != EventVisibility.PUBLIC
            or event.status not in (EventStatus.PUBLISHED, EventStatus.CANCELLED)
            or event.published_at is None
        ):
            raise fail(422, "Related Event must be published and PUBLIC.")


async def audit(session: AsyncSession, actor: User, recap: Recap, action: str) -> None:
    await record_audit_log(
        session,
        actor,
        action=f"recap.{action}",
        resource_type="recap",
        resource_id=recap.id,
        new_value={"version": recap.version, "status": recap.status},
    )


def touch(recap: Recap, actor: User) -> None:
    recap.version += 1
    recap.updated_by = actor.id


async def save_content(
    session: AsyncSession, actor: User, payload: RecapContent, recap: Recap | None = None
) -> Recap:
    await validate_related(session, payload.related_event_id)
    if recap is None:
        recap = Recap(
            id=uuid4(), created_by=actor.id, updated_by=actor.id, version=1, status="DRAFT"
        )
        session.add(recap)
    else:
        touch(recap, actor)
    for field, value in payload.model_dump(exclude={"version"}).items():
        setattr(recap, field, value or None)
    await session.flush()
    if recap.status == "PUBLISHED":
        await validate_publication(session, recap)
    return recap


async def save_photos(
    session: AsyncSession, actor: User, recap: Recap, payload: PhotoOrderUpdate
) -> None:
    require_version(recap, payload.version)
    photos = await photos_for(session, recap.id)
    by_id = {photo.id: photo for photo in photos}
    incoming = [photo.id for photo in payload.photos]
    if (
        len(set(incoming)) != len(incoming)
        or set(incoming) != set(by_id)
        or (payload.thumbnail_id is not None and payload.thumbnail_id not in by_id)
    ):
        raise fail(422, "Photo order or thumbnail ownership is invalid.")
    for index, edit in enumerate(payload.photos):
        photo = by_id[edit.id]
        photo.sort_order = index
        for field in ("alt_en", "alt_de", "caption_en", "caption_de"):
            setattr(photo, field, getattr(edit, field))
    recap.thumbnail_id = payload.thumbnail_id
    touch(recap, actor)
    await session.flush()
    if recap.status == "PUBLISHED":
        await validate_publication(session, recap)


async def upload_photo(
    session: AsyncSession,
    storage: ImageStorageService,
    actor: User,
    recap: Recap,
    *,
    upload_id: UUID,
    version: int,
    content: bytes,
    original_name: str,
    content_type: str,
    alt_en: str,
    alt_de: str,
    staged: list[StorageObjectRef],
) -> None:
    fingerprint = hashlib.sha256(content).hexdigest()
    previous = await session.scalar(
        select(RecapPhoto).where(RecapPhoto.recap_id == recap.id, RecapPhoto.upload_id == upload_id)
    )
    if previous is not None:
        if previous.fingerprint != fingerprint or previous.deleted_at is not None:
            raise fail(409, "Upload identifier was already used.")
        return
    require_version(recap, version)
    photos = await photos_for(session, recap.id)
    if len(photos) >= 12:
        raise fail(422, "A recap supports at most 12 photos.")
    derivatives = await prepare_recap_images_async(
        original_name=original_name, declared_content_type=content_type, content=content
    )
    photo = RecapPhoto(
        id=uuid4(),
        recap_id=recap.id,
        upload_id=upload_id,
        fingerprint=fingerprint,
        alt_en=alt_en,
        alt_de=alt_de,
        sort_order=len(photos),
    )
    session.add(photo)
    await session.flush()
    for variant, prepared in derivatives.items():
        # Store already validated derivatives without another expensive decode/encode.
        reference = StorageObjectRef(ImageBucket.EVENT_MEDIA, f"{uuid4()}.webp")
        staged.append(reference)
        await storage.upload_prepared_image(reference, prepared)
        session.add(
            RecapImage(
                photo_id=photo.id,
                object_key=reference.object_key,
                variant=variant,
                byte_size=prepared.byte_size,
                width=prepared.width,
                height=prepared.height,
            )
        )
    touch(recap, actor)
    await session.flush()
    if recap.status == "PUBLISHED":
        await validate_publication(session, recap)


async def cleanup_photos(session: AsyncSession, storage: ImageStorageService, recap: Recap) -> bool:
    """Keep failed object references durable; repeated deletes are safe and retryable."""
    photos = [
        photo
        for photo in await photos_for(session, recap.id, deleted=True)
        if photo.deleted_at is not None
    ]
    pending = False
    for photo in photos:
        images = list(
            await session.scalars(select(RecapImage).where(RecapImage.photo_id == photo.id))
        )
        for image in images:
            try:
                await storage.delete_image(
                    StorageObjectRef(ImageBucket.EVENT_MEDIA, image.object_key)
                )
                await session.delete(image)
            except StorageOperationError:
                pending = True
        await session.flush()
        # Retain the photo tombstone and upload UUID: a lost response must never resurrect a delete.
    await session.commit()
    return pending


async def mark_deleted(
    session: AsyncSession, actor: User, recap: Recap, photo_id: UUID | None = None
) -> bool:
    photos = await photos_for(session, recap.id)
    if photo_id is not None and photo_id not in {photo.id for photo in photos}:
        raise fail(404, "Photo not found.")
    remaining = [photo for photo in photos if photo.id != photo_id] if photo_id else []
    if photo_id and recap.status == "PUBLISHED" and not remaining:
        raise fail(422, "Unpublish before removing the last photo.")
    changed = recap.thumbnail_id == photo_id or (
        photo_id is not None and recap.thumbnail_id is None and photos[0].id == photo_id
    )
    if photo_id is None:
        recap.deleted_at = datetime.now(UTC)
        recap.status = "ARCHIVED"
    if recap.thumbnail_id not in {photo.id for photo in remaining}:
        recap.thumbnail_id = None
    for photo in photos:
        if photo_id is None or photo.id == photo_id:
            photo.deleted_at = datetime.now(UTC)
    for index, photo in enumerate(remaining):
        photo.sort_order = index
    touch(recap, actor)
    return changed
