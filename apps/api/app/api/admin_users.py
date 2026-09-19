"""ADMIN-only, read-only user/profile inspection endpoints."""

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.core.database import get_database_session
from app.models import User, UserRole
from app.schemas.admin_user import AdminUserDetail, AdminUserListResponse
from app.services.admin_users import get_admin_user_detail, list_admin_users
from app.services.audit_logs import record_audit_log

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin-users"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "An ADMIN session is required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


@router.get("", response_model=AdminUserListResponse)
async def read_admin_users(
    response: Response,
    _current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> AdminUserListResponse:
    """List non-deleted student accounts through a bounded projection."""
    result = await list_admin_users(
        session,
        page=page,
        page_size=page_size,
        search=search,
    )
    _mark_private(response)
    return result


@router.get("/{user_id}", response_model=AdminUserDetail)
async def read_admin_user_detail(
    user_id: UUID,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminUserDetail:
    """Read one coordinator-facing profile projection and persist access attribution."""
    try:
        detail = await get_admin_user_detail(session, user_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
                headers=_NO_STORE_HEADERS,
            )
        await record_audit_log(
            session,
            current_admin,
            action="profile.admin_read",
            resource_type="student_profile",
            resource_id=user_id,
        )
        await session.commit()
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        raise

    _mark_private(response)
    return detail
