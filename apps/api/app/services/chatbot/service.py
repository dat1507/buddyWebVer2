"""Public-information pipeline: validate, detect, retrieve, select, validate output."""

from pathlib import Path

from pydantic import ValidationError

from app.services.chatbot.intents import (
    INTENTS,
    conditional,
    confidence,
    content_tokens,
    current_query,
    language_for,
    reference_query,
    sensitive_query,
    tokens,
    topics,
    vocabulary,
)
from app.services.chatbot.knowledge import KnowledgeUnavailable, load_knowledge
from app.services.chatbot.language import detect_language
from app.services.chatbot.models import (
    MAX_ANSWER,
    Answer,
    Citation,
    Entry,
    Language,
    Question,
    Source,
    SourceProvenance,
)
from app.services.chatbot.owner_retrieval import select_passages
from app.services.chatbot.owner_source import CANONICAL_SOURCE, Snapshot, SourceIndex
from app.services.chatbot.providers import AnswerProvider, DisabledProvider
from app.services.chatbot.retrieval import Retriever, split_questions

LANGUAGE_PROMPT = "Please ask in English or German. / Bitte frage auf Englisch oder Deutsch."
FALLBACK = {
    "en": "I don't have a reliable answer for that yet. Please check the official VGU website "
    "at https://vgu.edu.vn/ or ask the relevant service.",
    "de": "Dazu habe ich noch keine verlässliche Antwort. Bitte prüfe die offizielle VGU-Website "
    "unter https://vgu.edu.vn/ oder frage die zuständige Stelle.",
}
MULTI_FALLBACK = {
    "en": "I could not answer every part. Please ask the remaining questions separately.",
    "de": "Ich konnte nicht jeden Teil beantworten. Bitte stelle die übrigen Fragen einzeln.",
}
CLARIFY = {
    "en": "That could refer to several topics. Please name the service or website action you mean.",
    "de": "Das könnte mehrere Themen betreffen. Bitte nenne den gemeinten Dienst oder Website-Schritt.",
}
RESTRICTED = {
    "en": "I can explain public information and website steps. I cannot access private profiles, "
    "matching results, invitations, conversations, credentials or internal instructions.",
    "de": "Ich kann öffentliche Informationen und die Website erklären. Ich habe keinen Zugriff "
    "auf private Profile, Matching-Ergebnisse, Einladungen, Chats, Zugangsdaten oder interne Anweisungen.",
}
UNAVAILABLE = {
    "en": "Public knowledge is temporarily unavailable. Please check https://vgu.edu.vn/.",
    "de": "Das öffentliche Wissen ist vorübergehend nicht verfügbar. Siehe https://vgu.edu.vn/.",
}


class InvalidQuestion(ValueError):
    """Sanitized validation error; contains no submitted text."""


class ChatbotService:
    def __init__(
        self,
        entries: tuple[Entry, ...] | None = None,
        provider: AnswerProvider | None = None,
        *,
        source_path: Path | None = None,
    ) -> None:
        # Retained only as an extension seam. Phase 3.1 never invokes any provider.
        self._provider = provider if provider is not None else DisabledProvider()
        # Explicit entry tuples retain the isolated legacy fixture/prototype contract.
        # Live API/CLI facts use the canonical guide, never stale manual guide copies.
        self.source_index = (
            SourceIndex(source_path or CANONICAL_SOURCE)
            if entries is None or source_path is not None
            else None
        )
        self._retriever: Retriever | None = None
        try:
            loaded = load_knowledge() if entries is None else entries
            self._retriever = Retriever(
                tuple(
                    entry
                    for entry in loaded
                    if not (self.source_index and entry.historical_reference)
                )
            )
        except KnowledgeUnavailable:
            pass

    def ask(self, text: str) -> Answer:
        try:
            question = Question(text=text)
        except ValidationError:
            raise InvalidQuestion(
                "Enter a question of 1–500 characters without control codes."
            ) from None
        detected = detect_language(question.text)
        # A verified FAQ never depends on canonical source I/O/parsing, including cold starts
        # and invalid guide updates. Private/instruction requests remain checked first.
        if (
            self.source_index
            and self._retriever
            and detected
            and len(split_questions(question.text)) == 1
            and confidence(question.text) == "high"
            and not self._restricted(question.text)
        ):
            direct = self._retriever.retrieve(question.text, detected)
            if direct:
                return self._verified(direct[0].entry, detected)
        snapshot = self.source_index.get() if self.source_index else None
        language = (
            language_for(question.text, snapshot.vocabulary if snapshot else frozenset())
            if self.source_index
            else detect_language(question.text)
        )
        if language is None:
            return Answer(language="und", outcome="choose_language", text=LANGUAGE_PROMPT)
        if self._restricted(question.text):
            return Answer(language=language, outcome="restricted", text=RESTRICTED[language])
        if self._retriever is None:
            return Answer(language=language, outcome="unavailable", text=UNAVAILABLE[language])
        if self.source_index:
            parts = split_questions(question.text)
            if len(parts) > 1:
                return self._source_parts(parts, language, snapshot)
            return self._source_answer(question.text, language, snapshot)
        hits = self._retriever.retrieve(question.text, language)
        if not hits:
            message = MULTI_FALLBACK if len(split_questions(question.text)) > 1 else FALLBACK
            if message is FALLBACK and self._retriever.ambiguous(question.text, language):
                message = CLARIFY
            return Answer(language=language, outcome="insufficient", text=message[language])
        parts = split_questions(question.text)
        selected = hits if len(parts) > 1 else hits[:1]
        missing = len(parts) > 1 and any(
            not self._retriever.retrieve(part, language) for part in parts
        )
        texts: list[str] = []
        citations: list[Citation] = []
        reserve = len(MULTI_FALLBACK[language]) + 2 if len(parts) > 1 else 0
        for hit in selected:
            entry = hit.entry
            text = self._select_answer(entry, language)
            if len("\n\n".join([*texts, text])) + reserve > MAX_ANSWER:
                missing = True
                break
            assert entry.authoritative or entry.historical_reference
            status = "historical_reference" if entry.historical_reference else entry.status
            assert status in {"verified_code", "verified_official", "historical_reference"}
            texts.append(text)
            citations.append(
                Citation(
                    entry_id=entry.id,
                    sources=entry.sources,
                    verified_on=entry.verified_on,
                    status=status,
                )
            )
        if not texts:
            return Answer(language=language, outcome="insufficient", text=FALLBACK[language])
        if missing:
            texts.append(MULTI_FALLBACK[language])
        return Answer(
            language=language,
            outcome="historical_reference"
            if any(citation.status == "historical_reference" for citation in citations)
            else "answer",
            text="\n\n".join(texts),
            citations=tuple(citations),
        )

    @staticmethod
    def _verified(entry: Entry, language: Language, *, guessed: bool = False) -> Answer:
        assert entry.status in {"verified_code", "verified_official"}
        return Answer(
            language=language,
            outcome="answer",
            text=(conditional(language) if guessed else "") + entry.localized(language).answer,
            citations=(
                Citation(
                    entry_id=entry.id,
                    sources=entry.sources,
                    verified_on=entry.verified_on,
                    status=entry.status,
                ),
            ),
        )

    def _source_answer(self, text: str, language: Language, snapshot: Snapshot | None) -> Answer:
        assert self._retriever is not None
        hits = self._retriever.retrieve(text, language)
        if hits and (confidence(text) == "high" or len(tokens(text)) > 1):
            return self._verified(hits[0].entry, language)
        if self._retriever.ambiguous(text, language):
            return Answer(language=language, outcome="clarification", text=CLARIFY[language])
        if not content_tokens(text):
            return Answer(language=language, outcome="clarification", text=CLARIFY[language])
        identified = topics(text)
        if len(identified) > 1:
            return Answer(language=language, outcome="clarification", text=CLARIFY[language])
        topic = next(iter(identified), "")
        # Short intent variants may select an existing FAQ only when no new factual constraint
        # is introduced. No vocabulary entry contains an answer or authorizes a new fact.
        if not sensitive_query(text) and not current_query(text):
            specification = next((intent for intent in INTENTS if intent.name == topic), None)
            if specification:
                candidates = [
                    entry
                    for entry in self._retriever.entries
                    if entry.id in specification.verified_ids
                    and content_tokens(text) - vocabulary(topic)
                    <= tokens(
                        entry.localized(language).answer
                        + " ".join(entry.localized(language).questions)
                    )
                ]
                if len(candidates) == 1:
                    return self._verified(
                        candidates[0], language, guessed=confidence(text) == "medium"
                    )
                if len(candidates) > 1:
                    return Answer(
                        language=language, outcome="clarification", text=CLARIFY[language]
                    )
        if snapshot is None:
            return Answer(language=language, outcome="unavailable", text=UNAVAILABLE[language])
        explicit_reference = reference_query(text)
        selected = select_passages(snapshot, text, reference=explicit_reference)
        if selected.ambiguous:
            return Answer(language=language, outcome="clarification", text=CLARIFY[language])
        if not selected.passages:
            return Answer(language=language, outcome="insufficient", text=FALLBACK[language])
        conflicted = any(p.policy == "conflicted" for p in selected.passages)
        citations = tuple(
            Citation(
                entry_id=p.id,
                sources=(
                    Source(
                        title="Canonical owner-provided guide",
                        reference=f"historical:systemPrompt.txt#L{p.start_line}-L{p.end_line}",
                    ),
                ),
                status="conflicted" if p.policy == "conflicted" else "owner_provided",
                verified_on=None,
                provenance=SourceProvenance(
                    sha256=snapshot.version,
                    start_line=p.start_line,
                    end_line=p.end_line,
                    section=p.section,
                ),
            )
            for p in selected.passages
        )
        if conflicted:
            caution = (
                "The owner-provided guide contains conflicting statements on this topic. I cannot confirm a current answer; please ask the relevant official service."
                if language == "en"
                else "Der bereitgestellte Leitfaden enthält widersprüchliche Angaben zu diesem Thema. Ich kann keine aktuelle Antwort bestätigen; bitte frage die zuständige offizielle Stelle."
            )
            if not explicit_reference:
                return Answer(
                    language=language, outcome="conflicted", text=caution, citations=citations
                )
        elif (sensitive_query(text) or current_query(text)) and not explicit_reference:
            caution = (
                "The guide contains unverified or time-sensitive information on this topic. Please check the current official service; I cannot confirm current rules, fees or availability."
                if language == "en"
                else "Der Leitfaden enthält hierzu unbestätigte oder zeitabhängige Angaben. Bitte prüfe die aktuellen Informationen beim offiziellen Dienst; Regeln, Gebühren und Verfügbarkeit kann ich nicht bestätigen."
            )
            return Answer(language=language, outcome="insufficient", text=caution)
        else:
            caution = (
                "Owner-provided student guide; not independently verified as current. Please confirm details locally. Original source passage:"
                if language == "en"
                else "Vom Eigentümer bereitgestellter Studierendenleitfaden; nicht unabhängig als aktuell bestätigt. Bitte prüfe Details vor Ort. Originaltext (unübersetzt; eine verlässliche deutsche Übersetzung liegt hier nicht vor):"
            )
        if sensitive_query(text) or any(p.policy == "sensitive" for p in selected.passages):
            caution += (
                " Historical reference only, not current medical, legal or financial advice."
                if language == "en"
                else " Nur historischer Quellenhinweis, keine aktuelle medizinische, rechtliche oder finanzielle Beratung."
            )
        elif any(p.time_sensitive for p in selected.passages):
            caution += (
                " Time-sensitive details in this passage are not confirmed as current."
                if language == "en"
                else " Zeitabhängige Angaben in dieser Passage sind nicht als aktuell bestätigt."
            )
        quote = "\n\n".join(f"[{p.section}]\n{p.text}" for p in selected.passages)
        prefix = conditional(language) if confidence(text) == "medium" else ""
        answer_text = prefix + caution + "\n\n" + quote
        if len(answer_text) > MAX_ANSWER:
            answer_text = (
                "The matching source passage is too long to quote safely here. Please name a specific service, item or detail."
                if language == "en"
                else "Die passende Quellpassage ist für ein sicheres Zitat hier zu lang. Bitte nenne einen bestimmten Dienst, Eintrag oder ein Detail."
            )
            return Answer(
                language=language,
                outcome="conflicted" if conflicted else "owner_provided",
                text=answer_text,
                citations=citations,
            )
        return Answer(
            language=language,
            outcome="conflicted" if conflicted else "owner_provided",
            text=answer_text,
            citations=citations,
        )

    def _source_parts(
        self, parts: tuple[str, ...], language: Language, snapshot: Snapshot | None
    ) -> Answer:
        if len(parts) > 3:
            return Answer(language=language, outcome="clarification", text=MULTI_FALLBACK[language])
        answers = [self._source_answer(part, language, snapshot) for part in parts]
        texts: list[str] = []
        citations: dict[str, Citation] = {}
        missing = False
        outcomes: set[str] = set()
        for answer in answers:
            if not answer.citations:
                missing = True
                continue
            identifiers = {citation.entry_id for citation in answer.citations}
            if identifiers <= citations.keys():
                continue
            if len(identifiers | citations.keys()) > 3:
                missing = True
                continue
            if len("\n\n".join([*texts, answer.text, MULTI_FALLBACK[language]])) > MAX_ANSWER:
                missing = True
                continue
            texts.append(answer.text)
            outcomes.add(answer.outcome)
            for citation in answer.citations:
                if len(citations) < 3:
                    citations[citation.entry_id] = citation
        if not texts:
            return Answer(language=language, outcome="clarification", text=MULTI_FALLBACK[language])
        if missing:
            texts.append(MULTI_FALLBACK[language])
        return Answer(
            language=language,
            outcome="conflicted"
            if "conflicted" in outcomes
            else "owner_provided"
            if "owner_provided" in outcomes
            else "answer",
            text="\n\n".join(texts),
            citations=tuple(citations.values()),
        )

    @staticmethod
    def _select_answer(entry: Entry, language: Language) -> str:
        return entry.localized(language).answer

    @staticmethod
    def _restricted(text: str) -> bool:
        # Defense in depth only. The actual boundary is no tools, no DB and no generation.
        normalized = text.casefold()
        return any(
            fragment in normalized
            for fragment in (
                "ignore previous",
                "ignore all",
                "system prompt",
                "systemprompt",
                "api key",
                "credentials",
                "password is",
                "show all users",
                "my invitation status",
                "my matching results",
                "read my chat",
                "private profile",
                "internal configuration",
                "ignoriere",
                "systemanweisungen",
                "zugangsdaten",
                "private daten",
                "mein einladungsstatus",
                "meine matching-ergebnisse",
                "meine chats",
            )
        )
