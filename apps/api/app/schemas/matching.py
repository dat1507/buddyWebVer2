"""Privacy-minimized profile contracts shared by Buddy Matching features."""

from __future__ import annotations

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
