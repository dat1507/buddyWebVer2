"""Privacy boundary tests for REC-001 candidate projections."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models import LanguageProficiency, StudentType
from app.schemas.matching import (
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SafeMatchingProfile,
)
from app.schemas.profile import WeeklyAvailability

PROFILE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PHOTO_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
INTEREST_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


def _safe_profile() -> SafeMatchingProfile:
    return SafeMatchingProfile(
        id=PROFILE_ID,
        display_name="Buddy",
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=SafeMatchingAvatar(id=PHOTO_ID, width=640, height=640),
        interests=[
            SafeMatchingPreference(
                id=INTEREST_ID,
                code="photography",
                label="Photography",
                is_custom=False,
            ),
            SafeMatchingPreference(
                id=None,
                code=None,
                label="Formula 1",
                is_custom=True,
            ),
        ],
        languages=[
            SafeMatchingLanguage(
                code=None,
                label="Thai",
                proficiency=LanguageProficiency.INTERMEDIATE,
                is_custom=True,
            )
        ],
        activities=[],
        availability=WeeklyAvailability.model_validate(
            {
                "timezone": "Asia/Ho_Chi_Minh",
                "slots": [{"weekday": 3, "start_minute": 1080, "end_minute": 1200}],
            }
        ),
    )


def test_candidate_projection_is_an_explicit_privacy_allowlist() -> None:
    payload = _safe_profile().model_dump(mode="json")

    assert set(payload) == {
        "id",
        "display_name",
        "student_type",
        "major",
        "avatar",
        "interests",
        "languages",
        "activities",
        "availability",
    }
    rendered = repr(payload).lower()
    for private_name in (
        "email",
        "password",
        "session",
        "csrf",
        "normalized_key",
        "user_id",
        "deleted_at",
    ):
        assert private_name not in rendered


def test_candidate_and_preference_contracts_reject_unallowlisted_fields() -> None:
    payload = _safe_profile().model_dump()
    payload["email"] = "private@example.com"
    with pytest.raises(ValidationError):
        SafeMatchingProfile.model_validate(payload)

    with pytest.raises(ValidationError):
        SafeMatchingPreference.model_validate(
            {
                "id": None,
                "code": None,
                "label": "Formula 1",
                "is_custom": True,
                "normalized_key": "formula 1",
            }
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"id": None, "code": "music", "label": "Music", "is_custom": False},
        {"id": INTEREST_ID, "code": None, "label": "Music", "is_custom": False},
        {"id": INTEREST_ID, "code": "music", "label": "Music", "is_custom": True},
    ],
)
def test_preference_identity_cannot_mix_custom_and_catalog_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SafeMatchingPreference.model_validate(payload)
