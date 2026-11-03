"""Conservative lexical EN/DE detection, independent of the browser locale."""

import re
import unicodedata

from app.services.chatbot.models import Language


def words(text: str) -> frozenset[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    # Keep identifiers such as D9 distinct from D8; digits must not disappear.
    return frozenset(re.findall(r"[^\W_]+", normalized))


EN_MARKERS = words(
    "what how where when which who can does do is are the my I me help please "
    "register verify send view find join about hours price cost need available"
)
DE_MARKERS = words(
    "was wie wo wann welche wer kann können funktioniert ist sind der die das ein eine "
    "mein meine ich mir bitte hilfe anmelden registrieren bestätigen senden ansehen "
    "finden gibt teilnehmen über öffnungszeiten preis kostet brauche verfügbar"
)


def detect_language(text: str) -> Language | None:
    tokens = words(text)
    en = len(tokens & EN_MARKERS)
    de = len(tokens & DE_MARKERS)
    if en and de and max(en, de) < 2 * min(en, de):
        # Balanced mixed-language questions require clarification. Allow UI loanwords.
        return None
    if de > en:
        return "de"
    if en > de:
        return "en"
    return None
