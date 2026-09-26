"""Authenticated localized catalogs and own-profile relation endpoints."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, require_role, require_session_csrf
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.profile_catalog import (
    ActivityCatalogItem,
    ActivityCatalogResponse,
    CatalogLocale,
    InterestCatalogItem,
    InterestCatalogResponse,
    LanguageCatalogItem,
    LanguageCatalogResponse,
    ProfileActivitySelectionResponse,
    ProfileActivityUpdate,
    ProfileInterestSelectionResponse,
    ProfileInterestUpdate,
    ProfileLanguageSelectionResponse,
    ProfileLanguageUpdate,
    ProfilePreferenceSelectionResponse,
    ProfilePreferenceUpdate,
)
from app.services.csrf import CsrfTokenClaims
from app.services.profile_catalogs import (
    get_own_preference_snapshot,
    list_active_activities,
    list_active_interests,
    list_active_languages,
    replace_own_activities,
    replace_own_interests,
    replace_own_languages,
    replace_own_preferences,
)
from app.services.profiles import (
    ProfileAccessError,
    ProfileValidationError,
    ProfileVersionConflictError,
)

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
require_profile_user = require_role(UserRole.USER)

router = APIRouter(
    tags=["profile-catalogs"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "Insufficient permissions."},
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


@router.get("/api/interests", response_model=InterestCatalogResponse)
async def read_interest_catalog(
    response: Response,
    _current_user: Annotated[User, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
) -> InterestCatalogResponse:
    """Read the active localized interest catalog for either authenticated role."""
    interests = await list_active_interests(session)
    _mark_private(response)
    return InterestCatalogResponse(
        locale=locale,
        items=[
            InterestCatalogItem(
                id=interest.id,
                code=interest.code,
                label=interest.label_en if locale == "en" else interest.label_de,
                category=interest.category,
            )
            for interest in interests
        ],
    )


@router.get("/api/languages", response_model=LanguageCatalogResponse)
async def read_language_catalog(
    response: Response,
    _current_user: Annotated[User, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
) -> LanguageCatalogResponse:
    """Read the active localized language catalog for either authenticated role."""
    languages = await list_active_languages(session)
    _mark_private(response)
    return LanguageCatalogResponse(
        locale=locale,
        items=[
            LanguageCatalogItem(
                code=language.code,
                label=language.label_en if locale == "en" else language.label_de,
            )
            for language in languages
        ],
    )


@router.get("/api/activities", response_model=ActivityCatalogResponse)
async def read_activity_catalog(
    response: Response,
    _current_user: Annotated[User, Depends(require_auth)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
) -> ActivityCatalogResponse:
    """Read the independent active Activity catalog for either authenticated role."""
    activities = await list_active_activities(session)
    _mark_private(response)
    return ActivityCatalogResponse(
        locale=locale,
        items=[
            ActivityCatalogItem(
                id=activity.id,
                code=activity.code,
                label=activity.label_en if locale == "en" else activity.label_de,
            )
            for activity in activities
        ],
    )


@router.put(
    "/api/profile/interests",
    response_model=ProfileInterestSelectionResponse,
    response_model_exclude_defaults=True,
)
async def update_profile_interests(
    payload: ProfileInterestUpdate,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProfileInterestSelectionResponse:
    """Atomically replace only the current USER's normalized interests."""
    try:
        result = await replace_own_interests(session, current_user, payload)
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
            detail="Profile interests are invalid.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfileInterestSelectionResponse(
        version=result.version,
        interest_ids=list(result.interest_ids),
        custom_interests=list(result.custom_interests),
    )


@router.put(
    "/api/profile/languages",
    response_model=ProfileLanguageSelectionResponse,
    response_model_exclude_defaults=True,
)
async def update_profile_languages(
    payload: ProfileLanguageUpdate,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProfileLanguageSelectionResponse:
    """Atomically replace only the current USER's normalized language proficiencies."""
    try:
        result = await replace_own_languages(session, current_user, payload)
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
            detail="Profile languages are invalid.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfileLanguageSelectionResponse(
        version=result.version,
        languages=list(result.languages),
        custom_languages=list(result.custom_languages),
    )


@router.put(
    "/api/profile/activities",
    response_model=ProfileActivitySelectionResponse,
    response_model_exclude_defaults=True,
)
async def update_profile_activities(
    payload: ProfileActivityUpdate,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProfileActivitySelectionResponse:
    """Atomically replace only the current USER's predefined and custom Activities."""
    try:
        result = await replace_own_activities(session, current_user, payload)
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
            detail="Profile activities are invalid.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfileActivitySelectionResponse(
        version=result.version,
        activity_ids=list(result.activity_ids),
        custom_activities=list(result.custom_activities),
    )


@router.get("/api/profile/preferences", response_model=ProfilePreferenceSelectionResponse)
async def read_profile_preferences(
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProfilePreferenceSelectionResponse:
    """Read all owner preference namespaces without exposing internal identity keys."""
    try:
        result = await get_own_preference_snapshot(session, current_user)
        await session.commit()
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfilePreferenceSelectionResponse(
        version=result.version,
        interest_ids=list(result.interest_ids),
        custom_interests=list(result.custom_interests),
        languages=list(result.languages),
        custom_languages=list(result.custom_languages),
        activity_ids=list(result.activity_ids),
        custom_activities=list(result.custom_activities),
    )


@router.put("/api/profile/preferences", response_model=ProfilePreferenceSelectionResponse)
async def update_profile_preferences(
    payload: ProfilePreferenceUpdate,
    response: Response,
    current_user: Annotated[User, Depends(require_profile_user)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProfilePreferenceSelectionResponse:
    """Replace all owner preference groups under one optimistic profile version."""
    try:
        result = await replace_own_preferences(session, current_user, payload)
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
            detail="Profile preferences are invalid.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except ProfileAccessError as error:
        await session.rollback()
        raise _profile_access_denied() from error
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return ProfilePreferenceSelectionResponse(
        version=result.version,
        interest_ids=list(result.interest_ids),
        custom_interests=list(result.custom_interests),
        languages=list(result.languages),
        custom_languages=list(result.custom_languages),
        activity_ids=list(result.activity_ids),
        custom_activities=list(result.custom_activities),
    )
