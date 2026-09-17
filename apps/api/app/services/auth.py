"""Registration, credential authentication, and role-verification services."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.services.passwords import hash_password, verify_password

MAX_EMAIL_LENGTH: Final = 254
MAX_EMAIL_LOCAL_PART_LENGTH: Final = 64
POSTGRES_UNIQUE_VIOLATION: Final = "23505"

_EMAIL_LOCAL_PART_PATTERN: Final = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+$")
_EMAIL_DOMAIN_LABEL_PATTERN: Final = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

# This is a non-secret cost-12 bcrypt hash used only to keep unknown-account login failures on the
# same expensive verification path as wrong-password failures. It cannot authenticate any account.
_DUMMY_PASSWORD_HASH: Final = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


class EmailValidationError(ValueError):
    """Raised when an email cannot be represented by the account identity contract."""


class AccountRegistrationError(ValueError):
    """Raised generically when a new account cannot be registered."""


class AuthenticationError(ValueError):
    """Raised generically when supplied credentials cannot authenticate an account."""


class RoleVerificationError(PermissionError):
    """Raised without disclosing role details when authorization fails."""


def canonicalize_email(email: str) -> str:
    """Trim, validate, and case-fold one conservative ASCII mailbox identity."""
    candidate = email.strip()
    if (
        not candidate
        or not candidate.isascii()
        or len(candidate) > MAX_EMAIL_LENGTH
        or candidate.count("@") != 1
    ):
        raise EmailValidationError("Email address is invalid.")

    local_part, domain = candidate.rsplit("@", maxsplit=1)
    domain_labels = domain.split(".")
    if (
        not local_part
        or len(local_part) > MAX_EMAIL_LOCAL_PART_LENGTH
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or _EMAIL_LOCAL_PART_PATTERN.fullmatch(local_part) is None
        or len(domain_labels) < 2
        or any(_EMAIL_DOMAIN_LABEL_PATTERN.fullmatch(label) is None for label in domain_labels)
    ):
        raise EmailValidationError("Email address is invalid.")

    return f"{local_part.casefold()}@{domain.casefold()}"


def _postgres_sqlstate(error: IntegrityError) -> str | None:
    current: BaseException | None = error.orig
    while current is not None:
        for attribute in ("sqlstate", "pgcode"):
            value = getattr(current, attribute, None)
            if isinstance(value, str):
                return value
        current = current.__cause__
    return None


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Authentication timestamps must be timezone-aware.")
    return value.astimezone(UTC)


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    """Stage a least-privilege USER registration and flush it without committing."""
    canonical_email = canonicalize_email(email)
    password_hash = hash_password(password)
    user = User(
        email=canonical_email,
        password_hash=password_hash,
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        if _postgres_sqlstate(error) == POSTGRES_UNIQUE_VIOLATION:
            raise AccountRegistrationError("Account registration failed.") from None
        raise
    return user


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
    *,
    now: datetime | None = None,
) -> User:
    """Verify credentials and stage last-login metadata without issuing a session."""
    try:
        canonical_email = canonicalize_email(email)
    except EmailValidationError:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise AuthenticationError("Invalid email or password.") from None

    user = await session.scalar(select(User).where(User.email == canonical_email))
    password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, password_hash)
    if user is None or not password_matches or not user.is_active or user.deleted_at is not None:
        raise AuthenticationError("Invalid email or password.")

    user.last_login = _utc_now(now)
    await session.flush()
    return user


def verify_user_role(user: User, required_role: UserRole) -> User:
    """Authorize from current persisted state, never from a client-supplied role."""
    if not user.is_active or user.deleted_at is not None or user.role is not required_role:
        raise RoleVerificationError("Insufficient permissions.")
    return user
