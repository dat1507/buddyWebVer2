"""Strict bounded recap input and key-free public/admin projections."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
Story = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
Alt = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Caption = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class RecapContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    related_event_id: UUID | None = None
    title_en: Title | None = None
    title_de: Title | None = None
    summary_en: Summary | None = None
    summary_de: Summary | None = None
    editorial_en: Story | None = None
    editorial_de: Story | None = None
    event_date: date | None = None


class RecapUpdate(RecapContent):
    version: int = Field(ge=1)


class RecapStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"]


class PhotoEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    alt_en: Alt
    alt_de: Alt
    caption_en: Caption | None = None
    caption_de: Caption | None = None


class PhotoOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    photos: list[PhotoEdit] = Field(max_length=12)
    thumbnail_id: UUID | None = None


class PhotoResponse(PhotoEdit):
    width: int
    height: int
    sort_order: int


class EvictedRecap(BaseModel):
    id: UUID
    title_en: str | None
    title_de: str | None


class RecapResponse(RecapContent):
    id: UUID
    version: int
    status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
    thumbnail_id: UUID | None
    photos: list[PhotoResponse]
    cleanup_pending: bool = False
    evicted_recaps: list[EvictedRecap] = Field(default_factory=list)


class RecapListResponse(BaseModel):
    items: list[RecapResponse]
    page: int
    total: int
    total_pages: int
    years: list[int]
    mosaic: list[RecapResponse]
    pending_cleanup: list[UUID] = Field(default_factory=list)


class RecapUrlResponse(BaseModel):
    url: str
    expires_in: int


class RecapDeleteResponse(BaseModel):
    cleanup_pending: bool
    thumbnail_changed: bool = False
    recap: RecapResponse | None = None
