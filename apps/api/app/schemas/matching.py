"""Privacy-minimized profile contracts shared by Buddy Matching features."""

from __future__ import annotations

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    model_validator,
)

from app.models import LanguageProficiency, StudentType
from app.schemas.profile import WeeklyAvailability
from app.schemas.profile_catalog import (
    MAX_PROFILE_ACTIVITY_SELECTIONS,
    MAX_PROFILE_INTEREST_SELECTIONS,
    MAX_PROFILE_LANGUAGE_SELECTIONS,
)


class SafeMatchingAvatar(BaseModel):
    """Minimal private-avatar reference without storage metadata or a durable URL."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class SafeMatchingPreference(BaseModel):
    """Localized predefined or profile-owned custom Interest/Activity value."""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None
    code: StrictStr | None
    label: StrictStr = Field(min_length=1, max_length=120)
    is_custom: StrictBool

    @model_validator(mode="after")
    def require_consistent_identity(self) -> Self:
        catalog_value = self.id is not None and self.code is not None and not self.is_custom
        custom_value = self.id is None and self.code is None and self.is_custom
        if not (catalog_value or custom_value):
            raise ValueError("Matching preference identity is inconsistent.")
        return self


class SafeMatchingLanguage(BaseModel):
    """Localized predefined or custom Language with its persisted proficiency."""

    model_config = ConfigDict(extra="forbid")

    code: StrictStr | None
    label: StrictStr = Field(min_length=1, max_length=120)
    proficiency: LanguageProficiency
    is_custom: StrictBool

    @model_validator(mode="after")
    def require_consistent_identity(self) -> Self:
        if (self.code is None) is not self.is_custom:
            raise ValueError("Matching language identity is inconsistent.")
        return self


class SafeMatchingProfile(BaseModel):
    """Explicit candidate allowlist with no User, auth, or internal identity fields."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    display_name: StrictStr | None = Field(default=None, max_length=80)
    student_type: StudentType
    major: StrictStr | None = None
    avatar: SafeMatchingAvatar
    interests: list[SafeMatchingPreference] = Field(
        min_length=1,
        max_length=MAX_PROFILE_INTEREST_SELECTIONS,
    )
    languages: list[SafeMatchingLanguage] = Field(
        min_length=1,
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS,
    )
    activities: list[SafeMatchingPreference] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_ACTIVITY_SELECTIONS,
    )
    availability: WeeklyAvailability | None


class CompatibilitySignalExplanation(BaseModel):
    """Public numeric contribution for one compatibility signal."""

    model_config = ConfigDict(extra="forbid")

    similarity: float = Field(ge=0, le=1)
    weight: int = Field(ge=0, le=100)
    points: float = Field(ge=0, le=100)


class CompatibilityExplanation(BaseModel):
    """Safe structured explanation with no raw or normalized preference identities."""

    model_config = ConfigDict(extra="forbid")

    interests: CompatibilitySignalExplanation
    activities: CompatibilitySignalExplanation
    availability: CompatibilitySignalExplanation
    languages: CompatibilitySignalExplanation
    major: CompatibilitySignalExplanation


class MatchingRecommendation(BaseModel):
    """One ranked, privacy-safe candidate and its server-owned score."""

    model_config = ConfigDict(extra="forbid")

    profile: SafeMatchingProfile
    score: int = Field(ge=0, le=100)
    explanation: CompatibilityExplanation


class MatchingRecommendationListResponse(BaseModel):
    """One deterministic page of the current recommendation ranking."""

    model_config = ConfigDict(extra="forbid")

    items: list[MatchingRecommendation]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=50)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    reference_week_start: date
