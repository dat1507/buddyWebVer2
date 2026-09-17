"""Reusable authentication dependencies for protected API routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Final

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.models import User, UserRole
from app.services.auth import RoleVerificationError, verify_user_role
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


async def require_auth(
    claims: Annotated[AccessTokenClaims, Depends(require_access_claims)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> User:
    """Return the active persisted User for a verified access-cookie subject.

    The signed role claim is intentionally not an authorization source. Callers receive the
    current database User so a later role dependency cannot restore privileges from a stale JWT.
    """
    user = await session.scalar(
        select(User).where(
            User.id == claims.user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if user is None or not user.is_active or user.deleted_at is not None:
        raise _authentication_required()
    return user


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
