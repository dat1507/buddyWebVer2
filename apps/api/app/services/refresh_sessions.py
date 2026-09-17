"""Persistent refresh-session creation, rotation, and replay revocation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthTokenSettings
from app.models import RefreshSession, User
from app.services.tokens import (
    RefreshTokenClaims,
    TokenPair,
    TokenValidationError,
    prepare_refresh_rotation,
)


class RefreshSessionError(ValueError):
    """Raised generically when a refresh session cannot be trusted."""


class RefreshSessionRevokedError(RefreshSessionError):
    """Raised after staging a family revocation that the endpoint must commit."""


@dataclass(frozen=True, slots=True)
class RefreshSessionRotation:
    """Authoritative user state and replacement credentials after rotation."""

    user: User
    token_pair: TokenPair


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Refresh-session timestamps must be timezone-aware.")
    return value.astimezone(UTC).replace(microsecond=0)


def _invalid_session() -> RefreshSessionError:
    return RefreshSessionError("Session is invalid or expired.")


async def create_refresh_session(
    session: AsyncSession,
    user: User,
    token_pair: TokenPair,
) -> RefreshSession:
    """Stage the initial server-side state for a newly issued refresh family."""
    refresh_session = RefreshSession(
        id=token_pair.session_id,
        user_id=user.id,
        refresh_token_id=token_pair.refresh_token_id,
        expires_at=token_pair.refresh_expires_at,
    )
    session.add(refresh_session)
    await session.flush()
    return refresh_session


async def _stage_family_revocation(
    session: AsyncSession,
    refresh_session: RefreshSession,
    revoked_at: datetime,
) -> None:
    refresh_session.revoked_at = revoked_at
    await session.flush()


async def rotate_refresh_session(
    session: AsyncSession,
    refresh_token: str,
    claims: RefreshTokenClaims,
    settings: AuthTokenSettings,
    *,
    now: datetime | None = None,
) -> RefreshSessionRotation:
    """Atomically validate, consume, and replace one current refresh-token identifier."""
    current_time = _utc_now(now)
    refresh_session = await session.scalar(
        select(RefreshSession).where(RefreshSession.id == claims.session_id).with_for_update()
    )
    if refresh_session is None or refresh_session.deleted_at is not None:
        raise _invalid_session()
    if refresh_session.revoked_at is not None:
        raise _invalid_session()
    if refresh_session.user_id != claims.user_id:
        await _stage_family_revocation(session, refresh_session, current_time)
        raise RefreshSessionRevokedError("Session is invalid or expired.")
    if refresh_session.expires_at <= current_time:
        await _stage_family_revocation(session, refresh_session, current_time)
        raise RefreshSessionRevokedError("Session is invalid or expired.")
    if refresh_session.refresh_token_id != claims.token_id:
        await _stage_family_revocation(session, refresh_session, current_time)
        raise RefreshSessionRevokedError("Session is invalid or expired.")

    user = await session.scalar(select(User).where(User.id == claims.user_id).with_for_update())
    if user is None or not user.is_active or user.deleted_at is not None:
        await _stage_family_revocation(session, refresh_session, current_time)
        raise RefreshSessionRevokedError("Session is invalid or expired.")

    try:
        rotation = prepare_refresh_rotation(
            refresh_token,
            user.role,
            settings,
            now=current_time,
        )
    except TokenValidationError:
        raise _invalid_session() from None
    if rotation.consumed_token_id != refresh_session.refresh_token_id:
        await _stage_family_revocation(session, refresh_session, current_time)
        raise RefreshSessionRevokedError("Session is invalid or expired.")

    refresh_session.refresh_token_id = rotation.replacement.refresh_token_id
    refresh_session.expires_at = rotation.replacement.refresh_expires_at
    await session.flush()
    return RefreshSessionRotation(user=user, token_pair=rotation.replacement)
