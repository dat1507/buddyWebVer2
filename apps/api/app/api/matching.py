"""Private matching recommendation and invitation APIs."""

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    require_auth,
    require_matching_eligibility,
    require_session_csrf,
    require_verified_buddy_capability,
)
from app.core.database import get_database_session
from app.core.rate_limits import check_user_rate_limit
from app.models import User
from app.schemas.matching import (
    IncomingInvitationListResponse,
    InvitationAcceptResponse,
    InvitationCreateRequest,
    InvitationCreateResponse,
    MatchingRecommendationListResponse,
    SentInvitationListResponse,
)
from app.schemas.profile_catalog import CatalogLocale
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.csrf import CsrfTokenClaims
from app.services.invitation_acceptance import (
    InvitationAcceptError,
    InvitationAcceptReason,
    accept_matching_invitation,
)
from app.services.invitation_reads import (
    DEFAULT_INVITATION_PAGE_SIZE,
    MAX_INVITATION_PAGE_SIZE,
    InvitationReadStateError,
    list_incoming_invitations,
    list_sent_invitations,
)
from app.services.invitation_sending import (
    InvitationSendError,
    InvitationSendReason,
    send_matching_invitation,
)
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


_INVITATION_VALIDATION_REASONS: Final = frozenset(
    {
        InvitationSendReason.MESSAGE_TOO_MANY_WORDS,
        InvitationSendReason.MESSAGE_TOO_MANY_CODE_POINTS,
        InvitationSendReason.SELF_NOT_ALLOWED,
    }
)


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


@router.get(
    "/invitations/incoming",
    response_model=IncomingInvitationListResponse,
)
async def read_incoming_invitations(
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_INVITATION_PAGE_SIZE),
    ] = DEFAULT_INVITATION_PAGE_SIZE,
) -> IncomingInvitationListResponse:
    """Return the current verified USER's effective PENDING incoming page."""
    try:
        result = await list_incoming_invitations(
            session,
            current,
            locale=locale,
            page=page,
            page_size=page_size,
            reference_week_start=current_reference_week_start(),
        )
    except InvitationReadStateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitations changed. Refresh and try again.",
            headers=_NO_STORE_HEADERS,
        ) from None
    _mark_private(response)
    return result


@router.get(
    "/invitations/sent",
    response_model=SentInvitationListResponse,
)
async def read_sent_invitations(
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_INVITATION_PAGE_SIZE),
    ] = DEFAULT_INVITATION_PAGE_SIZE,
) -> SentInvitationListResponse:
    """Return the current verified USER's visible sent invitation page."""
    try:
        result = await list_sent_invitations(
            session,
            current,
            locale=locale,
            page=page,
            page_size=page_size,
            reference_week_start=current_reference_week_start(),
        )
    except InvitationReadStateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitations changed. Refresh and try again.",
            headers=_NO_STORE_HEADERS,
        ) from None
    _mark_private(response)
    return result


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_matching_invitation(
    payload: InvitationCreateRequest,
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(require_auth)],
    current: Annotated[
        EligibleMatchingPrincipal,
        Depends(require_matching_eligibility),
    ],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> InvitationCreateResponse:
    """Atomically create one current-user-owned invitation and outbox event."""
    await check_user_rate_limit(request, current_user)
    try:
        invitation = await send_matching_invitation(
            session,
            current,
            recipient_profile_id=payload.recipient_profile_id,
            message=payload.message,
        )
        result = InvitationCreateResponse.model_validate(invitation)
        await session.commit()
    except InvitationSendError as error:
        await session.rollback()
        status_code = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if error.reason in _INVITATION_VALIDATION_REASONS
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(
            status_code=status_code,
            detail=error.reason.value,
            headers=_NO_STORE_HEADERS,
        ) from None
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return result


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=InvitationAcceptResponse,
)
async def accept_invitation(
    invitation_id: UUID,
    response: Response,
    current: Annotated[
        VerifiedBuddyPrincipal,
        Depends(require_verified_buddy_capability),
    ],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> InvitationAcceptResponse:
    """Atomically accept one current-recipient invitation and create its relationship."""
    try:
        accepted = await accept_matching_invitation(
            session,
            current,
            invitation_id=invitation_id,
        )
        result = InvitationAcceptResponse.model_validate(accepted)
        await session.commit()
    except InvitationAcceptError as error:
        await session.rollback()
        status_code = (
            status.HTTP_404_NOT_FOUND
            if error.reason is InvitationAcceptReason.NOT_FOUND
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(
            status_code=status_code,
            detail=error.reason.value,
            headers=_NO_STORE_HEADERS,
        ) from None
    except Exception:
        await session.rollback()
        raise
    _mark_private(response)
    return result
