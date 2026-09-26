"""Localized profile catalogs and owner-bound selection contracts."""

from __future__ import annotations

from typing import Final, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from app.models import (
    MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
    MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
    LanguageProficiency,
)

CatalogLocale = Literal["en", "de"]
MAX_PROFILE_INTEREST_SELECTIONS: Final = 20
MAX_PROFILE_LANGUAGE_SELECTIONS: Final = 10
MAX_PROFILE_ACTIVITY_SELECTIONS: Final = 20


class InterestCatalogItem(BaseModel):
    """One active interest exposed through its stable database identifier."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: StrictStr
    label: StrictStr
    category: StrictStr


class InterestCatalogResponse(BaseModel):
    """Localized active interest catalog."""

    model_config = ConfigDict(extra="forbid")

    locale: CatalogLocale
    items: list[InterestCatalogItem]


class LanguageCatalogItem(BaseModel):
    """One active language keyed by its stable normalized code."""

    model_config = ConfigDict(extra="forbid")

    code: StrictStr
    label: StrictStr


class LanguageCatalogResponse(BaseModel):
    """Localized active language catalog."""

    model_config = ConfigDict(extra="forbid")

    locale: CatalogLocale
    items: list[LanguageCatalogItem]


class ActivityCatalogItem(BaseModel):
    """One active Activity exposed through its stable database identifier."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: StrictStr
    label: StrictStr


class ActivityCatalogResponse(BaseModel):
    """Localized active Activity catalog."""

    model_config = ConfigDict(extra="forbid")

    locale: CatalogLocale
    items: list[ActivityCatalogItem]


class CustomPreferenceInput(BaseModel):
    """Bounded raw custom label accepted before PREF-002 normalization."""

    model_config = ConfigDict(extra="forbid")

    label: StrictStr = Field(max_length=MAX_CUSTOM_PREFERENCE_INPUT_LENGTH)


class CustomLanguageInput(CustomPreferenceInput):
    """Custom language label with the existing proficiency enum."""

    proficiency: LanguageProficiency


class CustomPreferenceSelection(BaseModel):
    """Validated custom preference projection without its internal identity key."""

    model_config = ConfigDict(extra="forbid")

    label: StrictStr = Field(
        min_length=1,
        max_length=MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
    )


class CustomLanguageSelection(CustomPreferenceSelection):
    """Validated custom language projection retaining its proficiency."""

    proficiency: LanguageProficiency


class ProfileInterestUpdate(BaseModel):
    """Exact replacement set for one profile's normalized interests."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=MAX_PROFILE_INTEREST_SELECTIONS)
    custom_interests: list[CustomPreferenceInput] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_INTEREST_SELECTIONS,
    )

    @field_validator("interest_ids")
    @classmethod
    def reject_duplicate_interests(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Interest identifiers must be unique.")
        return value

    @model_validator(mode="after")
    def bound_combined_interests(self) -> Self:
        if len(self.interest_ids) + len(self.custom_interests) > MAX_PROFILE_INTEREST_SELECTIONS:
            raise ValueError("Profile interests exceed the selection limit.")
        return self


class ProfileLanguageSelection(BaseModel):
    """One normalized language selection and its matching proficiency."""

    model_config = ConfigDict(extra="forbid")

    language_code: StrictStr = Field(
        min_length=2,
        max_length=35,
        pattern=r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$",
    )
    proficiency: LanguageProficiency


class ProfileLanguageUpdate(BaseModel):
    """Exact replacement set for one profile's language proficiencies."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    languages: list[ProfileLanguageSelection] = Field(max_length=MAX_PROFILE_LANGUAGE_SELECTIONS)
    custom_languages: list[CustomLanguageInput] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS,
    )

    @field_validator("languages")
    @classmethod
    def reject_duplicate_languages(
        cls, value: list[ProfileLanguageSelection]
    ) -> list[ProfileLanguageSelection]:
        codes = [selection.language_code for selection in value]
        if len(codes) != len(set(codes)):
            raise ValueError("Language codes must be unique.")
        return value

    @model_validator(mode="after")
    def bound_combined_languages(self) -> Self:
        if len(self.languages) + len(self.custom_languages) > MAX_PROFILE_LANGUAGE_SELECTIONS:
            raise ValueError("Profile languages exceed the selection limit.")
        return self


class ProfileActivityUpdate(BaseModel):
    """Exact replacement set for predefined and custom Activities."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    activity_ids: list[UUID] = Field(max_length=MAX_PROFILE_ACTIVITY_SELECTIONS)
    custom_activities: list[CustomPreferenceInput] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_ACTIVITY_SELECTIONS,
    )

    @field_validator("activity_ids")
    @classmethod
    def reject_duplicate_activities(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Activity identifiers must be unique.")
        return value

    @model_validator(mode="after")
    def bound_combined_activities(self) -> Self:
        if len(self.activity_ids) + len(self.custom_activities) > MAX_PROFILE_ACTIVITY_SELECTIONS:
            raise ValueError("Profile activities exceed the selection limit.")
        return self


class ProfilePreferenceUpdate(BaseModel):
    """Atomic exact replacement contract for all three preference namespaces."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=MAX_PROFILE_INTEREST_SELECTIONS)
    custom_interests: list[CustomPreferenceInput] = Field(
        max_length=MAX_PROFILE_INTEREST_SELECTIONS
    )
    languages: list[ProfileLanguageSelection] = Field(
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS
    )
    custom_languages: list[CustomLanguageInput] = Field(
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS
    )
    activity_ids: list[UUID] = Field(max_length=MAX_PROFILE_ACTIVITY_SELECTIONS)
    custom_activities: list[CustomPreferenceInput] = Field(
        max_length=MAX_PROFILE_ACTIVITY_SELECTIONS
    )

    @field_validator("interest_ids", "activity_ids")
    @classmethod
    def reject_duplicate_identifiers(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Preference identifiers must be unique within a group.")
        return value

    @field_validator("languages")
    @classmethod
    def reject_duplicate_language_codes(
        cls, value: list[ProfileLanguageSelection]
    ) -> list[ProfileLanguageSelection]:
        codes = [selection.language_code for selection in value]
        if len(codes) != len(set(codes)):
            raise ValueError("Language codes must be unique.")
        return value

    @model_validator(mode="after")
    def bound_combined_groups(self) -> Self:
        group_sizes = (
            (
                len(self.interest_ids) + len(self.custom_interests),
                MAX_PROFILE_INTEREST_SELECTIONS,
            ),
            (
                len(self.languages) + len(self.custom_languages),
                MAX_PROFILE_LANGUAGE_SELECTIONS,
            ),
            (
                len(self.activity_ids) + len(self.custom_activities),
                MAX_PROFILE_ACTIVITY_SELECTIONS,
            ),
        )
        if any(size > maximum for size, maximum in group_sizes):
            raise ValueError("A preference group exceeds its selection limit.")
        return self


class ProfileInterestSelectionResponse(BaseModel):
    """Canonical interest set after an owner-bound update."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=MAX_PROFILE_INTEREST_SELECTIONS)
    custom_interests: list[CustomPreferenceSelection] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_INTEREST_SELECTIONS,
    )


class ProfileLanguageSelectionResponse(BaseModel):
    """Canonical language set after an owner-bound update."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    languages: list[ProfileLanguageSelection] = Field(
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS
    )
    custom_languages: list[CustomLanguageSelection] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS,
    )


class ProfileActivitySelectionResponse(BaseModel):
    """Canonical Activity set after an owner-bound update."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    activity_ids: list[UUID] = Field(max_length=MAX_PROFILE_ACTIVITY_SELECTIONS)
    custom_activities: list[CustomPreferenceSelection] = Field(
        default_factory=list,
        max_length=MAX_PROFILE_ACTIVITY_SELECTIONS,
    )


class ProfilePreferenceSelectionResponse(BaseModel):
    """Complete deterministic owner projection for all preference namespaces."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=MAX_PROFILE_INTEREST_SELECTIONS)
    custom_interests: list[CustomPreferenceSelection] = Field(
        max_length=MAX_PROFILE_INTEREST_SELECTIONS
    )
    languages: list[ProfileLanguageSelection] = Field(
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS
    )
    custom_languages: list[CustomLanguageSelection] = Field(
        max_length=MAX_PROFILE_LANGUAGE_SELECTIONS
    )
    activity_ids: list[UUID] = Field(max_length=MAX_PROFILE_ACTIVITY_SELECTIONS)
    custom_activities: list[CustomPreferenceSelection] = Field(
        max_length=MAX_PROFILE_ACTIVITY_SELECTIONS
    )
