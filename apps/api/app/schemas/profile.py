"""Validation contracts for partial own-profile persistence updates."""

from __future__ import annotations

from datetime import date
from typing import Self
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

from app.models import StudentType


class WeeklyAvailabilitySlot(BaseModel):
    """One ISO-weekday interval measured in local minutes from midnight."""

    model_config = ConfigDict(extra="forbid")

    weekday: StrictInt = Field(ge=1, le=7)
    start_minute: StrictInt = Field(ge=0, le=1439)
    end_minute: StrictInt = Field(ge=0, le=1440)

    @model_validator(mode="after")
    def reject_zero_length_slot(self) -> Self:
        if self.start_minute == self.end_minute:
            raise ValueError("Availability slots must have a positive duration.")
        return self


def _normalized_slots(slots: list[WeeklyAvailabilitySlot]) -> list[WeeklyAvailabilitySlot]:
    normalized: list[WeeklyAvailabilitySlot] = []
    for slot in slots:
        if slot.end_minute > slot.start_minute:
            normalized.append(slot)
            continue

        normalized.append(
            WeeklyAvailabilitySlot(
                weekday=slot.weekday,
                start_minute=slot.start_minute,
                end_minute=1440,
            )
        )
        if slot.end_minute > 0:
            normalized.append(
                WeeklyAvailabilitySlot(
                    weekday=1 if slot.weekday == 7 else slot.weekday + 1,
                    start_minute=0,
                    end_minute=slot.end_minute,
                )
            )

    normalized.sort(key=lambda value: (value.weekday, value.start_minute, value.end_minute))
    previous: WeeklyAvailabilitySlot | None = None
    for slot in normalized:
        if (
            previous is not None
            and previous.weekday == slot.weekday
            and slot.start_minute < previous.end_minute
        ):
            raise ValueError("Availability slots must not overlap.")
        previous = slot
    return normalized


class WeeklyAvailability(BaseModel):
    """Canonical weekly availability with an IANA timezone and split overnight slots."""

    model_config = ConfigDict(extra="forbid")

    timezone: StrictStr
    slots: list[WeeklyAvailabilitySlot] = Field(default_factory=list, max_length=100)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate or len(candidate) > 64:
            raise ValueError("Availability timezone is invalid.")
        try:
            ZoneInfo(candidate)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Availability timezone is invalid.") from error
        return candidate

    @field_validator("slots")
    @classmethod
    def normalize_slots(cls, value: list[WeeklyAvailabilitySlot]) -> list[WeeklyAvailabilitySlot]:
        return _normalized_slots(value)


class ProfilePreferences(BaseModel):
    """Bounded matching preferences without an arbitrary free-form data channel."""

    model_config = ConfigDict(extra="forbid")

    preferred_activity_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @field_validator("preferred_activity_ids")
    @classmethod
    def reject_duplicate_activities(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Preferred activities must be unique.")
        return value


def _trim_required(value: str | None, *, field_name: str, maximum: int) -> str:
    if value is None:
        raise ValueError(f"{field_name} cannot be null.")
    candidate = value.strip()
    if not 1 <= len(candidate) <= maximum:
        raise ValueError(f"{field_name} must contain between 1 and {maximum} characters.")
    return candidate


def _trim_optional(value: str | None, *, field_name: str, maximum: int | None = None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or (maximum is not None and len(candidate) > maximum):
        suffix = f" and at most {maximum} characters" if maximum is not None else ""
        raise ValueError(f"{field_name} must be non-blank{suffix}.")
    return candidate


class ProfileUpdate(BaseModel):
    """Allowlisted partial update with a required optimistic-concurrency version."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    full_name: StrictStr | None = None
    display_name: StrictStr | None = None
    student_type: StudentType | None = None
    nationality: StrictStr | None = None
    major: StrictStr | None = None
    study_year: StrictInt | None = Field(default=None, ge=1, le=10)
    bio: StrictStr | None = None
    home_university: StrictStr | None = None
    arrival_date: date | None = None
    departure_date: date | None = None
    availability: WeeklyAvailability | None = None
    preferences: ProfilePreferences | None = None
    matching_opt_in: StrictBool | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str:
        return _trim_required(value, field_name="Full name", maximum=120)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        return _trim_optional(value, field_name="Display name", maximum=80)

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, value: str | None) -> str | None:
        return _trim_optional(value, field_name="Bio", maximum=500)

    @field_validator("nationality", "major", "home_university")
    @classmethod
    def validate_optional_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        raw_field_name = info.field_name or "profile_field"
        field_name = raw_field_name.replace("_", " ").title()
        return _trim_optional(value, field_name=field_name)

    @field_validator("student_type")
    @classmethod
    def reject_null_student_type(cls, value: StudentType | None) -> StudentType:
        if value is None:
            raise ValueError("Student type cannot be null.")
        return value

    @field_validator("matching_opt_in")
    @classmethod
    def reject_null_matching_opt_in(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("Matching opt-in cannot be null.")
        return value

    @model_validator(mode="after")
    def require_one_change(self) -> Self:
        if not self.model_fields_set.difference({"version"}):
            raise ValueError("At least one profile field must be supplied.")
        return self


class OwnProfileResponse(BaseModel):
    """Editable fields from the authenticated user's profile, without account identifiers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str | None
    display_name: str | None
    student_type: StudentType | None
    nationality: str | None
    major: str | None
    study_year: int | None
    bio: str | None
    home_university: str | None
    arrival_date: date | None
    departure_date: date | None
    availability: WeeklyAvailability | None
    preferences: ProfilePreferences | None
    matching_opt_in: bool
    version: int
