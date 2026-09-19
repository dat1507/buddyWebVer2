"""Public-safe profile-photo metadata and short-lived delivery contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import ProfilePhotoProcessingStatus


class ProfilePhotoResponse(BaseModel):
    """Photo metadata without a bucket, object key, or durable delivery URL."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    mime_type: str
    byte_size: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    processing_status: ProfilePhotoProcessingStatus
    created_at: datetime


class ProfilePhotoUrlResponse(BaseModel):
    """An authorized, short-lived URL that is never persisted by the application."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    url: str
    expires_in: int = Field(ge=1, le=300)
