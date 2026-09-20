"""Derived profile readiness and matching-eligibility response contracts."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProfileCompletionStatus(StrEnum):
    """Backend-derived onboarding readiness state."""

    INCOMPLETE = "INCOMPLETE"
    COMPLETE = "COMPLETE"


class ProfileMissingField(StrEnum):
    """Stable required-group codes localized by the frontend."""

    FULL_NAME = "FULL_NAME"
    STUDENT_TYPE = "STUDENT_TYPE"
    AVATAR = "AVATAR"
    INTERESTS = "INTERESTS"
    LANGUAGES = "LANGUAGES"


class MatchingIneligibilityReason(StrEnum):
    """Stable reason codes explaining why a new pairing cannot be created."""

    PROFILE_INCOMPLETE = "PROFILE_INCOMPLETE"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    MATCHING_OPT_IN_REQUIRED = "MATCHING_OPT_IN_REQUIRED"
    ACTIVE_MATCH_RESERVATION = "ACTIVE_MATCH_RESERVATION"


class ProfileCompletionResponse(BaseModel):
    """Read-only completion and new-pair eligibility projection."""

    model_config = ConfigDict(extra="forbid")

    status: ProfileCompletionStatus
    percentage: int = Field(ge=0, le=100, multiple_of=20)
    missing_fields: list[ProfileMissingField] = Field(max_length=5)
    matching_eligible: bool
    reasons: list[MatchingIneligibilityReason] = Field(max_length=5)
