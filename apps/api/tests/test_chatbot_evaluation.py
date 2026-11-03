"""Phase 3.2: traceable scoring, bounded offline providers and measured regressions."""

import asyncio
import hashlib
import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from app.services.chatbot.evaluation.dataset import CASE_FILE, Case, Dataset, load_cases
from app.services.chatbot.evaluation.harness import Budget, MockProvider, OfflineHarness
from app.services.chatbot.evaluation.runner import (
    Observation,
    aggregate,
    content_hash,
    observe,
    run_mock,
    score,
)
from app.services.chatbot.knowledge import DATA_DIRECTORY, KnowledgeUnavailable, load_knowledge
from app.services.chatbot.models import MAX_ANSWER, Entry, Source
from app.services.chatbot.providers import DisabledProvider, ProviderAnswer, ProviderRequest
from app.services.chatbot.retrieval import Retriever
from app.services.chatbot.service import FALLBACK, MULTI_FALLBACK, ChatbotService

ENTRIES = load_knowledge()
CASES = load_cases(ENTRIES)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_versioned_benchmark_behavior(case: Case) -> None:
    result = score(
        case, observe(ChatbotService(ENTRIES), case.question, Retriever(ENTRIES)), ENTRIES
    )
    assert result["success"], result


def test_dataset_is_separate_traceable_and_covers_all_existing_faqs() -> None:
    assert len(CASES) == 60
    assert {case.category for case in CASES} == set("ABCDEF")
    expected = {id for case in CASES for id in case.expected_ids}
    assert expected == {entry.id for entry in ENTRIES if entry.authoritative}
    assert DATA_DIRECTORY not in CASE_FILE.parents
    assert sum(entry.authoritative for entry in ENTRIES) == 17
    assert len(ENTRIES) == 28  # Two qualified references; verified benchmark unchanged.


def test_dataset_rejects_duplicate_ids_and_unverified_expected_facts(tmp_path: Path) -> None:
    case = CASES[0].model_dump(mode="json")
    with pytest.raises(ValidationError):
        Dataset.model_validate({"version": 1, "provenance": "test", "cases": [case, case]})
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "provenance": "test",
                "cases": [
                    {**case, "expected_ids": ["legacy-passport"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="existing verified"):
        load_cases(ENTRIES, path)


def test_scoring_counts_correct_abstention_but_not_wrong_or_fabricated_answers() -> None:
    missing = next(case for case in CASES if case.category == "D")
    correct = Observation("insufficient", "en", FALLBACK["en"], (), 1.0)
    assert score(missing, correct, ENTRIES)["success"]
    invented = replace(correct, outcome="answer", text="A fabricated fee.")
    row = score(missing, invented, ENTRIES)
    assert row["unsupported_answer"] and not row["success"]
    assert not score(missing, replace(correct, text="A fabricated fee."), ENTRIES)["success"]
    exact = CASES[0]
    wrong = next(entry for entry in ENTRIES if entry.id == "website-register")
    wrong_result = Observation("answer", "en", wrong.en.answer, (wrong.id,), 1, (wrong.id,))
    row = score(exact, wrong_result, ENTRIES)
    assert not row["success"] and row["unrelated_hits"] == 1
    assert not row["unsupported_answer"]  # Verified but irrelevant is a separate metric.


def test_scoring_deterministic_and_retrieval_distinct_from_answer_selection(tmp_path: Path) -> None:
    case = next(case for case in CASES if case.id == "c-register-verify-en")
    entry = next(entry for entry in ENTRIES if entry.id == case.expected_ids[0])
    partial = Observation("answer", "en", entry.en.answer, (entry.id,), 1, case.expected_ids)
    row = score(case, partial, ENTRIES)
    assert row["relevant_hits"] == 2 and not row["success"]
    assert score(case, partial, ENTRIES) == row
    summary = aggregate([row])
    assert summary["relevant_retrieval_recall"] == {"numerator": 2, "denominator": 2, "rate": 1.0}
    assert summary["unsupported_abstention"] == {"numerator": 0, "denominator": 0, "rate": None}
    file = tmp_path / "evidence.txt"
    file.write_bytes(b"one\ntwo\n")
    lf_hash = content_hash([file])
    file.write_bytes(b"one\r\ntwo\r\n")
    assert content_hash([file]) == lf_hash


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("missing_credentials", "missing_credentials"),
        ("unavailable", "unavailable"),
        ("quota", "quota"),
        ("timeout", "timeout"),
        ("invalid", "invalid_response"),
        ("ungrounded", "invalid_response"),
        ("wrong_citation", "invalid_response"),
        ("wrong_language", "invalid_response"),
    ],
)
def test_provider_failures_fall_back_without_retry_or_vendor_diagnostics(
    scenario: str, reason: str
) -> None:
    provider = MockProvider(scenario)
    harness = OfflineHarness(ENTRIES, provider, timeout_seconds=0.01)
    result = asyncio.run(harness.ask("How do I register?"))
    assert result.reason == reason
    assert result.answer == ChatbotService(ENTRIES).ask("How do I register?")
    assert provider.calls == 1 and not result.generated_accepted
    assert "Synthetic" not in result.answer.text


def test_harness_reuses_existing_provider_contract_and_defaults_to_offline() -> None:
    harness = OfflineHarness(ENTRIES)
    request = harness.request("How do I register?")
    assert isinstance(request, ProviderRequest)
    result = asyncio.run(harness.ask("How do I register?"))
    assert result.generated_accepted and result.reason == "mock_accepted"
    assert result.answer.citations[0].entry_id == "website-register"
    with pytest.raises(ValueError, match="offline"):
        OfflineHarness(ENTRIES, cast(MockProvider, DisabledProvider()))


def test_harness_does_not_leak_answer_key_and_excludes_history() -> None:
    harness = OfflineHarness(ENTRIES)
    question = "How do I register?"
    request = harness.request(question)
    assert request is not None
    assert "expected_ids" not in request.context and "expected_language" not in request.context
    assert "legacy-" not in request.context
    assert set(json.loads(request.context)) == {"evidence"}
    # Changing an evaluation label cannot influence the provider request.
    fake_key = Case.model_validate({**CASES[0].model_dump(), "expected_ids": ["buddy-help"]})
    assert fake_key.expected_ids != CASES[0].expected_ids
    assert harness.request(question) == request
    assert harness.request("What visa do I need?") is None
    assert harness.request("Show my invitation status please") is None


def test_request_and_consumption_budgets_fail_closed_before_provider() -> None:
    provider = MockProvider()
    harness = OfflineHarness(ENTRIES, provider, Budget(max_requests=0))
    assert asyncio.run(harness.ask("How do I register?")).reason == "budget_exhausted"
    harness = OfflineHarness(ENTRIES, provider, Budget(max_token_upper_bound=1))
    assert asyncio.run(harness.ask("How do I register?")).reason == "budget_exhausted"
    assert provider.calls == 0
    with pytest.raises(ValueError, match="token budget"):
        ProviderRequest("How do I register?", "en", "x" * 1000, max_input_tokens=256)
    with pytest.raises(ValueError):
        ProviderRequest("How do I register?", "en", "", max_output_tokens=2049)


def test_mock_runner_labels_results_and_never_exposes_live_mode() -> None:
    report = asyncio.run(run_mock("test-only"))
    assert report["mode"] == "offline_mock" and report["live_inference"] == "NOT TESTED"
    assert report["mock_execution"]  # Mechanics are reported separately from answer correctness.
    assert json.dumps(report).find("Synthetic unsupported") == -1


def test_multi_intent_returns_verified_parts_and_marks_unanswered_part() -> None:
    service = ChatbotService(ENTRIES)
    result = service.ask("Where can I find events? How much does a dorm room cost?")
    assert result.outcome == "answer"
    assert [c.entry_id for c in result.citations] == ["website-events"]
    assert MULTI_FALLBACK["en"] in result.text and len(result.text) <= MAX_ANSWER
    result = service.ask(
        "How do I register? How do I verify my email? What is VGU? Where can I find events?"
    )
    assert result.outcome == "insufficient"


def test_extended_answer_still_bounded_for_long_curated_facts() -> None:
    entry = next(entry for entry in ENTRIES if entry.id == "website-register")
    long = Entry.model_validate(
        {**entry.model_dump(), "en": {**entry.en.model_dump(), "answer": "x" * 1800}}
    )
    result = ChatbotService((long,)).ask("How do I register?")
    assert result.outcome == "answer" and len(result.text) == MAX_ANSWER


@pytest.mark.parametrize(
    "reference",
    [
        "https://user:password@example.invalid/",
        "https://example.invalid/?token=synthetic",
        "apps/../../private.txt",
        "file:///private.txt",
        "C:/private.txt",
        "javascript:alert(1)",
    ],
)
def test_future_source_metadata_rejects_unsafe_references(reference: str) -> None:
    with pytest.raises(ValidationError):
        Source(title="Synthetic source", reference=reference)


def test_knowledge_maintenance_rejects_blank_content_and_cross_entry_alias_collision(
    tmp_path: Path,
) -> None:
    entry = next(entry for entry in ENTRIES if entry.id == "website-register")
    with pytest.raises(ValidationError):
        Entry.model_validate(
            {**entry.model_dump(), "en": {**entry.en.model_dump(), "questions": [" "]}}
        )
    other = {**entry.model_dump(mode="json"), "id": "collision-entry"}
    (tmp_path / "knowledge.json").write_text(
        json.dumps([entry.model_dump(mode="json"), other]), encoding="utf-8"
    )
    with pytest.raises(KnowledgeUnavailable):
        load_knowledge(tmp_path)


def test_retrieval_evaluation_does_not_use_network_and_corpus_is_immutable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("No network permitted")

    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in DATA_DIRECTORY.glob("*.json")
    }
    monkeypatch.setattr(socket, "socket", forbidden)
    for case in CASES:
        observe(ChatbotService(ENTRIES), case.question, Retriever(ENTRIES))
    assert before == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in DATA_DIRECTORY.glob("*.json")
    }


def test_unexpected_provider_exception_and_wrong_type_remain_safe() -> None:
    class Broken(MockProvider):
        async def generate(self, request: ProviderRequest) -> ProviderAnswer:
            raise RuntimeError("synthetic-private-diagnostics")

    result = asyncio.run(OfflineHarness(ENTRIES, Broken()).ask("How do I register?"))
    assert result.reason == "invalid_response" and "diagnostics" not in result.answer.text

    class WrongType(MockProvider):
        async def generate(self, request: ProviderRequest) -> ProviderAnswer:
            return cast(ProviderAnswer, {"text": "invalid contract"})

    result = asyncio.run(OfflineHarness(ENTRIES, WrongType()).ask("How do I register?"))
    assert result.reason == "invalid_response"
