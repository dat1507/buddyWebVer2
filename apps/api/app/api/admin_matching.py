"""ADMIN-only, read-only matching monitoring endpoints."""

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.core.database import get_database_session
from app.models import StudentType, User, UserRole
from app.schemas.admin_matching import (
    AdminMatchingParticipantDetail,
    AdminMatchingParticipantListResponse,
    AdminMatchingStats,
)
from app.schemas.profile_catalog import CatalogLocale
from app.services.admin_matching import (
    DEFAULT_ADMIN_MATCHING_PAGE_SIZE,
    MAX_ADMIN_MATCHING_PAGE_SIZE,
    get_admin_matching_participant_detail,
    get_admin_matching_stats,
    list_admin_matching_participants,
)
from app.services.audit_logs import record_audit_log

_NO_STORE_HEADERS: Final = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(
    prefix="/api/admin/matching",
    tags=["admin-matching"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "An ADMIN session is required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


@router.get("/stats", response_model=AdminMatchingStats)
async def read_admin_matching_stats(
    response: Response,
    _current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminMatchingStats:
    """Return aggregate matching state without participant or communication data."""
    result = await get_admin_matching_stats(session)
    _mark_private(response)
    return result


@router.get("/participants", response_model=AdminMatchingParticipantListResponse)
async def read_admin_matching_participants(
    response: Response,
    _current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_ADMIN_MATCHING_PAGE_SIZE),
    ] = DEFAULT_ADMIN_MATCHING_PAGE_SIZE,
    student_type: Annotated[StudentType | None, Query()] = None,
    verified: Annotated[bool | None, Query()] = None,
    zero_buddies_only: Annotated[bool, Query()] = False,
) -> AdminMatchingParticipantListResponse:
    """Return one deterministic safe participant page with ACTIVE Buddy counts."""
    result = await list_admin_matching_participants(
        session,
        page=page,
        page_size=page_size,
        student_type=student_type,
        verified=verified,
        zero_buddies_only=zero_buddies_only,
    )
    _mark_private(response)
    return result


@router.get(
    "/participants/{profile_id}",
    response_model=AdminMatchingParticipantDetail,
)
async def read_admin_matching_participant_detail(
    profile_id: UUID,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    locale: Annotated[CatalogLocale, Query()] = "en",
) -> AdminMatchingParticipantDetail:
    """Read one audited matching-safe participant profile without account identity."""
    try:
        detail = await get_admin_matching_participant_detail(
            session,
            profile_id=profile_id,
            locale=locale,
        )
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matching participant not found.",
                headers=_NO_STORE_HEADERS,
            )
        await record_audit_log(
            session,
            current_admin,
            action="matching.participant_admin_read",
            resource_type="student_profile",
            resource_id=profile_id,
        )
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return detail
