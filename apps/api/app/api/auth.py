"""Public authentication transport endpoints."""

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.core.rate_limits import AuthRateLimiter, check_user_rate_limit, login_identifier
from app.models import User
from app.schemas.auth import (
    CsrfTokenResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegistrationRequest,
    RegistrationResponse,
    SanitizedUserResponse,
)
from app.services.auth import (
    AccountRegistrationError,
    AuthenticationError,
    authenticate_user,
    register_user,
)
from app.services.csrf import (
    CsrfTokenClaims,
    create_preauth_csrf_token,
    create_session_csrf_token,
    set_csrf_cookie,
    verify_csrf_request,
)
from app.services.refresh_sessions import (
    RefreshSessionError,
    RefreshSessionRevokedError,
    create_refresh_session,
    rotate_refresh_session,
)
from app.services.tokens import (
    RefreshTokenClaims,
    TokenValidationError,
    create_token_pair,
    refresh_cookie_name,
    set_auth_cookies,
    verify_refresh_token,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={
        429: {"description": "Rate limit exceeded; see Retry-After seconds."},
        503: {"description": "Required backend configuration/storage is unavailable."},
    },
)


@dataclass(frozen=True, slots=True)
class RefreshRequestContext:
    """Cryptographically trusted refresh JWT and its session-bound CSRF context."""

    refresh_token: str = field(repr=False)
    claims: RefreshTokenClaims


def require_preauth_csrf(
    request: Request,
    settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> CsrfTokenClaims:
    """Require a trusted origin and matching signed pre-auth cookie/header token."""
    return verify_csrf_request(request, settings, expected_scope="preauth")


async def require_login_attempt(
    payload: LoginRequest,
    request: Request,
    _csrf: Annotated[CsrfTokenClaims, Depends(require_preauth_csrf)],
) -> str:
    """Check account lockout after CSRF but before opening the login database session."""
    identifier = login_identifier(payload.email)
    limiter: AuthRateLimiter = request.state.auth_rate_limiter
    await limiter.check_login(identifier)
    return identifier


def require_refresh_context(
    request: Request,
    token_settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    csrf_settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
) -> RefreshRequestContext:
    """Require one valid refresh cookie and matching session-bound CSRF evidence."""
    refresh_token = request.cookies.get(refresh_cookie_name(token_settings))
    try:
        if refresh_token is None:
            raise TokenValidationError
        claims = verify_refresh_token(refresh_token, token_settings)
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        ) from None

    verify_csrf_request(
        request,
        csrf_settings,
        expected_scope="session",
        session_id=claims.session_id,
    )
    return RefreshRequestContext(refresh_token=refresh_token, claims=claims)


@router.get("/me", response_model=SanitizedUserResponse)
async def read_current_session(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(require_auth)],
) -> SanitizedUserResponse:
    """Return the current persisted identity without credentials or profile data."""
    await check_user_rate_limit(request, current_user)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return SanitizedUserResponse.model_validate(current_user)


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


@router.post("/login", response_model=LoginResponse)
async def login_account(
    payload: LoginRequest,
    request: Request,
    response: Response,
    attempt: Annotated[str, Depends(require_login_attempt)],
    token_settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    csrf_settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LoginResponse:
    """Authenticate one account and establish its cookie-only browser session."""
    limiter: AuthRateLimiter = request.state.auth_rate_limiter
    try:
        user = await authenticate_user(session, payload.email, payload.password)
        await check_user_rate_limit(request, user)
        token_pair = create_token_pair(user.id, user.role, token_settings)
        session_csrf = create_session_csrf_token(token_pair.session_id, csrf_settings)
        await create_refresh_session(session, user, token_pair)
        await session.commit()
        await limiter.login_succeeded(attempt)
    except AuthenticationError as error:
        await session.rollback()
        await limiter.login_failed(attempt)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        ) from error
    except Exception:
        await session.rollback()
        raise

    set_auth_cookies(response, token_pair, token_settings)
    set_csrf_cookie(response, session_csrf, csrf_settings)
    return LoginResponse(
        user=SanitizedUserResponse.model_validate(user),
        csrf_token=session_csrf.value,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_session(
    request: Request,
    response: Response,
    context: Annotated[RefreshRequestContext, Depends(require_refresh_context)],
    token_settings: Annotated[AuthTokenSettings, Depends(get_auth_token_settings)],
    csrf_settings: Annotated[CsrfSettings, Depends(get_csrf_settings)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RefreshResponse:
    """Atomically rotate one refresh token and reject reuse of an older family member."""
    try:
        rotation = await rotate_refresh_session(
            session,
            context.refresh_token,
            context.claims,
            token_settings,
        )
        await check_user_rate_limit(request, rotation.user)
        session_csrf = create_session_csrf_token(
            rotation.token_pair.session_id,
            csrf_settings,
        )
        await session.commit()
    except RefreshSessionRevokedError as error:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        ) from error
    except RefreshSessionError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        ) from error
    except Exception:
        await session.rollback()
        raise

    set_auth_cookies(response, rotation.token_pair, token_settings)
    set_csrf_cookie(response, session_csrf, csrf_settings)
    return RefreshResponse(
        user=SanitizedUserResponse.model_validate(rotation.user),
        csrf_token=session_csrf.value,
    )
