"""Authentication transport bootstrap endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.config import CsrfSettings, get_csrf_settings
from app.schemas.auth import CsrfTokenResponse
from app.services.csrf import create_preauth_csrf_token, set_csrf_cookie

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/csrf", response_model=CsrfTokenResponse)
async def issue_csrf_token(
    response: Response,
    settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> CsrfTokenResponse:
    """Establish a fresh pre-auth double-submit context without server-side state."""
    token = create_preauth_csrf_token(settings)
    set_csrf_cookie(response, token, settings)
    return CsrfTokenResponse(csrf_token=token.value)
