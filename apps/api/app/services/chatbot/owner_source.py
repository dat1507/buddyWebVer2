"""Bounded canonical-text parser and atomic, fail-closed local source snapshots."""

import json
import re
import threading
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from app.services.chatbot.intents import tokens, topics

CANONICAL_SOURCE = Path(__file__).with_name("sources") / "systemPrompt.txt"
MAX_SOURCE_BYTES = 256_000
MAX_PASSAGES = 2000
Policy = Literal["owner_provided", "conflicted", "sensitive", "instruction"]

# Layout recognition only: no factual answers, addresses, prices or business names.
HEADINGS = frozenset(
    "vgu buddy program the ambassador team|vgu official social media channels|vgu student association – vsa|vgu international office|student affairs|vgu library|arrival|after|maybe you should know before arrival|arrrival at vgu|monetary transaction|motorbike|taxi|transportation|anywhere|from hcmc to binh duong (and vice versa)|sport complex|outdoor|indoor|operation hours|registration|accomondation|dorminotory|location|fee (room only)|room types|additional information|living on campus|food cost|bus costs|extracurricular activities|living in thu dau mot city|living in ho chi minh city|rents|bus costs (registration needed)|day in life|shopping|surrounding the campus area|restaurant / food|grocerieswinmart|bach hoa xanh|aeon mall canary|co.opmart thu dau mot – supermarket|go! supermarket binh duong|grocerieshealth|hcmc hospital|on campus support|internet services|more information|copying and printing|vgu library other service providers|laundry|contact us".split(
        "|"
    )
)
INSTRUCTION = re.compile(
    r"(?i)(you are a virtual|your personality|assume every question|cannot successfully complete|ignore (?:all|previous)|reveal (?:your |the )?(?:system|prompt)|execute (?:this|the) command|system instructions|system prompt|api key|zugangsdaten|ignoriere)"
)
SENSITIVE = re.compile(
    r"(?i)\b(visa|passport|immigration|customs|law|insurance|vaccin\w*|malaria|dengue|health|hospital|medicine|medical|prohibited|restricted|mandatory|police|reimbursement)\b"
)
TIME_DEPENDENT = re.compile(
    r"(?i)(\b(?:vnd|eur|usd|fees?|costs?|prices?|rents?|curfew|hours?|am|pm|minutes?|months?|weeks?|deadline)\b|\d+\s*[:–-]\s*\d+)"
)


@dataclass(frozen=True)
class Passage:
    id: str
    text: str
    section: str
    start_line: int
    end_line: int
    policy: Policy
    time_sensitive: bool
    terms: frozenset[str]
    topics: frozenset[str]
    conflict_group: str | None = None


@dataclass(frozen=True)
class Snapshot:
    version: str
    passages: tuple[Passage, ...]
    source_lines: int
    vocabulary: frozenset[str]
    document_frequency: Mapping[str, int]

    def summary(self) -> dict[str, object]:
        return {
            "status": "ready",
            "sha256": self.version,
            "lines": self.source_lines,
            "passages": len(self.passages),
            "policies": {
                policy: sum(p.policy == policy for p in self.passages)
                for policy in ("owner_provided", "conflicted", "sensitive", "instruction")
            },
        }


class SourceInvalid(ValueError):
    """Diagnostic code only: never original text or filesystem paths."""


def heading(line: str) -> str | None:
    clean = line.strip()
    if clean.casefold().startswith("food and beverage:"):
        return "Food and beverage"
    if clean.startswith("#"):
        return clean.lstrip("#").strip()[:160] or None
    normalized = re.sub(r"^\d+", "", clean).rstrip(":").strip()
    if normalized.casefold() in HEADINGS:
        return normalized[:160]
    return None


def parse_source(raw: bytes) -> Snapshot:
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise SourceInvalid("empty_or_oversized")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SourceInvalid("invalid_utf8") from None
    if re.search(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{30,}|eyJ[A-Za-z0-9_-]{20,}\.)|https?://[^/\s]+@|[?&](?:token|api_key|secret)=",
        text,
    ):
        raise SourceInvalid("credential_like_content")
    if not text.strip() or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise SourceInvalid("invalid_text")
    lines = text.splitlines()
    passages: list[Passage] = []
    section = "Guide introduction"
    section_start = 1
    parent_section = ""
    buffered: list[tuple[int, str]] = []

    def flush() -> None:
        if not buffered:
            return
        first = buffered[0][0]
        block = "\n".join(line for _, line in buffered).strip()
        # Sentence boundaries preserve decimals, URLs and wrapped sentences. Lists without
        # reliable punctuation stay intact rather than being converted into guessed facts.
        offsets = [
            0,
            *[
                m.end()
                for m in re.finditer(r"(?<!Mr.)(?<!Ms.)(?<!Dr.)(?<=[.!?])\s+(?=[A-ZÀ-ỿ])", block)
            ],
            len(block),
        ]
        for start, end in zip(offsets, offsets[1:], strict=False):
            body = block[start:end].strip()
            if not body:
                continue
            start_line = first + block[:start].count("\n")
            end_line = min(buffered[-1][0], first + block[:end].rstrip().count("\n"))
            policy: Policy = (
                "instruction"
                if INSTRUCTION.search(body)
                else "sensitive"
                if SENSITIVE.search(body + " " + section)
                else "owner_provided"
            )
            material = section + "\n" + body
            identifier = (
                "owner-" + sha256((str(start_line) + "\n" + material).encode()).hexdigest()[:20]
            )
            passages.append(
                Passage(
                    identifier,
                    body,
                    section,
                    start_line,
                    end_line,
                    policy,
                    bool(TIME_DEPENDENT.search(body)),
                    tokens(material),
                    topics(material),
                )
            )
        buffered.clear()

    for number, line in enumerate(lines, 1):
        label = heading(line)
        if label:
            flush()
            main = line.lstrip().startswith(("## ", "# ")) or label.casefold() in {
                "vgu buddy program the ambassador team",
                "vgu official social media channels",
                "vgu student association – vsa",
                "vgu international office",
                "student affairs",
                "vgu library",
                "arrival",
                "monetary transaction",
                "motorbike",
                "taxi",
                "transportation",
                "sport complex",
                "accomondation",
                "dorminotory",
                "living on campus",
                "living in thu dau mot city",
                "living in ho chi minh city",
                "shopping",
                "surrounding the campus area",
                "food and beverage",
                "grocerieswinmart",
                "grocerieshealth",
                "hcmc hospital",
                "on campus support",
                "copying and printing",
                "laundry",
                "contact us",
            }
            if main or not parent_section:
                parent_section = label
                section = label
            else:
                section = f"{parent_section} / {label}"[:160]
            section_start = number
            # The heading itself remains part of the next verbatim evidence passage.
            buffered.append((number, line))
            continue
        if not line.strip():
            flush()
            continue
        # Preserve tabular/list rows and their wrapped addresses together.
        if (
            buffered
            and re.match(r"^\d+\s+[A-Za-zÀ-ỿ]", line.strip())
            and len("\n".join(s for _, s in buffered)) > 80
        ):
            flush()
        if not buffered and number == section_start:
            buffered.append((number, line))
        else:
            buffered.append((number, line))
    flush()
    if not passages or len(passages) > MAX_PASSAGES:
        raise SourceInvalid("invalid_passage_count")

    normalized = re.sub(r"\s+", " ", text.casefold())
    passport_values = set(re.findall(r"passport.{0,70}?valid.{0,40}?(\d+) months", normalized))

    def dorm_ranges(passage: Passage) -> set[tuple[str, str]]:
        if "dorm" not in passage.section.casefold() or not tokens(passage.text) & {
            "room",
            "shared",
            "rents",
        }:
            return set()
        return set(re.findall(r"(\d[\d,]*)\s*[–-]\s*(\d[\d,]*)\s*VND", passage.text))

    differing_dorm_ranges = set().union(*(dorm_ranges(passage) for passage in passages))
    dinner_yes = bool(
        re.search(r"(?:canteen|cafeteria).{0,90}(?:offers|serves?).{0,50}dinner", normalized)
    )
    dinner_no = bool(
        re.search(r"(?:canteen|cafeteria).{0,90}(?:don.t|not|no).{0,40}dinner", normalized)
    )
    # Structured owner updates can mark conflicts explicitly, or repeat a single-valued
    # field with different values under the same heading. Contact/address lists are exempt.
    fields: dict[tuple[str, str], set[str]] = {}
    for passage in passages:
        for name, value in re.findall(
            r"(?im)^(fact|status|current fee|passport validity|dinner service|opening hours):\s*(.+)$",
            passage.text,
        ):
            fields.setdefault((passage.section.casefold(), name.casefold()), set()).add(
                value.strip().casefold()
            )
    rebuilt = []
    for passage in passages:
        body = re.sub(r"\s+", " ", passage.text.casefold())
        conflicting = (
            ("passport" in body and "valid" in body and len(passport_values) > 1)
            or (
                bool(re.search(r"\b(?:cafeteria|canteen)\b", body))
                and "dinner" in body
                and dinner_yes
                and dinner_no
            )
            or (bool(dorm_ranges(passage)) and len(differing_dorm_ranges) > 1)
            or "[conflicted]" in body
            or any(
                len(fields.get((passage.section.casefold(), name.casefold()), set())) > 1
                for name, _ in re.findall(
                    r"(?im)^(fact|status|current fee|passport validity|dinner service|opening hours):\s*(.+)$",
                    passage.text,
                )
            )
        )
        rebuilt.append(
            replace(
                passage,
                policy="conflicted",
                conflict_group="passport-validity"
                if "passport" in body and "valid" in body
                else "cafeteria-dinner"
                if "dinner" in body
                else "dorm-room-prices"
                if dorm_ranges(passage)
                else passage.section.casefold(),
            )
            if conflicting and passage.policy != "instruction"
            else passage
        )
    return Snapshot(
        sha256(raw).hexdigest(),
        tuple(rebuilt),
        len(lines),
        frozenset().union(*(p.terms for p in rebuilt if p.policy != "instruction")),
        MappingProxyType(dict(Counter(word for passage in rebuilt for word in passage.terms))),
    )


class SourceIndex:
    """One immutable snapshot per observed file version; no background thread or network."""

    def __init__(self, path: Path = CANONICAL_SOURCE) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._signature: tuple[int, int, int, int] | None = None
        self._snapshot: Snapshot | None = None
        self._digest: str | None = None
        self.diagnostic = "not_loaded"
        self.rebuilds = 0

    def _stat(self) -> tuple[int, int, int, int]:
        info = self.path.stat()
        return info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_ino

    def get(self) -> Snapshot | None:
        with self._lock:
            signature: tuple[int, int, int, int] | None = None
            digest: str | None = None
            try:
                signature = self._stat()
                for _ in range(2):
                    if signature[2] > MAX_SOURCE_BYTES:
                        raise SourceInvalid("empty_or_oversized")
                    with self.path.open("rb") as source:
                        raw = source.read(MAX_SOURCE_BYTES + 1)
                    after = self._stat()
                    if signature == after:
                        digest = sha256(raw).hexdigest()
                        # Bounded reads/hash also detect same-size edits that preserve mtime.
                        # Parsing/tokenization/DF construction happen only for changed bytes.
                        if digest == self._digest:
                            self._signature = signature
                            return self._snapshot
                        candidate = parse_source(raw)
                        self._snapshot, self._signature, self._digest = candidate, signature, digest
                        self.diagnostic = "ready"
                        self.rebuilds += 1
                        return candidate
                    signature = after
                raise SourceInvalid("changed_during_read")
            except (OSError, SourceInvalid) as error:
                self._snapshot = None
                self._signature, self._digest = signature, digest
                self.diagnostic = str(error) if isinstance(error, SourceInvalid) else "unreadable"
                return None


def main() -> int:
    index = SourceIndex()
    snapshot = index.get()
    print(
        json.dumps(
            snapshot.summary()
            if snapshot
            else {"status": "unavailable", "diagnostic": index.diagnostic}
        )
    )
    return 0 if snapshot is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
