"""Localized profile catalogs and owner-bound selection contracts."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from app.models import LanguageProficiency

CatalogLocale = Literal["en", "de"]


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


class ProfileInterestUpdate(BaseModel):
    """Exact replacement set for one profile's normalized interests."""

    model_config = ConfigDict(extra="forbid")

    version: StrictInt = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=20)

    @field_validator("interest_ids")
    @classmethod
    def reject_duplicate_interests(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Interest identifiers must be unique.")
        return value


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
    languages: list[ProfileLanguageSelection] = Field(max_length=10)

    @field_validator("languages")
    @classmethod
    def reject_duplicate_languages(
        cls, value: list[ProfileLanguageSelection]
    ) -> list[ProfileLanguageSelection]:
        codes = [selection.language_code for selection in value]
        if len(codes) != len(set(codes)):
            raise ValueError("Language codes must be unique.")
        return value


class ProfileInterestSelectionResponse(BaseModel):
    """Canonical interest set after an owner-bound update."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    interest_ids: list[UUID] = Field(max_length=20)


class ProfileLanguageSelectionResponse(BaseModel):
    """Canonical language set after an owner-bound update."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    languages: list[ProfileLanguageSelection] = Field(max_length=10)
