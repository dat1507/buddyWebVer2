"""Bounded, immutable public knowledge and response contracts."""

from datetime import date
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_QUESTION = 500
MAX_ANSWER = 1800
MAX_CONTEXT = 6000
Language = Literal["en", "de"]
Verification = Literal[
    "verified_official", "verified_code", "unverified", "conflicting", "outdated"
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalizedKnowledge(Contract):
    questions: tuple[Annotated[str, Field(min_length=1, max_length=MAX_QUESTION)], ...] = Field(
        min_length=1, max_length=15
    )
    answer: str = Field(min_length=1, max_length=MAX_ANSWER)
    keywords: tuple[str, ...] = Field(default=(), max_length=30)

    @model_validator(mode="after")
    def nonblank_content(self) -> Self:
        if not self.answer.strip() or any(not text.strip() for text in self.questions):
            raise ValueError("Knowledge questions and answers must not be blank.")
        return self


class Source(Contract):
    title: str = Field(min_length=1, max_length=160)
    reference: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def stable_public_reference(self) -> Self:
        ref = self.reference
        if not self.title.strip():
            raise ValueError("Source title must not be blank.")
        if ref.startswith("https://"):
            url = urlsplit(ref)
            if not url.hostname or url.username or url.password or url.query:
                raise ValueError("Use stable public URLs without credentials or query tokens.")
        elif ref.startswith(("apps/", "docs/")):
            if ".." in PurePosixPath(ref).parts or "\\" in ref or ":" in ref:
                raise ValueError("Source paths must stay repository-relative.")
        elif not ref.startswith("historical:"):
            raise ValueError("Use a public HTTPS URL or a repository-relative source.")
        return self


class Entry(Contract):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,79}$")
    category: Literal[
        "vgu",
        "buddy-program",
        "student-life",
        "campus-services",
        "transportation",
        "accommodation",
        "buddyweb-guide",
        "faq",
    ]
    status: Verification
    verified_on: date | None
    sources: tuple[Source, ...] = Field(min_length=1, max_length=5)
    en: LocalizedKnowledge
    de: LocalizedKnowledge

    @model_validator(mode="after")
    def require_verification_evidence(self) -> Self:
        if self.authoritative and self.verified_on is None:
            raise ValueError("Verified knowledge requires an actual verification date.")
        if self.authoritative and any(
            source.reference.startswith("historical:") for source in self.sources
        ):
            raise ValueError("Historical evidence alone cannot authorize an answer.")
        return self

    @property
    def authoritative(self) -> bool:
        return self.status in {"verified_official", "verified_code"}

    @property
    def historical_reference(self) -> bool:
        # Owner-approved low-risk topics only; all previous exclusions remain excluded.
        references = {
            "legacy-d9-food": "historical:systemPrompt.txt#L235-L248",
            "legacy-laundry": "historical:systemPrompt.txt#L420-L421",
        }
        return (
            self.id in references
            and self.category == "student-life"
            and self.status == "unverified"
            and self.verified_on is None
            and len(self.sources) == 1
            and self.sources[0].reference == references[self.id]
        )

    def localized(self, language: Language) -> LocalizedKnowledge:
        return self.de if language == "de" else self.en


class Question(Contract):
    text: str = Field(strict=True, min_length=1, max_length=MAX_QUESTION, repr=False)

    @model_validator(mode="after")
    def validate_text(self) -> Self:
        if not self.text.strip() or any(
            ord(character) < 32 and character not in "\n\t" for character in self.text
        ):
            raise ValueError("Enter a nonempty question without control characters.")
        return self


class Citation(Contract):
    entry_id: str
    sources: tuple[Source, ...]
    verified_on: date | None
    status: Literal[
        "verified_official", "verified_code", "historical_reference", "owner_provided", "conflicted"
    ]
    provenance: "SourceProvenance | None" = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def verification_date(self) -> Self:
        if (self.status in {"historical_reference", "owner_provided", "conflicted"}) != (
            self.verified_on is None
        ):
            raise ValueError("Historical references have no current verification date.")
        if (self.status in {"owner_provided", "conflicted"}) != (self.provenance is not None):
            raise ValueError("Canonical source citations require exact provenance.")
        return self


class SourceProvenance(Contract):
    filename: Literal["systemPrompt.txt"] = "systemPrompt.txt"
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    section: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def ordered_lines(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("Source line range is reversed.")
        return self


class Answer(Contract):
    language: Literal["en", "de", "und"]
    outcome: Literal[
        "answer",
        "historical_reference",
        "owner_provided",
        "conflicted",
        "clarification",
        "insufficient",
        "choose_language",
        "restricted",
        "unavailable",
    ]
    text: str = Field(min_length=1, max_length=MAX_ANSWER)
    citations: tuple[Citation, ...] = Field(default=(), max_length=3)
    mode: Literal["local_retrieval"] = "local_retrieval"
