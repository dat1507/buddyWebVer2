"""Reusable authentication dependencies for protected API routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Final, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import (
    AuthTokenSettings,
    CorsSettings,
    CsrfSettings,
    StorageSettings,
    get_auth_token_settings,
    get_cors_settings,
    get_csrf_settings,
    get_storage_settings,
)
from app.core.database import get_database_session, get_session_factory
from app.models import User, UserRole
from app.services.auth import RoleVerificationError, verify_user_role
from app.services.buddy_access import (
    BuddyCapabilityError,
    VerifiedBuddyPrincipal,
    get_verified_buddy_principal,
)
from app.services.csrf import CsrfTokenClaims, verify_csrf_request
from app.services.image_storage import ImageStorageService, SupabaseStorageTransport
from app.services.matching_eligibility import (
    EligibleMatchingPrincipal,
    get_eligible_matching_principal,
)
from app.services.tokens import (
    AccessTokenClaims,
    TokenValidationError,
    access_cookie_name,
    verify_access_token,
)

AUTHENTICATION_REQUIRED_MESSAGE: Final = "Authentication required."
AUTHORIZATION_REQUIRED_MESSAGE: Final = "Insufficient permissions."
_NO_STORE_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


def _authentication_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=AUTHENTICATION_REQUIRED_MESSAGE,
        headers=_NO_STORE_HEADERS,
    )


def _authorization_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=AUTHORIZATION_REQUIRED_MESSAGE,
        headers=_NO_STORE_HEADERS,
    )


def _buddy_capability_required(error: BuddyCapabilityError) -> HTTPException:
    detail = error.reason.value if error.reason is not None else AUTHORIZATION_REQUIRED_MESSAGE
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
        headers=_NO_STORE_HEADERS,
    )


def _websocket_policy_denied(reason: str) -> WebSocketException:
    return WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=reason)


def require_trusted_websocket_origin(
    websocket: WebSocket,
    settings: Annotated[CorsSettings, Depends(get_cors_settings)],
) -> None:
    """Reject cross-site cookie-authenticated upgrades before protected work."""
    if websocket.headers.get("origin") not in settings.allowed_origins:
        raise _websocket_policy_denied("Origin is not allowed.")


async def _load_active_user(session: AsyncSession, user_id: UUID) -> User | None:
    return cast(
        User | None,
        await session.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        ),
    )


def require_access_claims(
    request: Request,
    settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
) -> AccessTokenClaims:
    """Verify the environment-specific access cookie before opening a database session."""
    token = request.cookies.get(access_cookie_name(settings))
    try:
        if token is None:
            raise TokenValidationError
        return verify_access_token(token, settings)
    except TokenValidationError:
        raise _authentication_required() from None


def optional_access_claims(
    request: Request,
    settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
) -> AccessTokenClaims | None:
    """Return verified claims when an access cookie is present.

    Public endpoints may serve an anonymous response when the cookie is absent. A supplied but
    invalid cookie is never silently downgraded to anonymous access.
    """
    token = request.cookies.get(access_cookie_name(settings))
    if token is None:
        return None
    try:
        return verify_access_token(token, settings)
    except TokenValidationError:
        raise _authentication_required() from None


async def require_auth(
    claims: Annotated[AccessTokenClaims, Depends(require_access_claims)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> User:
    """Return the active persisted User for a verified access-cookie subject.

    The signed role claim is intentionally not an authorization source. Callers receive the
    current database User so a later role dependency cannot restore privileges from a stale JWT.
    """
    user = await _load_active_user(session, claims.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _authentication_required()
    return user


async def optional_auth(
    claims: Annotated[AccessTokenClaims | None, Depends(optional_access_claims)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> User | None:
    """Resolve an optional cookie to current persisted state for audience-aware public reads."""
    if claims is None:
        return None
    user = await _load_active_user(session, claims.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _authentication_required()
    return user


async def require_verified_buddy_capability(
    current_user: Annotated[User, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VerifiedBuddyPrincipal:
    """Authorize one HTTP Buddy/chat interaction from current persisted state."""
    try:
        return await get_verified_buddy_principal(session, current_user)
    except BuddyCapabilityError as error:
        raise _buddy_capability_required(error) from None


async def require_matching_eligibility(
    principal: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> EligibleMatchingPrincipal:
    """Require current profile completion and matching opt-in after VERIFIED authorization."""
    try:
        return await get_eligible_matching_principal(session, principal)
    except BuddyCapabilityError as error:
        raise _buddy_capability_required(error) from None


async def authenticate_verified_buddy_websocket(
    websocket: WebSocket,
    settings: AuthTokenSettings,
    session: AsyncSession,
) -> VerifiedBuddyPrincipal:
    """Revalidate one socket identity against its cookie and current database state."""
    token = websocket.cookies.get(access_cookie_name(settings))
    try:
        if token is None:
            raise TokenValidationError
        claims = verify_access_token(token, settings)
    except TokenValidationError:
        raise _websocket_policy_denied(AUTHENTICATION_REQUIRED_MESSAGE) from None

    user = await _load_active_user(session, claims.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _websocket_policy_denied(AUTHENTICATION_REQUIRED_MESSAGE)
    try:
        return await get_verified_buddy_principal(session, user)
    except BuddyCapabilityError as error:
        reason = error.reason.value if error.reason is not None else AUTHORIZATION_REQUIRED_MESSAGE
        raise _websocket_policy_denied(reason) from None


async def require_verified_buddy_websocket(
    websocket: WebSocket,
    settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> VerifiedBuddyPrincipal:
    """Authorize the reusable short-lived Buddy WebSocket dependency."""
    return await authenticate_verified_buddy_websocket(websocket, settings, session)


async def require_verified_chat_websocket(
    websocket: WebSocket,
    _trusted_origin: Annotated[None, Depends(require_trusted_websocket_origin)],
    settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
) -> VerifiedBuddyPrincipal:
    """Authorize chat without retaining a database session for the socket lifetime."""
    async with session_factory() as session:
        return await authenticate_verified_buddy_websocket(websocket, settings, session)


def require_session_csrf(
    request: Request,
    claims: Annotated[AccessTokenClaims, Depends(require_access_claims)],
    settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> CsrfTokenClaims:
    """Require trusted-origin double-submit evidence bound to the access session."""
    return verify_csrf_request(
        request,
        settings,
        expected_scope="session",
        session_id=claims.session_id,
    )


def get_image_storage_service(
    settings: Annotated[StorageSettings, Depends(get_storage_settings)],
) -> ImageStorageService:
    """Build a request-scoped service around the server-only Storage credential."""
    return ImageStorageService(SupabaseStorageTransport(settings))


def require_role(required_role: UserRole) -> Callable[..., Awaitable[User]]:
    """Build an exact-role dependency on top of the verified persisted identity.

    Routes choose ``required_role`` in server code. The role claim in the access token and any
    client-supplied role fields are deliberately excluded from this authorization decision.
    """
    if not isinstance(required_role, UserRole):
        raise TypeError("required_role must be a UserRole.")

    async def verify_required_role(
        current_user: Annotated[User, Depends(require_auth)],
    ) -> User:
        try:
            return verify_user_role(current_user, required_role)
        except RoleVerificationError:
            raise _authorization_required() from None

    return verify_required_role
