"""Bounded drafts and explicit revision commands."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StrictBool, field_validator

from app.services.chatbot.models import MAX_ANSWER, MAX_QUESTION, Contract

Category = Literal[
    "vgu",
    "buddy-program",
    "student-life",
    "campus-services",
    "transportation",
    "accommodation",
    "buddyweb-guide",
    "faq",
]
Publication = Literal["draft", "published", "pending", "unpublished"]
QuestionText = Annotated[str, Field(max_length=MAX_QUESTION)]


class LocaleDraft(Contract):
    questions: tuple[QuestionText, ...] = Field(default=(), max_length=15)
    answer: str = Field(default="", max_length=MAX_ANSWER)


class FaqContent(Contract):
    category: Category = "faq"
    en: LocaleDraft = Field(default_factory=LocaleDraft)
    de: LocaleDraft = Field(default_factory=LocaleDraft)
    source_title: str = Field(default="", max_length=160)
    source_url: str = Field(default="", max_length=300)
    evidence: Literal["admin_managed", "unsupported", "conflicting"] = "unsupported"


class CreateFaq(Contract):
    content: FaqContent
    builtin_id: str | None = Field(default=None, max_length=80)


class Version(Contract):
    version: int = Field(strict=True, ge=1, le=2147483646)


class SaveFaq(Version):
    content: FaqContent


class Confirm(Version):
    confirm: StrictBool

    @field_validator("confirm")
    @classmethod
    def explicit_confirmation(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Confirm the public change.")
        return value


class Restore(Version):
    revision: int = Field(strict=True, ge=1, le=2147483646)
    publish: StrictBool = False
    confirm: StrictBool = False


class Preview(Contract):
    question: str = Field(min_length=1, max_length=MAX_QUESTION, repr=False)
    content: FaqContent
    faq_id: UUID | None = None
    builtin_id: str | None = Field(default=None, max_length=80)


class Faq(Contract):
    id: UUID
    builtin_id: str | None
    version: int
    draft_revision: int
    published_revision: int | None
    published_at: datetime | None
    updated_at: datetime
    status: Publication
    content: FaqContent


class FaqPage(Contract):
    items: tuple[Faq, ...]
    has_more: bool


class Revision(Contract):
    revision: int
    author_id: UUID
    created_at: datetime
    content: FaqContent


class History(Contract):
    items: tuple[Revision, ...]
    has_more: bool
