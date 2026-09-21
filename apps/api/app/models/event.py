"""Canonical Event persistence model and derived audience/time behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    and_,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import APPLICATION_SCHEMA
from app.models.base import Base

DEFAULT_EVENT_TIMEZONE = "Asia/Ho_Chi_Minh"


class EventStatus(StrEnum):
    """Admin-controlled editorial state, independent of the event schedule."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class EventVisibility(StrEnum):
    """Audience allowed to discover an otherwise published Event."""

    PUBLIC = "PUBLIC"
    MEMBERS = "MEMBERS"


class EventPhase(StrEnum):
    """Current temporal phase derived from Event start and end instants."""

    UPCOMING = "UPCOMING"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"


class EventRegistrationStatus(StrEnum):
    """Lifecycle state for one user's optional internal Event RSVP."""

    REGISTERED = "registered"
    CANCELLED = "cancelled"
    ATTENDED = "attended"


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value


def derive_event_phase(
    start_date: datetime | None,
    end_date: datetime | None,
    *,
    at: datetime | None = None,
) -> EventPhase | None:
    """Return the phase at an instant, or ``None`` for an incomplete draft schedule."""

    if start_date is None or end_date is None:
        return None

    start = _require_aware(start_date, field_name="Event start date")
    end = _require_aware(end_date, field_name="Event end date")
    if end <= start:
        raise ValueError("Event end date must be later than start date.")

    current = _require_aware(at or datetime.now(UTC), field_name="Phase reference time")
    if current < start:
        return EventPhase.UPCOMING
    if current < end:
        return EventPhase.ONGOING
    return EventPhase.COMPLETED


class Event(Base):
    """Scheduling source kept separate from promotion, media and registration rows."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "title_en IS NULL OR char_length(btrim(title_en)) BETWEEN 1 AND 120",
            name="ck_events_title_en_length",
        ),
        CheckConstraint(
            "title_de IS NULL OR char_length(btrim(title_de)) BETWEEN 1 AND 120",
            name="ck_events_title_de_length",
        ),
        CheckConstraint(
            "description_en IS NULL OR char_length(btrim(description_en)) BETWEEN 1 AND 10000",
            name="ck_events_description_en_length",
        ),
        CheckConstraint(
            "description_de IS NULL OR char_length(btrim(description_de)) BETWEEN 1 AND 10000",
            name="ck_events_description_de_length",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date > start_date",
            name="ck_events_date_order",
        ),
        CheckConstraint(
            "char_length(btrim(timezone)) BETWEEN 1 AND 255",
            name="ck_events_timezone_length",
        ),
        CheckConstraint(
            "location_en IS NULL OR char_length(btrim(location_en)) BETWEEN 1 AND 200",
            name="ck_events_location_en_length",
        ),
        CheckConstraint(
            "location_de IS NULL OR char_length(btrim(location_de)) BETWEEN 1 AND 200",
            name="ck_events_location_de_length",
        ),
        CheckConstraint(
            "category IS NULL OR char_length(btrim(category)) BETWEEN 1 AND 80",
            name="ck_events_category_length",
        ),
        CheckConstraint(
            "organizer IS NULL OR char_length(btrim(organizer)) BETWEEN 1 AND 200",
            name="ck_events_organizer_length",
        ),
        CheckConstraint(
            "registration_url IS NULL OR registration_url ~ '^https://[^[:space:]]+$'",
            name="ck_events_registration_url_https",
        ),
        CheckConstraint(
            "max_participants IS NULL OR max_participants > 0",
            name="ck_events_max_participants_positive",
        ),
        CheckConstraint("version >= 1", name="ck_events_version_positive"),
    )

    title_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_de: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_de: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_EVENT_TIMEZONE,
        server_default=text(f"'{DEFAULT_EVENT_TIMEZONE}'"),
    )
    location_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_de: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    organizer: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # EVT-010 supplies the EventMedia model; EVT-003 installs the circular cover FK.
    cover_media_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            name="event_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=EventStatus.DRAFT,
        server_default=EventStatus.DRAFT.value,
    )
    visibility: Mapped[EventVisibility] = mapped_column(
        Enum(
            EventVisibility,
            name="event_visibility",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda visibilities: [visibility.value for visibility in visibilities],
        ),
        nullable=False,
        default=EventVisibility.MEMBERS,
        server_default=EventVisibility.MEMBERS.value,
    )
    registration_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    @validates("start_date", "end_date", "registration_deadline", "published_at")
    def validate_aware_datetime(self, key: str, value: datetime | None) -> datetime | None:
        if value is not None:
            _require_aware(value, field_name=key.replace("_", " ").title())
        return value

    @validates("timezone")
    def validate_timezone(self, _key: str, value: str) -> str:
        candidate = value.strip()
        if not candidate or len(candidate) > 255:
            raise ValueError("Event timezone must be a valid IANA timezone.")
        try:
            ZoneInfo(candidate)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Event timezone must be a valid IANA timezone.") from error
        return candidate

    @validates("registration_url")
    def validate_registration_url(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise ValueError("Event registration URL must be an absolute HTTPS URL.")
        return candidate

    @property
    def phase(self) -> EventPhase | None:
        """Derive the current schedule phase without persisting mutable state."""

        return self.phase_at(datetime.now(UTC))

    def phase_at(self, at: datetime) -> EventPhase | None:
        """Derive the schedule phase at a caller-supplied aware instant."""

        return derive_event_phase(self.start_date, self.end_date, at=at)

    def is_publicly_visible(self) -> bool:
        """Apply the anonymous audience rule to an in-memory Event."""

        return (
            self.deleted_at is None
            and self.published_at is not None
            and self.visibility is EventVisibility.PUBLIC
            and self.status in {EventStatus.PUBLISHED, EventStatus.CANCELLED}
        )

    @classmethod
    def public_listing_clause(cls) -> ColumnElement[bool]:
        """Return the mandatory SQL predicate for anonymous event reads."""

        return and_(
            cls.deleted_at.is_(None),
            cls.published_at.is_not(None),
            cls.visibility == EventVisibility.PUBLIC,
            cls.status.in_((EventStatus.PUBLISHED, EventStatus.CANCELLED)),
        )


class EventRegistration(Base):
    """One optional internal RSVP owned by a User for an Event."""

    __tablename__ = "event_registrations"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(f"{APPLICATION_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[EventRegistrationStatus] = mapped_column(
        Enum(
            EventRegistrationStatus,
            name="event_registration_status",
            schema=APPLICATION_SCHEMA,
            native_enum=True,
            validate_strings=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=EventRegistrationStatus.REGISTERED,
        server_default=EventRegistrationStatus.REGISTERED.value,
    )

    @validates("registered_at")
    def validate_registered_at(self, _key: str, value: datetime) -> datetime:
        return _require_aware(value, field_name="Registration time")

    @property
    def is_active(self) -> bool:
        """Return whether this row currently reserves Event capacity."""

        return self.deleted_at is None and self.status is EventRegistrationStatus.REGISTERED

    @classmethod
    def active_clause(cls) -> ColumnElement[bool]:
        """Return the shared SQL predicate for capacity and deletion checks."""

        return and_(
            cls.deleted_at.is_(None),
            cls.status == EventRegistrationStatus.REGISTERED,
        )
