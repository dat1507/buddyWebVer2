"""Infrastructure health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database_session
from app.schemas.health import DatabaseHealthResponse
from app.services.database_health import check_database

router = APIRouter(prefix="/api/health", tags=["health"])


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
