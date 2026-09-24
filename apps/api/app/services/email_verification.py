"""Cryptographic issue and one-use consumption for email-verification tokens."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailVerificationToken, User

EMAIL_VERIFICATION_TOKEN_BYTES: Final = 32
EMAIL_VERIFICATION_TOKEN_TTL: Final = timedelta(minutes=15)
_ENCODED_TOKEN_LENGTH: Final = 43
_DIGEST_PURPOSE: Final = b"vgu-buddy-email-verification-token-v1\0"
_BASE64URL_CHARACTERS: Final = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)
_INVALID_TOKEN_MESSAGE: Final = "Verification token is invalid or expired."

Clock = Callable[[], datetime]
RandomBytes = Callable[[int], bytes]


class EmailVerificationTokenError(ValueError):
    """Raised generically when a verification token or its owner cannot be trusted."""


@dataclass(frozen=True, slots=True)
class IssuedEmailVerificationToken:
    """Plaintext returned once to the caller and intentionally excluded from repr."""

    token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ConsumedEmailVerificationToken:
    """Non-secret identity snapshot produced by one atomic token consumption."""

    user_id: UUID
    email_snapshot: str
    consumed_at: datetime


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Email-verification timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _invalid_token() -> EmailVerificationTokenError:
    return EmailVerificationTokenError(_INVALID_TOKEN_MESSAGE)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_token(token: str) -> bytes:
    if (
        not isinstance(token, str)
        or len(token) != _ENCODED_TOKEN_LENGTH
        or any(character not in _BASE64URL_CHARACTERS for character in token)
    ):
        raise _invalid_token()
    try:
        encoded = token.encode("ascii")
        decoded = base64.b64decode(
            encoded + (b"=" * (-len(encoded) % 4)),
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise _invalid_token() from None
    if len(decoded) != EMAIL_VERIFICATION_TOKEN_BYTES or _base64url_encode(decoded) != token:
        raise _invalid_token()
    return decoded


def _digest_random_bytes(random_bytes: bytes) -> bytes:
    return hashlib.sha256(_DIGEST_PURPOSE + random_bytes).digest()


def digest_email_verification_token(token: str) -> bytes:
    """Return the purpose-separated digest for one canonical plaintext token."""
    return _digest_random_bytes(_decode_token(token))


async def _lock_current_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _invalid_token()
    return user


async def issue_email_verification_token(
    session: AsyncSession,
    user_id: UUID,
    *,
    clock: Clock = _system_utc_now,
    random_bytes: RandomBytes = secrets.token_bytes,
) -> IssuedEmailVerificationToken:
    """Stage one newest token while superseding the owner's prior active token.

    The caller owns the surrounding transaction and must commit before exposing the plaintext.
    """
    user = await _lock_current_user(session, user_id)
    current_token = await session.scalar(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.consumed_at.is_(None),
            EmailVerificationToken.superseded_at.is_(None),
            EmailVerificationToken.deleted_at.is_(None),
        )
        .with_for_update()
    )
    entropy = random_bytes(EMAIL_VERIFICATION_TOKEN_BYTES)
    if not isinstance(entropy, bytes) or len(entropy) != EMAIL_VERIFICATION_TOKEN_BYTES:
        raise ValueError("Random source must return exactly 32 bytes.")
    current_time = _utc_now(clock)
    if current_token is not None:
        current_token.superseded_at = current_time

    plaintext_token = _base64url_encode(entropy)
    expires_at = current_time + EMAIL_VERIFICATION_TOKEN_TTL
    stored_token = EmailVerificationToken(
        user_id=user.id,
        token_digest=_digest_random_bytes(entropy),
        email_snapshot=user.email,
        expires_at=expires_at,
        created_at=current_time,
        updated_at=current_time,
    )
    session.add(stored_token)
    await session.flush()
    return IssuedEmailVerificationToken(token=plaintext_token, expires_at=expires_at)


async def consume_email_verification_token(
    session: AsyncSession,
    token: str,
    *,
    clock: Clock = _system_utc_now,
) -> ConsumedEmailVerificationToken:
    """Validate and atomically stage one-use consumption without verifying the User itself.

    Lock ordering is User then token for both issue and consume. The unlocked first lookup reveals
    only the owner identifier needed to preserve that ordering; all state is re-read under locks.
    """
    token_digest = digest_email_verification_token(token)
    candidate = await session.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_digest == token_digest
        )
    )
    if candidate is None:
        raise _invalid_token()

    user = await _lock_current_user(session, candidate.user_id)
    stored_token = await session.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.id == candidate.id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    current_time = _utc_now(clock)
    if (
        stored_token is None
        or not hmac.compare_digest(bytes(stored_token.token_digest), token_digest)
        or stored_token.user_id != user.id
        or stored_token.deleted_at is not None
        or stored_token.consumed_at is not None
        or stored_token.superseded_at is not None
        or stored_token.expires_at <= current_time
        or stored_token.email_snapshot != user.email
    ):
        raise _invalid_token()

    stored_token.consumed_at = current_time
    await session.flush()
    return ConsumedEmailVerificationToken(
        user_id=user.id,
        email_snapshot=stored_token.email_snapshot,
        consumed_at=current_time,
    )
