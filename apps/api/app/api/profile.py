"""Authenticated own-profile transport endpoints."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role, require_session_csrf
from app.core.database import get_database_session
from app.models import StudentProfile, User, UserRole
from app.schemas import OwnProfileResponse, ProfilePhotoResponse, ProfileUpdate
from app.services.csrf import CsrfTokenClaims
from app.services.profile_photos import get_own_avatar
from app.services.profiles import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
    get_or_create_own_profile,
    update_own_profile,
)

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
require_profile_user = require_role(UserRole.USER)

router = APIRouter(
    prefix="/api/profile",
    tags=["profile"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "A USER session is required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


def _profile_access_denied() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions.",
        headers=_NO_STORE_HEADERS,
    )


async def _own_profile_response(
    session: AsyncSession,
    current_user: User,
    profile: StudentProfile,
) -> OwnProfileResponse:
    response = OwnProfileResponse.model_validate(profile)
    avatar = await get_own_avatar(session, current_user)
    if avatar is None:
        return response
    return response.model_copy(update={"avatar": ProfilePhotoResponse.model_validate(avatar)})


@router.get("", response_model=OwnProfileResponse)
async def read_own_profile(
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OwnProfileResponse:
    """Read the current USER's profile, creating one resumable draft when absent."""
    try:
        profile = await get_or_create_own_profile(session, current_user)
        result = await _own_profile_response(session, current_user, profile)
        await session.commit()
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return result


@router.put("", response_model=OwnProfileResponse)
async def replace_own_profile_fields(
    payload: ProfileUpdate,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OwnProfileResponse:
    """Apply one CSRF-protected, optimistic partial update to the current USER's profile."""
    try:
        profile = await update_own_profile(session, current_user, payload)
        result = await _own_profile_response(session, current_user, profile)
        await session.commit()
    except ProfileVersionConflictError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile version is stale.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileValidationError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Profile update is invalid.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return result
