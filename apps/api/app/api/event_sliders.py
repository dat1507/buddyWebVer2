"""Anonymous read-only Landing slider projection from canonical Events."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_image_storage_service
from app.core.database import get_database_session
from app.schemas.event import EventLocale, PublicEventSliderResponse
from app.services.event_sliders import list_public_event_sliders
from app.services.image_storage import ImageStorageService, StorageOperationError

_NO_STORE_HEADERS: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}

router = APIRouter(prefix="/api/event-sliders", tags=["event-sliders"])


@router.get("", response_model=list[PublicEventSliderResponse])
async def read_event_sliders(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    locale: Annotated[EventLocale, Query()] = "en",
) -> list[PublicEventSliderResponse]:
    """Return the bounded public projection or an empty array when no Event qualifies."""
    try:
        slides = await list_public_event_sliders(session, storage, locale=locale)
    except StorageOperationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event slider media is unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from error
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value
    return slides
