"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.profile import router as profile_router
from app.core.config import (
    AuthConfigurationError,
    DatabaseConfigurationError,
    get_cors_settings,
)
from app.core.database import dispose_database_engine
from app.core.rate_limits import AuthRateLimitMiddleware, close_auth_rate_limiter
from app.services.csrf import CsrfValidationError

CORS_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOWED_HEADERS = ("Accept", "Content-Type", "X-CSRF-Token")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Release database resources when the API process stops."""
    yield
    await dispose_database_engine()
    close_auth_rate_limiter()


app = FastAPI(
    title="VGU Buddy API",
    description="Backend API for the VGU Student Companion Platform.",
    version="0.1.0",
    lifespan=lifespan,
)

cors_settings = get_cors_settings()
app.add_middleware(AuthRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_settings.allowed_origins),
    allow_credentials=True,
    allow_methods=list(CORS_ALLOWED_METHODS),
    allow_headers=list(CORS_ALLOWED_HEADERS),
    expose_headers=["Retry-After"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(profile_router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    """Return field diagnostics without reflecting submitted secrets or other raw inputs."""
    safe_errors = [
        {key: value for key, value in item.items() if key in {"type", "loc", "msg"}}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": safe_errors},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@app.exception_handler(CsrfValidationError)
async def handle_csrf_validation_error(
    _request: Request, _error: CsrfValidationError
) -> JSONResponse:
    """Return one generic authorization failure for every invalid CSRF condition."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "CSRF validation failed."},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@app.exception_handler(DatabaseConfigurationError)
async def handle_database_configuration_error(
    _request: Request, _error: DatabaseConfigurationError
) -> JSONResponse:
    """Return a sanitized availability error without credential details."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is not configured."},
    )


@app.exception_handler(AuthConfigurationError)
async def handle_auth_configuration_error(
    _request: Request, _error: AuthConfigurationError
) -> JSONResponse:
    """Fail closed without returning authentication configuration details."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Authentication is not configured."},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
