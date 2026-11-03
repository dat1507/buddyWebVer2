"""Public chatbot DTOs: source IDs and approved URLs, never repository file paths."""

from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from app.services.chatbot.models import (
    MAX_ANSWER,
    MAX_QUESTION,
    Answer,
    Contract,
    Question,
    SourceProvenance,
)

ErrorCode = Literal[
    "invalid_request",
    "payload_too_large",
    "unsupported_media_type",
    "method_not_allowed",
    "disabled",
    "configuration_error",
    "rate_limited",
    "overloaded",
    "timeout",
    "unavailable",
    "internal_error",
]


class ChatbotQuery(Contract):
    question: str = Field(strict=True, min_length=1, max_length=MAX_QUESTION, repr=False)

    @field_validator("question")
    @classmethod
    def valid_question(cls, value: str) -> str:
        return Question(text=value).text


class PublicReference(Contract):
    title: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=300)

    @field_validator("url")
    @classmethod
    def official_public_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.port not in {None, 443}
            or not (host == "vgu.edu.vn" or host.endswith(".vgu.edu.vn"))
            or any(character.isspace() or ord(character) < 32 for character in value)
        ):
            raise ValueError("Only reviewed public university URLs are allowed.")
        return value


class PublicCitation(Contract):
    entry_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,79}$")
    title: Literal[
        "BuddyWeb guide",
        "VGU public information",
        "Historical student guide (systemPrompt.txt)",
        "Owner-provided guide (systemPrompt.txt)",
    ]
    verification_status: Literal[
        "verified_code", "verified_official", "historical_reference", "owner_provided", "conflicted"
    ]
    verified_on: date | None
    references: tuple[PublicReference, ...] = Field(max_length=5)
    provenance: SourceProvenance | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ChatbotResponse(Contract):
    answer: str = Field(min_length=1, max_length=MAX_ANSWER)
    language: Literal["en", "de", "und"]
    supported: bool
    status: (
        Literal[
            "answer",
            "historical_reference",
            "owner_provided",
            "conflicted",
            "clarification",
            "insufficient",
            "choose_language",
            "restricted",
        ]
        | ErrorCode
    )
    sources: tuple[PublicCitation, ...] = Field(default=(), max_length=3)
    mode: Literal["local_retrieval"] = "local_retrieval"


def public_answer(answer: Answer) -> ChatbotResponse:
    citations = []
    for citation in answer.citations:
        references = tuple(
            PublicReference(title=source.title, url=source.reference)
            for source in citation.sources
            if source.reference.startswith("https://")
        )
        if citation.status == "verified_official" and not references:
            raise ValueError("Official evidence requires a public reference.")
        citations.append(
            PublicCitation(
                entry_id=citation.entry_id,
                title="BuddyWeb guide"
                if citation.status == "verified_code"
                else "Historical student guide (systemPrompt.txt)"
                if citation.status == "historical_reference"
                else "Owner-provided guide (systemPrompt.txt)"
                if citation.status in {"owner_provided", "conflicted"}
                else "VGU public information",
                verification_status=citation.status,
                verified_on=citation.verified_on,
                references=references,
                provenance=citation.provenance,
            )
        )
    return ChatbotResponse(
        answer=answer.text,
        language=answer.language,
        supported=bool(citations),
        status=answer.outcome,
        sources=tuple(citations),
    )
