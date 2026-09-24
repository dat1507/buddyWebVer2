"""Authenticated EMAIL-004 current-address replacement orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmailVerificationDeliverySettings
from app.models import User, UserRole
from app.services.auth import (
    POSTGRES_UNIQUE_VIOLATION,
    EmailValidationError,
    canonicalize_email,
)
from app.services.email_verification_requests import (
    EmailVerificationRequestError,
    request_email_verification,
)
from app.services.passwords import verify_password


class EmailChangeError(ValueError):
    """Sanitized base failure for authenticated email replacement."""


class EmailChangeAuthenticationError(EmailChangeError):
    """Raised when the current account is no longer eligible for the change."""


class EmailChangeConflictError(EmailChangeError):
    """Raised without revealing which account owns a conflicting address."""


class EmailChangePasswordError(EmailChangeError):
    """Raised when current-password confirmation fails without invalidating the session."""


@dataclass(frozen=True, slots=True)
class EmailChangeResult:
    """Updated persisted session projection with no credential material."""

    user: User = field(repr=False)


def _postgres_sqlstate(error: IntegrityError) -> str | None:
    current: BaseException | None = error.orig
    while current is not None:
        for attribute in ("sqlstate", "pgcode"):
            value = getattr(current, attribute, None)
            if isinstance(value, str):
                return value
        current = current.__cause__
    return None


async def change_current_user_email(
    session: AsyncSession,
    user_id: UUID,
    new_email: str,
    current_password: str,
    delivery_settings: EmailVerificationDeliverySettings,
) -> EmailChangeResult:
    """Atomically replace one USER email, relock capabilities, and request verification."""
    try:
        canonical_email = canonicalize_email(new_email)
    except EmailValidationError:
        raise EmailChangeConflictError("Email address could not be changed.") from None

    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if (
        user is None
        or user.role is not UserRole.USER
        or not user.is_active
        or user.deleted_at is not None
    ):
        raise EmailChangeAuthenticationError("Email change could not be authorized.")
    if not verify_password(current_password, user.password_hash):
        raise EmailChangePasswordError("Email change could not be authorized.")
    if user.email == canonical_email:
        raise EmailChangeConflictError("Email address could not be changed.")

    user.email = canonical_email
    user.email_verified_at = None
    try:
        await session.flush()
    except IntegrityError as error:
        if _postgres_sqlstate(error) == POSTGRES_UNIQUE_VIOLATION:
            raise EmailChangeConflictError("Email address could not be changed.") from None
        raise

    try:
        await request_email_verification(session, user.id, delivery_settings)
    except EmailVerificationRequestError:
        raise EmailChangeAuthenticationError("Email change could not be authorized.") from None
    return EmailChangeResult(user=user)
