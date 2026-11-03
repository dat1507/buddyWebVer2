"""Deterministic extractive-answer scoring; timings are observations, not score inputs."""

import hashlib
import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import cast

from app.services.chatbot.evaluation.dataset import CASE_FILE, Case, load_cases
from app.services.chatbot.evaluation.harness import OfflineHarness
from app.services.chatbot.knowledge import DATA_DIRECTORY, load_knowledge
from app.services.chatbot.models import Answer, Entry
from app.services.chatbot.retrieval import Retriever
from app.services.chatbot.service import (
    FALLBACK,
    LANGUAGE_PROMPT,
    MULTI_FALLBACK,
    RESTRICTED,
    UNAVAILABLE,
    ChatbotService,
    InvalidQuestion,
)


def content_hash(paths: list[Path]) -> str:
    """Stable across Git LF/CRLF checkouts; names disambiguate a corpus or source set."""
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(path.read_text(encoding="utf-8").encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class Observation:
    outcome: str
    language: str
    text: str
    ids: tuple[str, ...]
    latency_ms: float
    retrieved_ids: tuple[str, ...] = ()


def observe(
    service: ChatbotService, question: object, retriever: Retriever | None = None
) -> Observation:
    started = perf_counter()
    try:
        answer = service.ask(cast(str, question))
    except InvalidQuestion:
        return Observation("invalid", "und", "", (), (perf_counter() - started) * 1000)
    elapsed = (perf_counter() - started) * 1000
    retrieved: tuple[str, ...] = ()
    if (
        retriever is not None
        and answer.language in {"en", "de"}
        and answer.outcome in {"answer", "insufficient"}
    ):
        retrieved = tuple(
            hit.entry.id for hit in retriever.retrieve(cast(str, question), answer.language)
        )
    result = observation(answer, elapsed)
    return Observation(result.outcome, result.language, result.text, result.ids, elapsed, retrieved)


def observation(answer: Answer, latency_ms: float) -> Observation:
    return Observation(
        answer.outcome,
        answer.language,
        answer.text,
        tuple(citation.entry_id for citation in answer.citations),
        latency_ms,
    )


def score(case: Case, result: Observation, entries: tuple[Entry, ...]) -> dict[str, object]:
    by_id = {entry.id: entry for entry in entries if entry.authoritative}
    expected = set(case.expected_ids)
    actual = set(result.ids)
    retrieved = set(result.retrieved_ids)
    language_ok = result.language == case.expected_language
    citations_ok = actual == expected
    # Exact curated chunks only: a conservative claim-level audit, not semantic AI grading.
    remaining = result.text
    known = True
    for id in result.ids:
        if id not in by_id or result.language not in {"en", "de"}:
            known = False
            continue
        entry = by_id[id]
        text = entry.de.answer if result.language == "de" else entry.en.answer
        if text not in remaining:
            known = False
        remaining = remaining.replace(text, "", 1)
    for text in (*FALLBACK.values(), *MULTI_FALLBACK.values()):
        remaining = remaining.replace(text, "")
    unsupported = result.outcome == "answer" and (not known or bool(remaining.strip("\n ")))
    uncertainty_ok = not case.requires_uncertainty or any(
        text in result.text for text in (*FALLBACK.values(), *MULTI_FALLBACK.values())
    )
    safe_nonanswer = result.outcome == "answer" or result.text in {
        "insufficient": set((*FALLBACK.values(), *MULTI_FALLBACK.values())),
        "restricted": set(RESTRICTED.values()),
        "unavailable": set(UNAVAILABLE.values()),
        "choose_language": {LANGUAGE_PROMPT},
        "invalid": {""},
    }.get(result.outcome, set())
    success = (
        result.outcome == case.expected_outcome
        and language_ok
        and citations_ok
        and not unsupported
        and uncertainty_ok
        and safe_nonanswer
        and len(result.ids) == len(actual)
    )
    return {
        "id": case.id,
        "category": case.category,
        "language": case.expected_language,
        "success": success,
        "answer_expected": bool(expected),
        "outcome": result.outcome,
        "actual_language": result.language,
        "actual_ids": list(result.ids),
        "expected_ids": list(case.expected_ids),
        "retrieved_ids": list(result.retrieved_ids),
        "relevant_hits": len(expected & retrieved),
        "expected_hits": len(expected),
        "unrelated_hits": len(retrieved - expected),
        "returned_hits": len(retrieved),
        "correct_citations": len(expected & actual),
        "returned_citations": len(actual),
        "language_ok": language_ok,
        "citations_ok": citations_ok,
        "unsupported_answer": unsupported,
        "latency_ms": round(result.latency_ms, 4),
        "unsupported_question": not expected and case.expected_outcome == "insufficient",
        "correct_abstention": result.outcome == "insufficient" and not actual,
    }


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    def total(key: str) -> int:
        return sum(int(cast(int, row[key])) for row in rows)

    def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "rate": round(numerator / denominator, 4) if denominator else None,
        }

    factual = [row for row in rows if row["answer_expected"]]
    emitted = [row for row in rows if row["outcome"] == "answer"]
    unsupported = [row for row in rows if row["unsupported_question"]]
    times = sorted(float(cast(float, row["latency_ms"])) for row in rows)
    return {
        "cases": len(rows),
        "behavior_accuracy": ratio(total("success"), len(rows)),
        "factual_answer_accuracy": ratio(
            sum(bool(row["success"]) for row in factual), len(factual)
        ),
        "relevant_retrieval_recall": ratio(total("relevant_hits"), total("expected_hits")),
        "unrelated_retrieval_rate": ratio(total("unrelated_hits"), total("returned_hits")),
        "unsupported_abstention": ratio(
            sum(bool(row["correct_abstention"]) for row in unsupported), len(unsupported)
        ),
        "unsupported_answer_rate": ratio(
            sum(bool(row["unsupported_answer"]) for row in emitted), len(emitted)
        ),
        "language_accuracy": ratio(total("language_ok"), len(rows)),
        "citation_accuracy": ratio(sum(bool(row["citations_ok"]) for row in factual), len(factual)),
        "citation_precision": ratio(total("correct_citations"), total("returned_citations")),
        "latency_ms": {
            "median": round(statistics.median(times), 4) if times else None,
            "p95": times[max(0, math.ceil(0.95 * len(times)) - 1)] if times else None,
        },
    }


def report(rows: list[dict[str, object]], label: str, mode: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "label": label,
        "mode": mode,
        "hash_normalization": "UTF-8 text with LF line endings",
        "dataset_sha256": hashlib.sha256(
            CASE_FILE.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest(),
        "corpus_sha256": content_hash(list(DATA_DIRECTORY.glob("*.json"))),
        "runtime_source_sha256": content_hash(list(DATA_DIRECTORY.parent.glob("*.py"))),
        "live_inference": "NOT TESTED",
        "summary": aggregate(rows),
        "by_category": {
            key: aggregate([row for row in rows if row["category"] == key]) for key in "ABCDEF"
        },
        "by_language": {
            key: aggregate([row for row in rows if row["language"] == key])
            for key in ("en", "de", "und")
        },
        "rows": rows,
    }


def run_retrieval(label: str = "working-tree") -> dict[str, object]:
    entries = load_knowledge()
    cases = load_cases(entries)
    service = ChatbotService(entries)
    service.ask("How do I register?")  # Warm-up excluded; corpus construction is not timed.
    retriever = Retriever(entries)
    return report(
        [score(case, observe(service, case.question, retriever), entries) for case in cases],
        label,
        "retrieval_only",
    )


async def run_mock(label: str = "working-tree") -> dict[str, object]:
    entries = load_knowledge()
    harness = OfflineHarness(entries)
    rows: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()
    accepted = 0
    for case in load_cases(entries):
        started = perf_counter()
        try:
            result = await harness.ask(cast(str, case.question))
            elapsed = (perf_counter() - started) * 1000
            raw = observe(harness.service, case.question, harness.retriever)
            observed = observation(result.answer, elapsed)
            observed = Observation(
                observed.outcome,
                observed.language,
                observed.text,
                observed.ids,
                elapsed,
                raw.retrieved_ids,
            )
            reasons[result.reason] += 1
            accepted += int(result.generated_accepted)
        except InvalidQuestion:
            observed = Observation("invalid", "und", "", (), (perf_counter() - started) * 1000)
            reasons["invalid_input"] += 1
        rows.append(score(case, observed, entries))
    result_report = report(rows, label, "offline_mock")
    result_report["mock_execution"] = {
        "provider_calls": harness.provider.calls,
        "generated_accepted": accepted,
        "reasons": dict(reasons),
        "reserved_token_upper_bound": harness.budget.reserved_tokens,
        "note": "Test-double/fallback mechanics only; not AI quality, tokens or latency.",
    }
    return result_report


def write_report(result: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
