"""JWT creation, validation, refresh rotation, and auth-cookie primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final, Literal, cast
from uuid import UUID, uuid4

import jwt
from fastapi import Response

from app.core.config import AuthTokenSettings
from app.models import UserRole

JWT_ALGORITHM: Final = "HS256"
JWT_ISSUER: Final = "vgu-buddy-api"
JWT_AUDIENCE: Final = "vgu-buddy-web"
JWT_CLOCK_SKEW: Final = timedelta(seconds=30)
ACCESS_TOKEN_TTL: Final = timedelta(minutes=15)
REFRESH_TOKEN_TTL: Final = timedelta(days=7)

PRODUCTION_ACCESS_COOKIE_NAME: Final = "__Host-vgu_buddy_access"
PRODUCTION_REFRESH_COOKIE_NAME: Final = "__Host-vgu_buddy_refresh"
DEVELOPMENT_ACCESS_COOKIE_NAME: Final = "vgu_buddy_access_dev"
DEVELOPMENT_REFRESH_COOKIE_NAME: Final = "vgu_buddy_refresh_dev"

TokenType = Literal["access", "refresh"]


class TokenValidationError(ValueError):
    """Raised with a generic message when an auth token cannot be trusted."""


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Trusted claims extracted from a verified access token."""

    user_id: UUID
    role: UserRole
    session_id: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshTokenClaims:
    """Trusted claims extracted from a verified refresh token."""

    user_id: UUID
    session_id: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    """New access/refresh credentials and their server-side correlation identifiers."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    access_expires_at: datetime
    refresh_expires_at: datetime
    session_id: UUID
    access_token_id: UUID
    refresh_token_id: UUID


@dataclass(frozen=True, slots=True)
class RefreshTokenRotation:
    """A replacement pair that must be committed atomically against the consumed JTI."""

    consumed_token_id: UUID
    replacement: TokenPair


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Token timestamps must be timezone-aware.")
    return value.astimezone(UTC).replace(microsecond=0)


def _encode_token(
    *,
    user_id: UUID,
    session_id: UUID,
    token_id: UUID,
    token_type: TokenType,
    issued_at: datetime,
    expires_at: datetime,
    settings: AuthTokenSettings,
    role: UserRole | None = None,
) -> str:
    payload: dict[str, str | datetime] = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(token_id),
        "token_type": token_type,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
    }
    if role is not None:
        payload["role"] = role.value
    return jwt.encode(
        payload,
        settings.signing_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
        headers={"typ": "JWT"},
    )


def create_token_pair(
    user_id: UUID,
    role: UserRole,
    settings: AuthTokenSettings,
    *,
    session_id: UUID | None = None,
    now: datetime | None = None,
) -> TokenPair:
    """Create a short-lived access token and one-use refresh-token candidate."""
    issued_at = _utc_now(now)
    current_session_id = session_id or uuid4()
    access_token_id = uuid4()
    refresh_token_id = uuid4()
    access_expires_at = issued_at + ACCESS_TOKEN_TTL
    refresh_expires_at = issued_at + REFRESH_TOKEN_TTL

    return TokenPair(
        access_token=_encode_token(
            user_id=user_id,
            role=role,
            session_id=current_session_id,
            token_id=access_token_id,
            token_type="access",
            issued_at=issued_at,
            expires_at=access_expires_at,
            settings=settings,
        ),
        refresh_token=_encode_token(
            user_id=user_id,
            session_id=current_session_id,
            token_id=refresh_token_id,
            token_type="refresh",
            issued_at=issued_at,
            expires_at=refresh_expires_at,
            settings=settings,
        ),
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        session_id=current_session_id,
        access_token_id=access_token_id,
        refresh_token_id=refresh_token_id,
    )


def _decode_token(
    token: str,
    expected_type: TokenType,
    settings: AuthTokenSettings,
) -> dict[str, object]:
    required_claims = ["iss", "aud", "sub", "sid", "jti", "token_type", "iat", "nbf", "exp"]
    if expected_type == "access":
        required_claims.append("role")

    try:
        decoded = jwt.decode_complete(
            token,
            settings.signing_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            leeway=JWT_CLOCK_SKEW,
            options={
                "require": required_claims,
                "strict_aud": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_jti": True,
                "verify_nbf": True,
                "verify_signature": True,
                "verify_sub": True,
            },
        )
        header = cast(dict[str, object], decoded["header"])
        payload = cast(dict[str, object], decoded["payload"])
        if (
            header.get("alg") != JWT_ALGORITHM
            or header.get("typ") != "JWT"
            or payload["token_type"] != expected_type
        ):
            raise TokenValidationError
        return payload
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise TokenValidationError("Token is invalid or expired.") from None


def _read_uuid_claim(payload: dict[str, object], claim: str) -> UUID:
    value = payload.get(claim)
    if not isinstance(value, str):
        raise TokenValidationError
    return UUID(value)


def _read_timestamp_claim(payload: dict[str, object], claim: str) -> datetime:
    value = payload.get(claim)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TokenValidationError
    return datetime.fromtimestamp(value, tz=UTC)


def _read_common_claims(
    payload: dict[str, object], expected_ttl: timedelta
) -> tuple[UUID, UUID, UUID, datetime, datetime]:
    try:
        user_id = _read_uuid_claim(payload, "sub")
        session_id = _read_uuid_claim(payload, "sid")
        token_id = _read_uuid_claim(payload, "jti")
        issued_at = _read_timestamp_claim(payload, "iat")
        not_before = _read_timestamp_claim(payload, "nbf")
        expires_at = _read_timestamp_claim(payload, "exp")
        if not_before != issued_at or expires_at - issued_at != expected_ttl:
            raise TokenValidationError
    except (KeyError, TypeError, ValueError, OSError, OverflowError):
        raise TokenValidationError("Token is invalid or expired.") from None
    return user_id, session_id, token_id, issued_at, expires_at


def verify_access_token(token: str, settings: AuthTokenSettings) -> AccessTokenClaims:
    """Validate and return trusted claims from an access token only."""
    try:
        payload = _decode_token(token, "access", settings)
        user_id, session_id, token_id, issued_at, expires_at = _read_common_claims(
            payload, ACCESS_TOKEN_TTL
        )
        role_value = payload.get("role")
        if not isinstance(role_value, str):
            raise TokenValidationError
        role = UserRole(role_value)
    except (TokenValidationError, ValueError):
        raise TokenValidationError("Token is invalid or expired.") from None

    return AccessTokenClaims(
        user_id=user_id,
        role=role,
        session_id=session_id,
        token_id=token_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def verify_refresh_token(token: str, settings: AuthTokenSettings) -> RefreshTokenClaims:
    """Validate and return trusted claims from a refresh token only."""
    try:
        payload = _decode_token(token, "refresh", settings)
        user_id, session_id, token_id, issued_at, expires_at = _read_common_claims(
            payload, REFRESH_TOKEN_TTL
        )
    except (TokenValidationError, ValueError):
        raise TokenValidationError("Token is invalid or expired.") from None

    return RefreshTokenClaims(
        user_id=user_id,
        session_id=session_id,
        token_id=token_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def prepare_refresh_rotation(
    refresh_token: str,
    current_role: UserRole,
    settings: AuthTokenSettings,
    *,
    now: datetime | None = None,
) -> RefreshTokenRotation:
    """Verify a refresh token and prepare its same-session replacement.

    The caller must atomically compare and consume ``consumed_token_id`` in the persistent refresh
    session before exposing the replacement. A mismatch is token reuse and must revoke the session
    family; cryptographic verification alone cannot provide replay detection.
    """
    claims = verify_refresh_token(refresh_token, settings)
    replacement = create_token_pair(
        claims.user_id,
        current_role,
        settings,
        session_id=claims.session_id,
        now=now,
    )
    return RefreshTokenRotation(
        consumed_token_id=claims.token_id,
        replacement=replacement,
    )


def _cookie_names(settings: AuthTokenSettings) -> tuple[str, str]:
    if settings.secure_cookies:
        return PRODUCTION_ACCESS_COOKIE_NAME, PRODUCTION_REFRESH_COOKIE_NAME
    return DEVELOPMENT_ACCESS_COOKIE_NAME, DEVELOPMENT_REFRESH_COOKIE_NAME


def _mark_auth_response_private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def set_auth_cookies(
    response: Response,
    token_pair: TokenPair,
    settings: AuthTokenSettings,
) -> None:
    """Attach access and refresh JWTs only as hardened HttpOnly cookies."""
    access_name, refresh_name = _cookie_names(settings)
    response.set_cookie(
        access_name,
        token_pair.access_token,
        max_age=int(ACCESS_TOKEN_TTL.total_seconds()),
        expires=token_pair.access_expires_at,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        refresh_name,
        token_pair.refresh_token,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        expires=token_pair.refresh_expires_at,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    _mark_auth_response_private(response)


def clear_auth_cookies(response: Response, settings: AuthTokenSettings) -> None:
    """Expire both auth cookies with the same scope and security attributes."""
    for cookie_name in _cookie_names(settings):
        response.delete_cookie(
            cookie_name,
            path="/",
            secure=settings.secure_cookies,
            httponly=True,
            samesite="lax",
        )
    _mark_auth_response_private(response)
