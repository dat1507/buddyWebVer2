"""Validation tests for allowlisted partial profile updates."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import StudentType
from app.schemas import ProfilePreferences, ProfileUpdate, WeeklyAvailability


@pytest.mark.parametrize(
    "field_name",
    [
        "id",
        "user_id",
        "role",
        "completion",
        "percentage",
        "onboarding_completed_at",
        "deleted_at",
        "interests",
        "languages",
    ],
)
def test_profile_update_forbids_owner_authorization_and_derived_fields(field_name: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProfileUpdate.model_validate(
            {"version": 1, "display_name": "Student", field_name: "untrusted"}
        )


@pytest.mark.parametrize("field_name", ["full_name", "student_type", "matching_opt_in"])
def test_profile_update_rejects_explicit_null_for_non_nullable_update_fields(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError, match="cannot be null"):
        ProfileUpdate.model_validate({"version": 1, field_name: None})


def test_profile_update_distinguishes_omitted_fields_from_explicit_optional_null() -> None:
    update = ProfileUpdate.model_validate({"version": 4, "display_name": None})

    assert update.model_fields_set == {"version", "display_name"}
    assert update.display_name is None
    assert update.full_name is None


def test_profile_update_requires_version_and_at_least_one_change() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        ProfileUpdate.model_validate({"full_name": "Student Name"})
    with pytest.raises(ValidationError, match="At least one profile field"):
        ProfileUpdate.model_validate({"version": 1})


def test_profile_update_normalizes_bounded_text_and_domain_values() -> None:
    update = ProfileUpdate.model_validate(
        {
            "version": 2,
            "full_name": "  Student Name  ",
            "display_name": "  Student  ",
            "bio": "  Hello  ",
            "student_type": "INTERNATIONAL",
            "study_year": 3,
            "arrival_date": "2026-10-01",
            "matching_opt_in": False,
        }
    )

    assert update.full_name == "Student Name"
    assert update.display_name == "Student"
    assert update.bio == "Hello"
    assert update.student_type is StudentType.INTERNATIONAL
    assert update.study_year == 3
    assert update.arrival_date == date(2026, 10, 1)
    assert update.matching_opt_in is False


def test_weekly_availability_splits_overnight_slots_and_sorts_iso_weekdays() -> None:
    availability = WeeklyAvailability.model_validate(
        {
            "timezone": "Europe/Berlin",
            "slots": [
                {"weekday": 2, "start_minute": 1380, "end_minute": 60},
                {"weekday": 1, "start_minute": 600, "end_minute": 720},
            ],
        }
    )

    assert [slot.model_dump() for slot in availability.slots] == [
        {"weekday": 1, "start_minute": 600, "end_minute": 720},
        {"weekday": 2, "start_minute": 1380, "end_minute": 1440},
        {"weekday": 3, "start_minute": 0, "end_minute": 60},
    ]


def test_weekly_availability_rejects_invalid_timezone_zero_length_and_overlap() -> None:
    with pytest.raises(ValidationError, match="timezone is invalid"):
        WeeklyAvailability.model_validate({"timezone": "Not/A_Zone", "slots": []})
    with pytest.raises(ValidationError, match="positive duration"):
        WeeklyAvailability.model_validate(
            {
                "timezone": "UTC",
                "slots": [{"weekday": 1, "start_minute": 60, "end_minute": 60}],
            }
        )
    with pytest.raises(ValidationError, match="must not overlap"):
        WeeklyAvailability.model_validate(
            {
                "timezone": "UTC",
                "slots": [
                    {"weekday": 1, "start_minute": 60, "end_minute": 180},
                    {"weekday": 1, "start_minute": 120, "end_minute": 240},
                ],
            }
        )


def test_profile_preferences_are_bounded_structured_and_duplicate_free() -> None:
    activity_id = uuid4()
    preferences = ProfilePreferences.model_validate({"preferred_activity_ids": [str(activity_id)]})
    assert preferences.preferred_activity_ids == [activity_id]

    with pytest.raises(ValidationError, match="must be unique"):
        ProfilePreferences.model_validate(
            {"preferred_activity_ids": [str(activity_id), str(activity_id)]}
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProfilePreferences.model_validate(
            {"preferred_activity_ids": [], "notes": "sensitive free-form data"}
        )
