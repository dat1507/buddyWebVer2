"""Owner-bound avatar metadata and private delivery authorization."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    User,
    UserRole,
)
from app.models.profile import PROFILE_IMAGE_BUCKET
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
    StoredImage,
    replace_image_reference,
)
from app.services.profiles import ProfileAccessError, get_or_create_own_profile


class ProfilePhotoNotFoundError(LookupError):
    """Raised when a photo is absent or outside the caller's authorization boundary."""


@dataclass(frozen=True, slots=True)
class ProfilePhotoMutation:
    photo: ProfilePhoto
    cleanup_pending: bool


def _require_profile_owner(owner: User) -> None:
    if not owner.is_active or owner.deleted_at is not None or owner.role is not UserRole.USER:
        raise ProfileAccessError("Profile photo access is not permitted.")


def _reference(photo: ProfilePhoto) -> StorageObjectRef:
    if photo.bucket != PROFILE_IMAGE_BUCKET:
        raise RuntimeError("Profile photo storage metadata is invalid.")
    return StorageObjectRef(
        bucket=ImageBucket.PROFILE_IMAGES,
        object_key=photo.object_key,
    )


async def _locked_own_profile(session: AsyncSession, owner: User) -> StudentProfile:
    _require_profile_owner(owner)
    profile = await session.scalar(
        select(StudentProfile)
        .where(
            StudentProfile.user_id == owner.id,
            StudentProfile.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if profile is not None:
        return profile
    return await get_or_create_own_profile(session, owner)


async def get_own_avatar(session: AsyncSession, owner: User) -> ProfilePhoto | None:
    """Return the current active avatar selected only through its authenticated owner."""
    _require_profile_owner(owner)
    result = await session.execute(
        select(ProfilePhoto)
        .join(StudentProfile, StudentProfile.id == ProfilePhoto.profile_id)
        .where(
            StudentProfile.user_id == owner.id,
            StudentProfile.deleted_at.is_(None),
            ProfilePhoto.is_avatar.is_(True),
            ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
            ProfilePhoto.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def replace_own_avatar(
    session: AsyncSession,
    storage: ImageStorageService,
    owner: User,
    *,
    original_name: str,
    declared_content_type: str,
    content: bytes,
) -> ProfilePhotoMutation:
    """Replace one owner's avatar while preserving the prior reference on failure."""
    profile = await _locked_own_profile(session, owner)
    previous_photo = await session.scalar(
        select(ProfilePhoto)
        .where(
            ProfilePhoto.profile_id == profile.id,
            ProfilePhoto.is_avatar.is_(True),
            ProfilePhoto.deleted_at.is_(None),
        )
        .with_for_update()
    )
    previous_reference = _reference(previous_photo) if previous_photo is not None else None
    attached: list[ProfilePhoto] = []

    async def attach(image: StoredImage) -> None:
        if previous_photo is not None:
            await session.delete(previous_photo)
            await session.flush()
        photo = ProfilePhoto(
            profile_id=profile.id,
            bucket=image.reference.bucket.value,
            object_key=image.reference.object_key,
            mime_type=image.mime_type,
            byte_size=image.byte_size,
            width=image.width,
            height=image.height,
            is_avatar=True,
            processing_status=ProfilePhotoProcessingStatus.READY,
        )
        session.add(photo)
        await session.flush()
        attached.append(photo)

    async def is_referenced(reference: StorageObjectRef) -> bool:
        reference_count = await session.scalar(
            select(func.count(ProfilePhoto.id)).where(
                ProfilePhoto.bucket == reference.bucket.value,
                ProfilePhoto.object_key == reference.object_key,
            )
        )
        return bool(reference_count)

    replacement = await replace_image_reference(
        session,
        storage,
        bucket=ImageBucket.PROFILE_IMAGES,
        original_name=original_name,
        declared_content_type=declared_content_type,
        content=content,
        attach=attach,
        previous=previous_reference,
        is_referenced=is_referenced,
    )
    if not attached:  # pragma: no cover - successful helper execution guarantees attachment.
        raise RuntimeError("Profile photo attachment did not complete.")
    return ProfilePhotoMutation(
        photo=attached[0],
        cleanup_pending=replacement.cleanup_pending,
    )


async def remove_own_avatar(
    session: AsyncSession,
    storage: ImageStorageService,
    owner: User,
    photo_id: UUID,
) -> bool:
    """Commit owner-bound metadata removal before deleting the now-orphaned object."""
    _require_profile_owner(owner)
    photo = await session.scalar(
        select(ProfilePhoto)
        .join(StudentProfile, StudentProfile.id == ProfilePhoto.profile_id)
        .where(
            ProfilePhoto.id == photo_id,
            ProfilePhoto.is_avatar.is_(True),
            ProfilePhoto.deleted_at.is_(None),
            StudentProfile.user_id == owner.id,
            StudentProfile.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if photo is None:
        raise ProfilePhotoNotFoundError("Profile photo was not found.")
    reference = _reference(photo)
    await session.delete(photo)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    try:
        await storage.delete_image(reference)
    except StorageOperationError:
        return True
    return False


async def get_authorized_profile_photo(
    session: AsyncSession,
    viewer: User,
    photo_id: UUID,
) -> ProfilePhoto:
    """Resolve owner or coordinator access without accepting a client-supplied owner ID."""
    conditions = [
        ProfilePhoto.id == photo_id,
        ProfilePhoto.is_avatar.is_(True),
        ProfilePhoto.processing_status == ProfilePhotoProcessingStatus.READY,
        ProfilePhoto.deleted_at.is_(None),
        StudentProfile.deleted_at.is_(None),
        User.role == UserRole.USER,
        User.deleted_at.is_(None),
    ]
    if viewer.role is UserRole.USER:
        conditions.append(StudentProfile.user_id == viewer.id)
    elif viewer.role is not UserRole.ADMIN:
        raise ProfileAccessError("Profile photo access is not permitted.")

    photo = await session.scalar(
        select(ProfilePhoto)
        .join(StudentProfile, StudentProfile.id == ProfilePhoto.profile_id)
        .join(User, User.id == StudentProfile.user_id)
        .where(*conditions)
    )
    if photo is None:
        raise ProfilePhotoNotFoundError("Profile photo was not found.")
    return photo


def profile_photo_reference(photo: ProfilePhoto) -> StorageObjectRef:
    """Build a trusted private-object reference from persisted metadata."""
    return _reference(photo)
