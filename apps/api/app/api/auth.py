"""Public authentication transport endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CsrfSettings, get_csrf_settings
from app.core.database import get_database_session
from app.schemas.auth import CsrfTokenResponse, RegistrationRequest, RegistrationResponse
from app.services.auth import AccountRegistrationError, register_user
from app.services.csrf import (
    CsrfTokenClaims,
    create_preauth_csrf_token,
    set_csrf_cookie,
    verify_csrf_request,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def require_preauth_csrf(
    request: Request,
    settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> CsrfTokenClaims:
    """Require a trusted origin and matching signed pre-auth cookie/header token."""
    return verify_csrf_request(request, settings, expected_scope="preauth")


@router.get("/csrf", response_model=CsrfTokenResponse)
async def issue_csrf_token(
    response: Response,
    settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> CsrfTokenResponse:
    """Establish a fresh pre-auth double-submit context without server-side state."""
    token = create_preauth_csrf_token(settings)
    set_csrf_cookie(response, token, settings)
    return CsrfTokenResponse(csrf_token=token.value)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_account(
    payload: RegistrationRequest,
    response: Response,
    _csrf: Annotated[CsrfTokenClaims, Depends(require_preauth_csrf)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RegistrationResponse:
    """Register one least-privilege USER without creating an authenticated session."""
    try:
        await register_user(session, payload.email, payload.password)
        await session.commit()
    except AccountRegistrationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account registration failed.",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        ) from error
    except Exception:
        await session.rollback()
        raise

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return RegistrationResponse()
