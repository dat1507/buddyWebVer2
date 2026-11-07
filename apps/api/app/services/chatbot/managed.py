"""Validation and precedence for the separately managed FAQ layer."""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from pydantic import ValidationError

from app.schemas.chatbot import ChatbotResponse, PublicCitation, PublicReference, public_answer
from app.schemas.managed_faq import FaqContent
from app.services.chatbot.intents import current_query, sensitive_query
from app.services.chatbot.knowledge import load_knowledge
from app.services.chatbot.language import words
from app.services.chatbot.models import Entry, Language
from app.services.chatbot.retrieval import split_questions
from app.services.chatbot.service import ChatbotService

MAX_PUBLISHED = 200
# Managed answers deliberately cover public, low-risk information only. A URL is not verification.
_SENSITIVE = re.compile(
    r"\b(fees?|tuition|charges?|scholarship|refund|payment|feeschedule|price|"
    r"admission|enrolment|enrollment|eligibility|deadline|rules?|regulation\w*|policy|"
    r"gebühr\w*|stipendi\w*|zahlung\w*|zulassung\w*|frist\w*|regel\w*|"
    r"diagnos\w*|prescri\w*|tax|fine|opening hours|office hours)\b|[€$₫]|\b(?:VND|USD|EUR)\b",
    re.IGNORECASE,
)
_PRIVATE = re.compile(
    r"https?://|[\w.+-]+@[\w.-]+|(?:\+?\d[ ().-]*){7,}|"
    r"\b(?:[a-f0-9]{8}-[a-f0-9-]{27}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.|"
    r"(?:password|passwd|secret|token|api.?key|bearer|cookie|passwort|schlüssel)\s*[:=])|"
    r"<[^>]*>|(?:\]\s*\()",
    re.IGNORECASE,
)


class KnowledgeIssue(ValueError):
    """Stable validation code without any submitted content."""


@lru_cache(maxsize=1)
def builtin_entries() -> tuple[Entry, ...]:
    return load_knowledge()


@lru_cache(maxsize=1)
def baseline_service() -> ChatbotService:
    return ChatbotService()


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def _public_reference(content: FaqContent) -> PublicReference:
    try:
        reference = PublicReference(title=content.source_title.strip(), url=content.source_url)
    except ValueError:
        raise KnowledgeIssue("unsafe_source") from None
    if not re.fullmatch(
        r"https://(?:[a-z0-9-]+\.)*vgu\.edu\.vn(?::443)?(?:/[a-zA-Z0-9/_.-]*)?", reference.url
    ):
        raise KnowledgeIssue("unsafe_source")
    return reference


def validate_draft(content: FaqContent) -> None:
    for value in (
        content.source_title,
        content.en.answer,
        content.de.answer,
        *content.en.questions,
        *content.de.questions,
    ):
        if (
            _PRIVATE.search(value)
            or ChatbotService._restricted(value)
            or any(unicodedata.category(c) in {"Cc", "Cf"} and c not in "\n\t" for c in value)
        ):
            raise KnowledgeIssue("unsafe_content")
    if content.source_url:
        # Accept an incomplete title while saving a draft, never an arbitrary URL.
        _public_reference(content.model_copy(update={"source_title": "Source"}))


@dataclass(frozen=True, slots=True)
class ManagedFaq:
    id: UUID
    revision: int
    builtin_id: str | None
    content: FaqContent
    reference: PublicReference

    @property
    def citation_id(self) -> str:
        return f"managed-{self.id.hex}-r{self.revision}"


def validated_faq(
    faq_id: UUID,
    revision: int,
    builtin_id: str | None,
    content: FaqContent,
) -> ManagedFaq:
    validate_draft(content)
    if content.evidence != "admin_managed":
        raise KnowledgeIssue("evidence_required")
    if not all(
        locale.answer.strip()
        and locale.questions
        and all(_normalized(question) for question in locale.questions)
        for locale in (content.en, content.de)
    ):
        raise KnowledgeIssue("bilingual_required")
    for value in (
        *content.en.questions,
        *content.de.questions,
        content.en.answer,
        content.de.answer,
    ):
        if sensitive_query(value) or current_query(value) or _SENSITIVE.search(value):
            raise KnowledgeIssue("high_risk")
    return ManagedFaq(faq_id, revision, builtin_id, content, _public_reference(content))


def validate_snapshot(faqs: tuple[ManagedFaq, ...]) -> tuple[ManagedFaq, ...]:
    if len(faqs) > MAX_PUBLISHED:
        raise KnowledgeIssue("publication_limit")
    builtin = tuple(entry for entry in builtin_entries() if entry.authoritative)
    builtin_ids = {entry.id for entry in builtin}
    targets: set[str] = set()
    for faq in faqs:
        if faq.builtin_id is not None:
            if faq.builtin_id not in builtin_ids or faq.builtin_id in targets:
                raise KnowledgeIssue("builtin_conflict")
            targets.add(faq.builtin_id)
    for lang in ("en", "de"):
        seen: set[frozenset[str]] = set()
        builtin_aliases = {
            words(question): entry.id
            for entry in builtin
            for question in entry.localized(lang).questions
        }
        for faq in faqs:
            for question in getattr(faq.content, lang).questions:
                key = words(question)
                if (
                    not key
                    or key in seen
                    or (key in builtin_aliases and builtin_aliases[key] != faq.builtin_id)
                ):
                    raise KnowledgeIssue("alias_conflict")
                seen.add(key)
    return faqs


def answer_with_managed(
    service: ChatbotService,
    question: str,
    faqs: tuple[ManagedFaq, ...],
) -> ChatbotResponse:
    base = public_answer(service.ask(question))
    if (
        not faqs
        or base.language == "und"
        or base.status not in {"answer", "insufficient"}
        or len(split_questions(question)) != 1
        or sensitive_query(question)
        or current_query(question)
        or _SENSITIVE.search(question)
    ):
        return base
    language: Language = base.language
    original = base.sources[0] if len(base.sources) == 1 else None
    key = _normalized(question)
    for faq in faqs:
        locale = faq.content.en if language == "en" else faq.content.de
        if faq.builtin_id is not None:
            if (
                original is None
                or original.entry_id != faq.builtin_id
                or original.verification_status
                not in {
                    "verified_code",
                    "verified_official",
                }
            ):
                continue
        elif (
            base.status != "insufficient"
            or base.sources
            or not any(_normalized(alias) == key for alias in locale.questions)
        ):
            continue
        return ChatbotResponse(
            answer=locale.answer,
            language=language,
            supported=True,
            status="answer",
            sources=(
                PublicCitation(
                    entry_id=faq.citation_id,
                    title="Admin-managed FAQ",
                    verification_status="admin_managed",
                    verified_on=None,
                    references=(faq.reference,),
                ),
            ),
        )
    return base


def validate_selection(faq: ManagedFaq, faqs: tuple[ManagedFaq, ...]) -> None:
    """A published question must select its own revision in the real retrieval path."""
    for lang in ("en", "de"):
        for question in getattr(faq.content, lang).questions:
            answer = answer_with_managed(baseline_service(), question, faqs)
            if (
                answer.language != lang
                or len(answer.sources) != 1
                or answer.sources[0].entry_id != faq.citation_id
            ):
                raise KnowledgeIssue("retrieval_conflict")


def from_row(row_id: UUID, revision: int, builtin_id: str | None, content: object) -> ManagedFaq:
    try:
        return validated_faq(row_id, revision, builtin_id, FaqContent.model_validate(content))
    except ValidationError:
        raise KnowledgeIssue("invalid_snapshot") from None
