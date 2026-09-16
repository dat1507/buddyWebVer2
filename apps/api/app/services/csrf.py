"""Signed, context-bound double-submit CSRF protection primitives."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final, Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Request, Response

from app.core.config import CorsConfigurationError, CsrfSettings, normalize_http_origin
from app.services.tokens import REFRESH_TOKEN_TTL

CSRF_HEADER_NAME: Final = "X-CSRF-Token"
CSRF_TOKEN_VERSION: Final = "v1"
CSRF_CLOCK_SKEW: Final = timedelta(seconds=30)
PREAUTH_CSRF_TTL: Final = timedelta(hours=1)
SESSION_CSRF_TTL: Final = REFRESH_TOKEN_TTL
MAX_CSRF_TOKEN_LENGTH: Final = 1024
UNSAFE_HTTP_METHODS: Final = frozenset({"POST", "PUT", "PATCH", "DELETE"})

PRODUCTION_CSRF_COOKIE_NAME: Final = "__Host-vgu_buddy_csrf"
DEVELOPMENT_CSRF_COOKIE_NAME: Final = "vgu_buddy_csrf_dev"

_BASE64URL_CHARACTERS: Final = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)
_PAYLOAD_KEYS: Final = frozenset({"binding", "exp", "iat", "nonce", "scope"})

CsrfScope = Literal["preauth", "session"]


class CsrfValidationError(ValueError):
    """Raised with one generic message when CSRF evidence cannot be trusted."""


@dataclass(frozen=True, slots=True)
class CsrfToken:
    """Signed value returned in JSON and submitted in the matching cookie/header."""

    value: str = field(repr=False)
    scope: CsrfScope
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CsrfTokenClaims:
    """Trusted metadata from a verified CSRF token."""

    scope: CsrfScope
    issued_at: datetime
    expires_at: datetime


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("CSRF timestamps must be timezone-aware.")
    return value.astimezone(UTC).replace(microsecond=0)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    if not value or any(character not in _BASE64URL_CHARACTERS for character in value):
        raise CsrfValidationError
    try:
        encoded = value.encode("ascii")
        padded = encoded + (b"=" * (-len(encoded) % 4))
        return base64.b64decode(padded, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise CsrfValidationError from None


def _token_ttl(scope: CsrfScope) -> timedelta:
    return PREAUTH_CSRF_TTL if scope == "preauth" else SESSION_CSRF_TTL


def _binding_tag(signing_key: bytes, scope: CsrfScope, binding: bytes) -> bytes:
    message = b"vgu-buddy-csrf-binding-v1\0" + scope.encode("ascii") + b"\0" + binding
    return hmac.digest(signing_key, message, hashlib.sha256)


def _token_signature(signing_key: bytes, payload_segment: str) -> bytes:
    message = b"vgu-buddy-csrf-token-v1\0" + payload_segment.encode("ascii")
    return hmac.digest(signing_key, message, hashlib.sha256)


def _create_csrf_token(
    scope: CsrfScope,
    binding: bytes,
    settings: CsrfSettings,
    *,
    now: datetime | None = None,
) -> CsrfToken:
    issued_at = _utc_now(now)
    expires_at = issued_at + _token_ttl(scope)
    signing_key = settings.signing_key.get_secret_value()
    payload = {
        "binding": _base64url_encode(_binding_tag(signing_key, scope, binding)),
        "exp": int(expires_at.timestamp()),
        "iat": int(issued_at.timestamp()),
        "nonce": _base64url_encode(secrets.token_bytes(32)),
        "scope": scope,
    }
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    payload_segment = _base64url_encode(payload_bytes)
    signature_segment = _base64url_encode(_token_signature(signing_key, payload_segment))
    return CsrfToken(
        value=f"{CSRF_TOKEN_VERSION}.{payload_segment}.{signature_segment}",
        scope=scope,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def create_preauth_csrf_token(
    settings: CsrfSettings,
    *,
    now: datetime | None = None,
) -> CsrfToken:
    """Create a signed one-hour token for registration and login requests."""
    return _create_csrf_token("preauth", secrets.token_bytes(32), settings, now=now)


def create_session_csrf_token(
    session_id: UUID,
    settings: CsrfSettings,
    *,
    now: datetime | None = None,
) -> CsrfToken:
    """Create a signed token bound by HMAC to one refresh-session identifier."""
    return _create_csrf_token("session", session_id.bytes, settings, now=now)


def _invalid_csrf() -> CsrfValidationError:
    return CsrfValidationError("CSRF validation failed.")


def verify_csrf_token(
    token: str,
    settings: CsrfSettings,
    *,
    expected_scope: CsrfScope,
    session_id: UUID | None = None,
    now: datetime | None = None,
) -> CsrfTokenClaims:
    """Verify signature, scope, lifetime, nonce, and optional refresh-session binding."""
    try:
        if len(token) > MAX_CSRF_TOKEN_LENGTH:
            raise CsrfValidationError
        version, payload_segment, signature_segment = token.split(".")
        if version != CSRF_TOKEN_VERSION:
            raise CsrfValidationError

        signing_key = settings.signing_key.get_secret_value()
        supplied_signature = _base64url_decode(signature_segment)
        expected_signature = _token_signature(signing_key, payload_segment)
        if len(supplied_signature) != len(expected_signature) or not hmac.compare_digest(
            supplied_signature, expected_signature
        ):
            raise CsrfValidationError

        raw_payload = json.loads(_base64url_decode(payload_segment))
        if not isinstance(raw_payload, dict) or set(raw_payload) != _PAYLOAD_KEYS:
            raise CsrfValidationError
        payload = cast(dict[str, object], raw_payload)

        scope = payload.get("scope")
        issued_timestamp = payload.get("iat")
        expires_timestamp = payload.get("exp")
        nonce = payload.get("nonce")
        binding = payload.get("binding")
        if scope != expected_scope:
            raise CsrfValidationError
        if (
            not isinstance(issued_timestamp, int)
            or isinstance(issued_timestamp, bool)
            or not isinstance(expires_timestamp, int)
            or isinstance(expires_timestamp, bool)
            or not isinstance(nonce, str)
            or not isinstance(binding, str)
        ):
            raise CsrfValidationError

        issued_at = datetime.fromtimestamp(issued_timestamp, tz=UTC)
        expires_at = datetime.fromtimestamp(expires_timestamp, tz=UTC)
        current_time = _utc_now(now)
        if expires_at - issued_at != _token_ttl(expected_scope):
            raise CsrfValidationError
        if issued_at > current_time + CSRF_CLOCK_SKEW:
            raise CsrfValidationError
        if expires_at <= current_time - CSRF_CLOCK_SKEW:
            raise CsrfValidationError
        if len(_base64url_decode(nonce)) != 32:
            raise CsrfValidationError

        supplied_binding = _base64url_decode(binding)
        if len(supplied_binding) != hashlib.sha256().digest_size:
            raise CsrfValidationError
        if expected_scope == "session":
            if session_id is None:
                raise CsrfValidationError
            expected_binding = _binding_tag(signing_key, "session", session_id.bytes)
            if not hmac.compare_digest(supplied_binding, expected_binding):
                raise CsrfValidationError
        elif session_id is not None:
            raise CsrfValidationError
    except (
        CsrfValidationError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        OSError,
        OverflowError,
    ):
        raise _invalid_csrf() from None

    return CsrfTokenClaims(
        scope=expected_scope,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _origin_from_referer(referer: str) -> str:
    parsed = urlsplit(referer)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise CsrfValidationError
    if parsed.username is not None or parsed.password is not None:
        raise CsrfValidationError
    try:
        port = parsed.port
    except ValueError:
        raise CsrfValidationError from None

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default_port = 80 if parsed.scheme == "http" else 443
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{parsed.scheme}://{host}{port_suffix}"


def verify_request_origin(request: Request, settings: CsrfSettings) -> str:
    """Require one exact allowlisted Origin, falling back to Referer only when absent."""
    try:
        origin_values = request.headers.getlist("origin")
        if origin_values:
            if len(origin_values) != 1:
                raise CsrfValidationError
            source_origin = normalize_http_origin(origin_values[0])
        else:
            referer_values = request.headers.getlist("referer")
            if len(referer_values) != 1:
                raise CsrfValidationError
            source_origin = _origin_from_referer(referer_values[0])
        if source_origin not in settings.trusted_origins:
            raise CsrfValidationError
        return source_origin
    except (CorsConfigurationError, CsrfValidationError, ValueError):
        raise _invalid_csrf() from None


def csrf_cookie_name(settings: CsrfSettings) -> str:
    """Return the environment-appropriate host-only CSRF cookie name."""
    if settings.secure_cookies:
        return PRODUCTION_CSRF_COOKIE_NAME
    return DEVELOPMENT_CSRF_COOKIE_NAME


def verify_csrf_request(
    request: Request,
    settings: CsrfSettings,
    *,
    expected_scope: CsrfScope,
    session_id: UUID | None = None,
    now: datetime | None = None,
) -> CsrfTokenClaims:
    """Validate an unsafe request's origin and signed cookie/header double submission."""
    try:
        if request.method.upper() not in UNSAFE_HTTP_METHODS:
            raise CsrfValidationError
        verify_request_origin(request, settings)

        header_values = request.headers.getlist(CSRF_HEADER_NAME)
        if len(header_values) != 1:
            raise CsrfValidationError
        header_token = header_values[0]
        cookie_token = request.cookies.get(csrf_cookie_name(settings))
        if (
            cookie_token is None
            or len(header_token) > MAX_CSRF_TOKEN_LENGTH
            or len(cookie_token) != len(header_token)
            or not hmac.compare_digest(cookie_token, header_token)
        ):
            raise CsrfValidationError
        return verify_csrf_token(
            header_token,
            settings,
            expected_scope=expected_scope,
            session_id=session_id,
            now=now,
        )
    except (CsrfValidationError, TypeError, ValueError):
        raise _invalid_csrf() from None


def _mark_response_private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def set_csrf_cookie(
    response: Response,
    token: CsrfToken,
    settings: CsrfSettings,
) -> None:
    """Set the signed token in a host-only HttpOnly double-submit cookie."""
    response.set_cookie(
        csrf_cookie_name(settings),
        token.value,
        max_age=int((token.expires_at - token.issued_at).total_seconds()),
        expires=token.expires_at,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    _mark_response_private(response)


def clear_csrf_cookie(response: Response, settings: CsrfSettings) -> None:
    """Expire the CSRF cookie using exactly the attributes with which it was set."""
    response.delete_cookie(
        csrf_cookie_name(settings),
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    _mark_response_private(response)
