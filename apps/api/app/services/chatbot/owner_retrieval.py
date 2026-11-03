"""An evidence-gated extension to the existing FAQ retriever, not a fact generator."""

import re
from dataclasses import dataclass
from math import log

from app.services.chatbot.intents import content_tokens, tokens, topics, vocabulary
from app.services.chatbot.owner_source import Passage, Snapshot

MIN_COVERAGE = 0.8
AMBIGUITY_GAP = 0.15


@dataclass(frozen=True)
class Selection:
    passages: tuple[Passage, ...] = ()
    ambiguous: bool = False


def select_passages(snapshot: Snapshot, question: str, *, reference: bool = False) -> Selection:
    query = content_tokens(question)
    identified = topics(question)
    if len(identified) > 1:
        return Selection(ambiguous=True)
    topic = next(iter(identified), "")
    synonyms = vocabulary(topic)
    required = query - synonyms
    if not query:
        return Selection()
    # Query-specific words, numbers, negation and place identifiers must be in the passage.
    # An intent synonym alone can select evidence only from that actual source topic.
    scored: list[tuple[float, Passage]] = []
    for passage in snapshot.passages:
        if passage.policy == "instruction" or len(tokens(passage.text)) < 3:
            continue
        if tokens(passage.text) <= tokens("no name of restaurant food specialty price address"):
            continue
        if passage.policy == "conflicted" and not (
            reference
            or query
            & {"passport", "reisepass", "dinner", "abendessen", "valid", "status", "fact", "price"}
        ):
            continue
        body_terms = tokens(passage.text)
        if topic == "food" and not body_terms & tokens(
            "food restaurant restaurants dishes meal meals rice noodles vendors"
        ):
            continue
        if len(body_terms) < 6 and not re.search(
            r"(?m)^\s*\d+\s+[A-Za-zÀ-ỿ]|\b[A-Za-z]+:\s+\S", passage.text
        ):
            continue
        if required and not required <= passage.terms:
            continue
        section_topics = topics(passage.section)
        if topic and topic not in passage.topics:
            continue
        if (
            topic
            and section_topics
            and topic not in section_topics
            and passage.section.casefold() not in {"shopping", "guide introduction"}
            and len(body_terms & synonyms) < 2
        ):
            continue
        if passage.policy == "sensitive" and not reference:
            continue
        coverage = len(query & passage.terms) / len(query)
        if not topic and coverage < MIN_COVERAGE:
            continue
        matches = query & passage.terms
        rarity = sum(
            log(1 + len(snapshot.passages) / (1 + snapshot.document_frequency.get(word, 0)))
            for word in matches
        )
        score = rarity + 4 * (topic in section_topics if topic else False)
        body = tokens(passage.text)
        score += len(body & synonyms) * 0.3
        if topic in {"food", "laundry", "groceries", "accommodation", "transport"}:
            score += (
                len(body & {"outside", "near", "next", "location", "locations", "located"}) * 6.0
            )
        if passage.policy == "conflicted" and query & {
            "passport",
            "reisepass",
            "dinner",
            "abendessen",
            "validity",
            "gültig",
        }:
            score += 20
        if score or topic:
            scored.append((score, passage))
    if not scored:
        return Selection()
    scored.sort(key=lambda item: (-item[0], item[1].start_line))
    best = scored[0][1]
    if best.policy == "conflicted":
        matching = tuple(
            p
            for p in snapshot.passages
            if p.policy == "conflicted" and p.conflict_group == best.conflict_group
        )[:2]
        return Selection(matching)
    if (
        not topic
        and len(scored) > 1
        and scored[0][0] - scored[1][0] < AMBIGUITY_GAP
        and best.section != scored[1][1].section
    ):
        return Selection(ambiguous=True)
    return Selection((best,))
