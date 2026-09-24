"""Infrastructure health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database_session
from app.schemas.health import (
    DatabaseHealthResponse,
    LivenessResponse,
    ReadinessDependencies,
    ReadinessResponse,
)
from app.services.database_health import check_database
from app.services.infrastructure_health import check_infrastructure_readiness

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Report process liveness without touching external dependencies."""
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness() -> ReadinessResponse | JSONResponse:
    """Report fixed dependency states with 503 until every required service is ready."""
    report = await check_infrastructure_readiness()
    payload = ReadinessResponse(
        status="ready" if report.ready else "not_ready",
        dependencies=ReadinessDependencies(
            database=report.database,
            redis=report.redis,
            email=report.email,
            storage=report.storage,
        ),
    )
    if not report.ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(mode="json"),
        )
    return payload


@router.get("/database", response_model=DatabaseHealthResponse)
async def database_health(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DatabaseHealthResponse:
    """Report success only after a real SQL round trip."""
    try:
        healthy = await check_database(session)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        ) from exc

    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database health check failed.",
        )
    return DatabaseHealthResponse()
