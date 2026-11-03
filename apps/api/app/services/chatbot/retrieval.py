"""Small FAQ-first lexical retriever with coverage and ambiguity abstention."""

import re
from dataclasses import dataclass

from app.services.chatbot.language import words
from app.services.chatbot.models import MAX_CONTEXT, Entry, Language

STOP_WORDS = words(
    "what how where when which who can does do is are the a an I me my please about "
    "was wie wo wann welche wer kann können ist sind der die das ein eine ich mir "
    "mein meine bitte über to of in on at for and or mit im am auf zu zur zum von "
    "den dem des und oder you your man es sich students student studierende vgu buddyweb "
    "another other from get find documents document einem eines anderen anderer studierenden "
    "person finde finden bekommen gibt s einer dokumente"
)

# Linguistic variants only; facts and FAQ aliases remain in the unchanged corpus.
NORMALIZE = {
    "erstelle": "erstellen",
    "registriere": "registrieren",
    "invite": "invitation",
    "invitations": "invitation",
    "schicken": "senden",
    "sende": "senden",
    "sehe": "ansehen",
    "öffne": "öffnen",
    "kontaktiere": "hilfe",
    "kontaktieren": "hilfe",
    "contact": "help",
    "unterstützung": "hilfe",
    "internationale": "international",
    "informationen": "information",
    "wohnheim": "dormitory",
    "wohnheiminformationen": "dormitory information",
    "sportinformationen": "sports information",
    "sportangebot": "sports",
    "chatte": "chat",
    "chatten": "chat",
    "chatting": "chat",
}


def split_questions(text: str) -> tuple[str, ...]:
    # Split explicit question boundaries only, not conjunctions within a supported FAQ.
    parts = tuple(part.strip() for part in re.split(r"[?？]+", text) if part.strip())
    return parts if len(parts) > 1 else (text,)


def terms(text: str) -> frozenset[str]:
    return frozenset(
        variant
        for word in words(text) - STOP_WORDS
        for variant in NORMALIZE.get(word, word).split()
    )


@dataclass(frozen=True)
class Hit:
    entry: Entry
    score: float


class Retriever:
    def __init__(self, entries: tuple[Entry, ...]) -> None:
        self.entries = tuple(entry for entry in entries if entry.authoritative)
        self.historical_entries = tuple(entry for entry in entries if entry.historical_reference)

    def retrieve(self, question: str, language: Language) -> tuple[Hit, ...]:
        parts = split_questions(question)
        if len(parts) > 1:
            if len(parts) > 3:
                return ()
            selected: dict[str, Hit] = {}
            for part in parts:
                hits = self._retrieve_single(part, language)
                if hits:
                    selected.setdefault(hits[0].entry.id, hits[0])
            return tuple(selected.values())[:3]
        return self._retrieve_single(question, language)

    def _retrieve_single(self, question: str, language: Language) -> tuple[Hit, ...]:
        verified = self._retrieve_verified(question, language)
        if verified:
            return verified
        if self.ambiguous(question, language):
            return ()
        # Historical answers require an entire normalized alias, not a fuzzy overlap.
        # Unknown modifiers (prices, medical/legal claims, current opening hours) abstain.
        query = terms(question)
        historical = tuple(
            Hit(entry, 1.0)
            for entry in self.historical_entries
            if query and query in {terms(alias) for alias in entry.localized(language).questions}
        )
        return historical if len(historical) == 1 else ()

    def ambiguous(self, question: str, language: Language) -> bool:
        hits = self._retrieve_verified(question, language, include_ambiguous=True)
        return len(hits) > 1 and hits[0].score - hits[1].score < 0.12

    def _retrieve_verified(
        self, question: str, language: Language, *, include_ambiguous: bool = False
    ) -> tuple[Hit, ...]:
        exact = tuple(
            Hit(entry, 2.0)
            for entry in self.entries
            if words(question) in {words(alias) for alias in entry.localized(language).questions}
        )
        if exact:
            return exact if len(exact) == 1 or include_ambiguous else ()
        query = terms(question)
        if not query:
            return ()
        hits: list[Hit] = []
        for entry in self.entries:
            localized = entry.localized(language)
            aliases = tuple(terms(alias) for alias in localized.questions)
            # Aliases authorize answers; keywords are editor metadata, not sufficient evidence.
            best = 0.0
            for alias in aliases:
                if query == alias:
                    best = 1.0
                    continue
                shared = query & alias
                coverage = len(shared) / len(query)
                precision = len(shared) / max(1, len(alias))
                if len(shared) >= 2 and coverage >= 0.7 and precision >= 0.5:
                    best = max(best, 0.7 * coverage + 0.3 * precision)
            if best:
                hits.append(Hit(entry, best))
        hits.sort(key=lambda hit: (-hit.score, hit.entry.id))
        if not include_ambiguous and len(hits) > 1 and hits[0].score - hits[1].score < 0.12:
            return ()
        return tuple(hits[:3])

    @staticmethod
    def context(hits: tuple[Hit, ...], language: Language) -> str:
        chunks: list[str] = []
        used = 0
        for hit in hits[:3]:
            if not hit.entry.authoritative:
                continue
            chunk = f"[{hit.entry.id}] {hit.entry.localized(language).answer}"
            if used + len(chunk) + 1 > MAX_CONTEXT:
                break
            chunks.append(chunk)
            used += len(chunk) + 1
        return "\n".join(chunks)
