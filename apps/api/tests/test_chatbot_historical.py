"""Owner-authorized references: historical status and conservative boundaries."""

from pathlib import Path

import pytest

from app.schemas.chatbot import public_answer
from app.services.chatbot.knowledge import load_knowledge
from app.services.chatbot.language import words
from app.services.chatbot.models import MAX_ANSWER, Entry
from app.services.chatbot.retrieval import Hit, Retriever
from app.services.chatbot.service import CLARIFY, FALLBACK, MULTI_FALLBACK, ChatbotService

ENTRIES = load_knowledge()
HISTORICAL = tuple(e for e in ENTRIES if e.historical_reference)
CASES = [
    (e, lang, q) for e in HISTORICAL for lang in ("en", "de") for q in e.localized(lang).questions
]


@pytest.mark.parametrize(("entry", "language", "question"), CASES)
def test_qualified_reference_paraphrases(entry: Entry, language: str, question: str) -> None:
    answer = ChatbotService(ENTRIES).ask(question)
    assert answer.outcome == "historical_reference"
    assert answer.language == language
    assert answer.text == getattr(entry, language).answer
    assert len(answer.text) <= MAX_ANSWER
    assert [c.entry_id for c in answer.citations] == [entry.id]
    assert answer.citations[0].verified_on is None
    assert answer.citations[0].status == "historical_reference"
    assert answer.citations[0].sources == entry.sources
    response = public_answer(answer)
    assert response.supported  # Source-supported, not currently verified.
    assert response.status == "historical_reference"
    source = response.sources[0]
    assert source.title == "Historical student guide (systemPrompt.txt)"
    assert source.verification_status == "historical_reference"
    assert source.verified_on is None and source.references == ()
    assert "apps/" not in response.model_dump_json() and "C:" not in response.model_dump_json()
    assert "not been" in answer.text or "nicht" in answer.text


@pytest.mark.parametrize(
    "question",
    [
        "Where can I find food near D8 Gate?",
        "Where is the laundry service open now?",
        "What are EVA Laundry prices?",
        "Where is EVA Laundry address?",
        "Is food near D9 Gate safe for my allergy?",
        "Is laundry required for my visa?",
        "Wo finde ich einen Wäscheservice für medizinische Kleidung?",
        "Ist EVA Laundry heute geöffnet?",
        "What visa do I need?",
        "Is health insurance required?",
        "How long must my passport be valid?",
        "Where can I find a hospital near D9 Gate?",
        "Where is the automobile repair service?",
        "Where can I find food near D9 Gate and prices?",
        "How much does a dorm room cost?",
        "What is the weather on Mars?",
    ],
)
def test_unknown_current_high_risk_and_unrelated_questions_abstain(question: str) -> None:
    result = ChatbotService(ENTRIES).ask(question)
    assert result.outcome == "insufficient"
    assert result.citations == ()


def test_missing_source_and_ineligible_metadata_fail_closed(tmp_path: Path) -> None:
    for entry in HISTORICAL:
        for changes in (
            {"id": "legacy-health"},
            {"status": "outdated"},
            {"sources": [dict(title="Unknown", reference="historical:missing")]},
        ):
            changed = Entry.model_validate({**entry.model_dump(), **changes})
            assert not changed.historical_reference
            assert ChatbotService((changed,)).ask(entry.en.questions[0]).outcome == "insufficient"
    without = tuple(e for e in ENTRIES if not e.historical_reference)
    for entry in HISTORICAL:
        assert ChatbotService(without).ask(entry.en.questions[0]).outcome == "insufficient"


def test_verified_precedence_exclusions_and_no_historical_provider_context() -> None:
    food = HISTORICAL[0]
    verified = Entry.model_validate(
        {
            **food.model_dump(),
            "id": "fixture-verified-food",
            "status": "verified_code",
            "verified_on": "2026-10-24",
            "sources": [dict(title="Fixture", reference="docs/fixture.md")],
        }
    )
    result = ChatbotService((*ENTRIES, verified)).ask(food.en.questions[0])
    assert result.outcome == "answer" and result.citations[0].entry_id == verified.id
    retriever = Retriever(ENTRIES)
    for entry in ENTRIES:
        if not entry.authoritative and not entry.historical_reference:
            for language in ("en", "de"):
                assert not retriever.retrieve(entry.localized(language).questions[0], language)
    assert retriever.context(tuple(Hit(e, 1) for e in HISTORICAL), "en") == ""
    assert words("D9 Gate") != words("D8 Gate")


def test_fallbacks_and_mixed_questions_remain_bounded() -> None:
    service = ChatbotService(ENTRIES)
    assert "one specific" not in FALLBACK["en"]
    result = service.ask("Where is the laundry service? What visa do I need?")
    assert result.outcome == "historical_reference"
    assert len(result.citations) == 1 and MULTI_FALLBACK["en"] in result.text
    assert len(result.text) <= MAX_ANSWER
    result = service.ask("How do I register? Where is the laundry service?")
    assert result.outcome == "historical_reference"
    assert {c.status for c in result.citations} == {"verified_code", "historical_reference"}
    one = next(e for e in ENTRIES if e.id == "website-register")
    two = one.model_copy(update={"id": "fixture-second"})
    result = ChatbotService((one, two)).ask("How do I register?")
    assert result.outcome == "insufficient" and result.text == CLARIFY["en"]


def test_source_snapshot_and_only_two_qualified_records() -> None:
    assert len(HISTORICAL) == 2
    path = (
        Path(__file__).resolve().parents[3]
        / "docs/project-knowledge/chatbot/HISTORICAL_SOURCE_2026-10-24.md"
    )
    evidence = path.read_text(encoding="utf-8")
    assert "head outside the D9 gate" in evidence
    assert "Laundry Place next to the Automobile Repair shop" in evidence
    for entry in HISTORICAL:
        assert entry.verified_on is None and entry.status == "unverified"
        assert not entry.authoritative
        for language in ("en", "de"):
            assert not any(c.isdigit() for c in entry.localized(language).answer.replace("D9", ""))
            assert "24 hours" not in entry.localized(language).answer
