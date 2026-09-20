"""Validation boundaries for profile catalog relation replacement."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import LanguageProficiency
from app.schemas.profile_catalog import (
    ProfileInterestUpdate,
    ProfileLanguageUpdate,
)


def test_interest_update_accepts_empty_or_unique_bounded_stable_ids() -> None:
    first = uuid4()
    second = uuid4()

    assert ProfileInterestUpdate(version=1, interest_ids=[]).interest_ids == []
    update = ProfileInterestUpdate.model_validate(
        {"version": 2, "interest_ids": [str(first), str(second)]}
    )
    assert update.interest_ids == [first, second]


def test_interest_update_rejects_duplicates_excess_and_extra_fields() -> None:
    interest_id = uuid4()
    with pytest.raises(ValidationError, match="must be unique"):
        ProfileInterestUpdate.model_validate(
            {"version": 1, "interest_ids": [str(interest_id), str(interest_id)]}
        )
    with pytest.raises(ValidationError, match="at most 20"):
        ProfileInterestUpdate.model_validate(
            {"version": 1, "interest_ids": [str(uuid4()) for _ in range(21)]}
        )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProfileInterestUpdate.model_validate(
            {"version": 1, "interest_ids": [], "profile_id": str(uuid4())}
        )


def test_language_update_accepts_domain_proficiency_and_empty_removal() -> None:
    assert ProfileLanguageUpdate(version=1, languages=[]).languages == []
    update = ProfileLanguageUpdate.model_validate(
        {
            "version": 2,
            "languages": [
                {"language_code": "de", "proficiency": "intermediate"},
                {"language_code": "en", "proficiency": "fluent"},
            ],
        }
    )
    assert update.languages[0].proficiency is LanguageProficiency.INTERMEDIATE


def test_language_update_rejects_duplicate_unknown_shape_excess_and_invalid_proficiency() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        ProfileLanguageUpdate.model_validate(
            {
                "version": 1,
                "languages": [
                    {"language_code": "en", "proficiency": "fluent"},
                    {"language_code": "en", "proficiency": "native"},
                ],
            }
        )
    with pytest.raises(ValidationError, match="at most 10"):
        ProfileLanguageUpdate.model_validate(
            {
                "version": 1,
                "languages": [
                    {"language_code": f"x-{index:02d}", "proficiency": "beginner"}
                    for index in range(11)
                ],
            }
        )
    with pytest.raises(ValidationError, match="Input should be"):
        ProfileLanguageUpdate.model_validate(
            {
                "version": 1,
                "languages": [{"language_code": "en", "proficiency": "expert"}],
            }
        )
    with pytest.raises(ValidationError, match="String should match pattern"):
        ProfileLanguageUpdate.model_validate(
            {
                "version": 1,
                "languages": [{"language_code": "EN", "proficiency": "native"}],
            }
        )


@pytest.mark.parametrize("payload", [{}, {"version": 0}, {"version": True}])
def test_relation_updates_require_a_positive_strict_version(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProfileInterestUpdate.model_validate(payload)
    with pytest.raises(ValidationError):
        ProfileLanguageUpdate.model_validate(payload)
