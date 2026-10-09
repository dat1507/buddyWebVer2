"""Strict request and response projections for Event administration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self, cast
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.models import (
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventPhase,
    EventStatus,
    EventVisibility,
)
from app.models.event import DEFAULT_EVENT_TIMEZONE

EventLocale = Literal["en", "de"]


def _trim_optional(value: str | None, *, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not 1 <= len(candidate) <= maximum:
        raise ValueError(f"{field_name} must contain between 1 and {maximum} characters.")
    return candidate


def _aware(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value


class EventContentFields(BaseModel):
    """Draft-capable Event fields shared by create and update requests."""

    model_config = ConfigDict(extra="forbid")

    title_en: StrictStr | None = None
    title_de: StrictStr | None = None
    description_en: StrictStr | None = None
    description_de: StrictStr | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    timezone: StrictStr | None = None
    location_en: StrictStr | None = None
    location_de: StrictStr | None = None
    category: StrictStr | None = None
    organizer: StrictStr | None = None
    registration_url: StrictStr | None = None
    visibility: EventVisibility | None = None
    registration_enabled: StrictBool | None = None
    max_participants: StrictInt | None = Field(default=None, ge=1)
    registration_deadline: datetime | None = None

    @field_validator(
        "title_en",
        "title_de",
        "location_en",
        "location_de",
        "category",
        "organizer",
    )
    @classmethod
    def validate_short_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        limits = {
            "title_en": 120,
            "title_de": 120,
            "location_en": 200,
            "location_de": 200,
            "category": 80,
            "organizer": 200,
        }
        field_name = info.field_name or "event field"
        return _trim_optional(
            value,
            field_name=field_name.replace("_", " ").title(),
            maximum=limits[field_name],
        )

    @field_validator("description_en", "description_de")
    @classmethod
    def validate_description(cls, value: str | None, info: ValidationInfo) -> str | None:
        field_name = (info.field_name or "description").replace("_", " ").title()
        return _trim_optional(value, field_name=field_name, maximum=10_000)

    @field_validator("start_date", "end_date", "registration_deadline")
    @classmethod
    def validate_aware_datetime(
        cls,
        value: datetime | None,
        info: ValidationInfo,
    ) -> datetime | None:
        field_name = (info.field_name or "event date").replace("_", " ").title()
        return _aware(value, field_name=field_name)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Timezone cannot be null.")
        candidate = value.strip()
        if not candidate or len(candidate) > 255:
            raise ValueError("Timezone must be a valid IANA timezone.")
        try:
            ZoneInfo(candidate)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Timezone must be a valid IANA timezone.") from error
        return candidate

    @field_validator("registration_url")
    @classmethod
    def validate_registration_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise ValueError("Registration URL must be an absolute HTTPS URL.")
        return candidate

    @field_validator("visibility")
    @classmethod
    def reject_null_visibility(cls, value: EventVisibility | None) -> EventVisibility:
        if value is None:
            raise ValueError("Visibility cannot be null.")
        return value

    @field_validator("registration_enabled")
    @classmethod
    def reject_null_registration_enabled(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("Registration enabled cannot be null.")
        return value

    @model_validator(mode="after")
    def validate_supplied_schedule(self) -> Self:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date <= self.start_date
        ):
            raise ValueError("Event end date must be later than start date.")
        if (
            self.start_date is not None
            and self.registration_deadline is not None
            and self.registration_deadline > self.start_date
        ):
            raise ValueError("Registration deadline cannot be after the event start date.")
        return self


class EventDraftCreate(EventContentFields):
    """Create one incomplete Event draft with private defaults."""

    timezone: StrictStr | None = DEFAULT_EVENT_TIMEZONE
    visibility: EventVisibility | None = EventVisibility.MEMBERS
    registration_enabled: StrictBool | None = False


class EventDraftUpdate(EventContentFields):
    """Allowlisted partial draft/content update with optimistic concurrency."""

    version: StrictInt = Field(ge=1)
    cover_media_id: UUID | None = None

    @model_validator(mode="after")
    def require_one_change(self) -> Self:
        if not self.model_fields_set.difference({"version"}):
            raise ValueError("At least one Event field must be supplied.")
        return self


class EventStatusUpdate(BaseModel):
    """Explicit editorial transition request separated from content updates."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    status: EventStatus


class AdminEventResponse(BaseModel):
    """Allowlisted Event projection without creator IDs or storage object keys."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    title_en: str | None
    title_de: str | None
    description_en: str | None
    description_de: str | None
    start_date: datetime | None
    end_date: datetime | None
    timezone: str
    location_en: str | None
    location_de: str | None
    category: str | None
    organizer: str | None
    registration_url: str | None
    cover_media_id: UUID | None
    status: EventStatus
    visibility: EventVisibility
    phase: EventPhase | None
    registration_enabled: bool
    max_participants: int | None
    registration_deadline: datetime | None
    published_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class AdminEventListResponse(BaseModel):
    """One stable bounded page of Events across every editorial state."""

    model_config = ConfigDict(extra="forbid")

    items: list[AdminEventResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class EventDeleteResponse(BaseModel):
    """Deletion result without private Storage object identities."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    cleanup_pending: bool
    failed_object_count: int = Field(ge=0)


class EventCoverUploadFields(BaseModel):
    """Text fields carried beside one multipart Event cover."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    alt_en: StrictStr
    alt_de: StrictStr

    @field_validator("version", mode="before")
    @classmethod
    def parse_multipart_version(cls, value: object) -> object:
        if isinstance(value, str) and value.isascii() and value.isdigit():
            return int(value)
        return value

    @field_validator("alt_en", "alt_de")
    @classmethod
    def validate_alt_text(cls, value: str, info: ValidationInfo) -> str:
        return cast(
            str,
            _trim_optional(
                value,
                field_name=(info.field_name or "alt text").replace("_", " ").title(),
                maximum=200,
            ),
        )


class EventMediaUpdate(BaseModel):
    """Allowlisted cover metadata update with parent Event concurrency."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    alt_en: StrictStr | None = None
    alt_de: StrictStr | None = None
    sort_order: StrictInt | None = Field(default=None, ge=0)

    @field_validator("alt_en", "alt_de")
    @classmethod
    def validate_optional_alt_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        return _trim_optional(
            value,
            field_name=(info.field_name or "alt text").replace("_", " ").title(),
            maximum=200,
        )

    @model_validator(mode="after")
    def require_media_change(self) -> Self:
        if not self.model_fields_set.difference({"version"}):
            raise ValueError("At least one Event media field must be supplied.")
        return self


class AdminEventMediaResponse(BaseModel):
    """Admin media metadata without bucket or object-key disclosure."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    event_id: UUID
    usage: EventMediaUsage
    alt_en: str
    alt_de: str
    mime_type: str
    byte_size: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    sort_order: int = Field(ge=0)
    processing_status: EventMediaProcessingStatus
    created_at: datetime
    updated_at: datetime


class EventCoverUploadResponse(BaseModel):
    """Cover replacement result and any post-commit cleanup state."""

    model_config = ConfigDict(extra="forbid")

    event: AdminEventResponse
    media: AdminEventMediaResponse
    cleanup_pending: bool


class EventMediaDeleteResponse(BaseModel):
    """Media deletion result without private object identity."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    media_id: UUID
    event_version: int = Field(ge=1)
    cleanup_pending: bool


class EventMediaUrlResponse(BaseModel):
    """Short-lived Event media delivery response."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    url: str
    expires_in: int = Field(ge=1, le=300)


class EventSliderCta(BaseModel):
    """Internal detail action consumed by the existing Landing adapter."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    href: str = Field(pattern=r"^/events/[0-9a-f-]{36}$")


class PublicEventSliderResponse(BaseModel):
    """Exact snake-case projection expected by the current frontend Zod parser."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    image_url: str
    image_alt: str = Field(min_length=1, max_length=200)
    event_start_at: datetime | None
    event_end_at: datetime | None
    location: str | None = Field(default=None, max_length=200)
    cta: EventSliderCta | None
    sort_order: int = Field(ge=0)

    @field_validator("image_url")
    @classmethod
    def require_https_image_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise ValueError("Slider image URL must be absolute HTTPS.")
        return value


class PublicEventCoverResponse(BaseModel):
    """Short-lived public Event cover projection without Storage object identity."""

    model_config = ConfigDict(extra="forbid")

    url: str
    alt_text: str
    mime_type: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    expires_in: int = Field(ge=1, le=300)


class PublicEventResponse(BaseModel):
    """Localized audience-safe Event detail used by public and member clients."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    locale: EventLocale
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    timezone: str
    location: str
    category: str | None
    organizer: str | None
    registration_url: str | None
    registration_enabled: bool
    registration_deadline: datetime | None
    status: EventStatus
    visibility: EventVisibility
    phase: EventPhase
    cover: PublicEventCoverResponse | None


class PublicEventListResponse(BaseModel):
    """One deterministic bounded page of audience-safe Events."""

    model_config = ConfigDict(extra="forbid")

    items: list[PublicEventResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
