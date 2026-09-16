"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import (
    AuthConfigurationError,
    DatabaseConfigurationError,
    get_cors_settings,
)
from app.core.database import dispose_database_engine

CORS_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOWED_HEADERS = ("Accept", "Content-Type", "X-CSRF-Token")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Release database resources when the API process stops."""
    yield
    await dispose_database_engine()


app = FastAPI(
    title="VGU Buddy API",
    description="Backend API for the VGU Student Companion Platform.",
    version="0.1.0",
    lifespan=lifespan,
)

cors_settings = get_cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_settings.allowed_origins),
    allow_credentials=True,
    allow_methods=list(CORS_ALLOWED_METHODS),
    allow_headers=list(CORS_ALLOWED_HEADERS),
)

app.include_router(health_router)
app.include_router(auth_router)


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
    )
