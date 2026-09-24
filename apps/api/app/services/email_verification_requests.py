"""EMAIL-002 request orchestration and sealed verification-email template."""

from __future__ import annotations

import base64
import binascii
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from urllib.parse import quote
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmailVerificationDeliverySettings
from app.models import User, UserRole
from app.services.email_outbox import (
    EmailTemplateError,
    RenderedEmailContent,
    enqueue_transactional_email,
)
from app.services.email_verification import (
    digest_email_verification_token,
    issue_email_verification_token,
)

EMAIL_VERIFICATION_REQUESTED: Final = "EMAIL_VERIFICATION_REQUESTED"
_PAYLOAD_VERSION: Final = 1
_NONCE_BYTES: Final = 12
_SEALING_AAD: Final = b"vgu-buddy-email-verification-delivery-v1"

Clock = Callable[[], datetime]
RandomBytes = Callable[[int], bytes]


class EmailVerificationRequestError(ValueError):
    """Sanitized failure when the current account cannot request verification."""


@dataclass(frozen=True, slots=True)
class EmailVerificationRequestResult:
    """Non-secret request result; the public response remains deliberately generic."""

    created: bool


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or not value:
        raise EmailTemplateError("verification_payload_invalid")
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(
            encoded + (b"=" * (-len(encoded) % 4)),
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise EmailTemplateError("verification_payload_invalid") from None
    if _base64url_encode(decoded) != value:
        raise EmailTemplateError("verification_payload_invalid")
    return decoded


def seal_email_verification_token(
    token: str,
    expires_at: datetime,
    settings: EmailVerificationDeliverySettings,
    *,
    random_bytes: RandomBytes = secrets.token_bytes,
) -> dict[str, object]:
    """Seal plaintext for durable retry without persisting a usable token."""
    digest_email_verification_token(token)
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("Email-verification expiry must be timezone-aware.")
    nonce = random_bytes(_NONCE_BYTES)
    if not isinstance(nonce, bytes) or len(nonce) != _NONCE_BYTES:
        raise ValueError("Random source must return exactly 12 bytes.")
    ciphertext = AESGCM(settings.sealing_key.get_secret_value()).encrypt(
        nonce,
        token.encode("ascii"),
        _SEALING_AAD,
    )
    return {
        "version": _PAYLOAD_VERSION,
        "nonce": _base64url_encode(nonce),
        "sealed_value": _base64url_encode(ciphertext),
        "expires_at": expires_at.astimezone(UTC).isoformat(),
    }


class EmailVerificationTemplate:
    """Server-owned plain-text renderer for sealed verification links."""

    event_type = EMAIL_VERIFICATION_REQUESTED

    def __init__(
        self,
        settings: EmailVerificationDeliverySettings,
        *,
        clock: Clock = _system_utc_now,
    ) -> None:
        self._settings = settings
        self._clock = clock

    def render(self, payload: Mapping[str, object]) -> RenderedEmailContent:
        if set(payload) != {"version", "nonce", "sealed_value", "expires_at"}:
            raise EmailTemplateError("verification_payload_invalid")
        if payload["version"] != _PAYLOAD_VERSION:
            raise EmailTemplateError("verification_payload_invalid")
        nonce = _base64url_decode(payload["nonce"])
        ciphertext = _base64url_decode(payload["sealed_value"])
        if len(nonce) != _NONCE_BYTES:
            raise EmailTemplateError("verification_payload_invalid")
        expires_at_value = payload["expires_at"]
        if not isinstance(expires_at_value, str):
            raise EmailTemplateError("verification_payload_invalid")
        try:
            expires_at = datetime.fromisoformat(expires_at_value)
        except ValueError:
            raise EmailTemplateError("verification_payload_invalid") from None
        current_time = self._clock()
        if (
            expires_at.tzinfo is None
            or expires_at.utcoffset() is None
            or current_time.tzinfo is None
            or current_time.utcoffset() is None
            or expires_at.astimezone(UTC) <= current_time.astimezone(UTC)
        ):
            raise EmailTemplateError("verification_link_expired")
        try:
            token = AESGCM(self._settings.sealing_key.get_secret_value()).decrypt(
                nonce,
                ciphertext,
                _SEALING_AAD,
            ).decode("ascii")
            digest_email_verification_token(token)
        except Exception:
            raise EmailTemplateError("verification_payload_invalid") from None

        link = (
            f"{self._settings.public_app_base_url}/verify-email"
            f"?token={quote(token, safe='')}"
        )
        return RenderedEmailContent(
            subject="Verify your VGU Buddy email",
            text_body=(
                "Verify your email address for VGU Buddy by opening this link:\n\n"
                f"{link}\n\n"
                "This link expires 15 minutes after it was requested. "
                "If you did not request this email, you can ignore it."
            ),
        )


async def request_email_verification(
    session: AsyncSession,
    user_id: UUID,
    settings: EmailVerificationDeliverySettings,
) -> EmailVerificationRequestResult:
    """Stage one latest token and its durable email event in the caller's transaction."""
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if (
        user is None
        or user.role is not UserRole.USER
        or not user.is_active
        or user.deleted_at is not None
    ):
        raise EmailVerificationRequestError("Email verification could not be requested.")
    if user.is_current_email_verified:
        return EmailVerificationRequestResult(created=False)

    issued = await issue_email_verification_token(session, user.id)
    payload = seal_email_verification_token(issued.token, issued.expires_at, settings)
    await enqueue_transactional_email(
        session,
        event_type=EMAIL_VERIFICATION_REQUESTED,
        aggregate_id=issued.token_id,
        recipient_user_id=user.id,
        recipient_email=user.email,
        idempotency_key=f"{EMAIL_VERIFICATION_REQUESTED}/{issued.token_id}",
        payload=payload,
    )
    return EmailVerificationRequestResult(created=True)
