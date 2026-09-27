"""Read-only REC-003 ranked recommendation API."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth, require_matching_eligibility
from app.core.database import get_database_session
from app.core.rate_limits import check_user_rate_limit
from app.models import User
from app.schemas.matching import MatchingRecommendationListResponse
from app.schemas.profile_catalog import CatalogLocale
from app.services.matching_eligibility import EligibleMatchingPrincipal
from app.services.matching_recommendations import (
    DEFAULT_RECOMMENDATION_PAGE_SIZE,
    MAX_RECOMMENDATION_PAGE_SIZE,
    MatchingRecommendationCapacityError,
    MatchingRecommendationStateError,
    current_reference_week_start,
    list_ranked_matching_recommendations,
)

_NO_STORE_HEADERS: Final = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}

router = APIRouter(
    prefix="/api/matching",
    tags=["matching"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "Verified matching eligibility is required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


@router.get(
    "/recommendations",
    response_model=MatchingRecommendationListResponse,
)
async def read_matching_recommendations(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(require_auth)],
    current: Annotated[
        EligibleMatchingPrincipal,
        Depends(require_matching_eligibility),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_RECOMMENDATION_PAGE_SIZE),
    ] = DEFAULT_RECOMMENDATION_PAGE_SIZE,
) -> MatchingRecommendationListResponse:
    """Return one current-user-specific ranking page without any mutation."""
    await check_user_rate_limit(request, current_user)
    try:
        result = await list_ranked_matching_recommendations(
            session,
            current,
            locale=locale,
            page=page,
            page_size=page_size,
            reference_week_start=current_reference_week_start(),
        )
    except MatchingRecommendationStateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Matching eligibility changed. Refresh and try again.",
            headers=_NO_STORE_HEADERS,
        ) from None
    except MatchingRecommendationCapacityError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations are temporarily unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from None
    _mark_private(response)
    return result
