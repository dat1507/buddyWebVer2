"""Authenticated localized catalogs and own-profile relation endpoints."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, require_role, require_session_csrf
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.profile_catalog import (
    CatalogLocale,
    InterestCatalogItem,
    InterestCatalogResponse,
    LanguageCatalogItem,
    LanguageCatalogResponse,
    ProfileInterestSelectionResponse,
    ProfileInterestUpdate,
    ProfileLanguageSelectionResponse,
    ProfileLanguageUpdate,
)
from app.services.csrf import CsrfTokenClaims
from app.services.profile_catalogs import (
    list_active_interests,
    list_active_languages,
    replace_own_interests,
    replace_own_languages,
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


@router.put("/api/profile/interests", response_model=ProfileInterestSelectionResponse)
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
    )


@router.put("/api/profile/languages", response_model=ProfileLanguageSelectionResponse)
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
    )
