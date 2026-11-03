"""Search vocabulary only. These labels/synonyms never supply factual answers."""

import re
import unicodedata
from dataclasses import dataclass

from app.services.chatbot.language import detect_language, words
from app.services.chatbot.models import Language
from app.services.chatbot.retrieval import STOP_WORDS


@dataclass(frozen=True)
class Intent:
    name: str
    en: str
    de: str
    verified_ids: tuple[str, ...] = ()


INTENTS = (
    Intent(
        "food",
        "food eat eating hungry restaurant restaurants meal meals cafeteria canteen beverages coffee cafe",
        "essen hunger hungrig restaurant restaurants mensa kantine lebensmittel getränke kaffee café",
    ),
    Intent(
        "laundry",
        "laundry laundromat wash washing clothes",
        "wäscherei waescherei wäsche waesche waschen wäscheservice waescheservice waschservice kleidung",
    ),
    Intent(
        "transport",
        "transport transportation bus buses metro taxi motorbike travel",
        "transport verkehr bus busse u-bahn taxi motorrad anreise",
    ),
    Intent(
        "accommodation",
        "accommodation dorm dormitory room housing rents rent guesthouse apartment",
        "unterkunft wohnheim zimmer wohnen miete gästehaus",
        ("dormitory-information",),
    ),
    Intent(
        "library",
        "library printing print copying copy scanning scan",
        "bibliothek bücherei drucken druck kopieren scannen",
        ("library-services",),
    ),
    Intent(
        "sports",
        "sports sport swimming pool badminton basketball football tennis volleyball stadium",
        "sport sporthalle schwimmen schwimmbad badminton basketball fußball tennis volleyball stadion",
        ("sports-information",),
    ),
    Intent(
        "buddy-program",
        "ambassador volunteer buddy program",
        "botschafter freiwillige buddy programm",
        ("buddy-program-overview", "buddy-participation"),
    ),
    Intent(
        "registration",
        "register registration signup",
        "registrieren registrierung erstelle erstellen kontoerstellung",
        ("website-register",),
    ),
    Intent("login", "login signin", "anmelden anmeldung einloggen"),
    Intent(
        "verification",
        "verification verify confirmation",
        "verifizieren bestätigen verifizierung emailbestätigung",
        ("website-verification",),
    ),
    Intent(
        "matching",
        "matching recommendation match recommendations",
        "matching empfehlung empfehlungen partner",
        ("website-matching",),
    ),
    Intent(
        "invitations",
        "invitation invitations invite",
        "einladung einladungen einladen",
        ("website-invitations",),
    ),
    Intent(
        "chat",
        "chat conversation conversations chatting",
        "chat chats unterhaltung nachrichten",
        ("website-buddy-chat",),
    ),
    Intent(
        "events",
        "event events activities",
        "veranstaltung veranstaltungen aktivitäten",
        ("website-events",),
    ),
    Intent(
        "campus",
        "facilities facility services resources campus",
        "einrichtungen einrichtung dienste angebote campus",
        ("campus-resources",),
    ),
    Intent(
        "groceries",
        "groceries grocery supermarket supermarkets shopping convenience necessities store",
        "einkaufen einkauf supermarkt supermärkte laden geschäft",
    ),
    Intent(
        "internet",
        "internet wifi wi-fi sim telecom mobile connectivity",
        "internet wlan sim mobilfunk handytarif",
    ),
    Intent(
        "contacts",
        "contact contacts office affairs scholarship scholarships career careers",
        "kontakt kontakte büro stipendium stipendien karriere",
        ("international-help",),
    ),
    Intent(
        "health",
        "health hospital medical medicine pharmacy insurance vaccine vaccinations",
        "gesundheit krankenhaus medizin apotheke versicherung impfung impfungen",
    ),
    Intent(
        "arrival",
        "arrival visa passport immigration customs residence",
        "ankunft visum reisepass einwanderung zoll aufenthalt",
    ),
    Intent(
        "banking",
        "bank banks banking atm currency monetary withdraw money exchange",
        "bank banken geldautomat währung geld wechselkurs",
    ),
)

# Grammatical scaffolding; specific places, dates, negation and factual constraints remain.
FILLER = STOP_WORDS | words(
    "there somewhere anywhere any around near nearby outside inside place places located looking look want need would like some something mention mentions guide previous historical source student campus vgu can have has habe einen etwas nähe nahe außerhalb innerhalb beim brauche möchte ort orten leitfaden studienführer studierendenleitfaden sagt nennt erwähnt irgendwelche irgendwo um gibt es"
)
FILLER = FILLER | words(
    "service services be must long much lange viel viele habe haben einen einem einer mentioned information details tell show does say facility facilities please gern gerne kannst kann man"
)
FILLER = FILLER - {"campus"}  # Keep campus available when it is the only identifiable topic.
TYPO = {
    "validity": "valid",
    "gültig": "valid",
    "tor": "gate",
    "tors": "gate",
    "tore": "gate",
    "straße": "street",
    "strasse": "street",
    "restarant": "restaurant",
    "restraunt": "restaurant",
    "restuarant": "restaurant",
    "laundary": "laundry",
    "waescherei": "wäscherei",
    "waesche": "wäsche",
    "waescheservice": "wäscheservice",
    "bibliothekk": "bibliothek",
    "registartion": "registration",
}


def tokens(text: str) -> frozenset[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    normalized = unicodedata.normalize("NFC", text).casefold()
    normalized = re.sub(r"\b(?:how much|wie viel)\b", "price", normalized)
    normalized = re.sub(r"\b(?:log|sign)[ -]+in\b", "login", normalized)
    normalized = re.sub(r"\bsign[ -]+up\b", "signup", normalized)
    normalized = re.sub(
        r"\b(?:fees|fee|costs|cost|prices|preise|preis|gebühren|gebühr|kosten)\b",
        "price",
        normalized,
    )
    return frozenset(TYPO.get(word, word) for word in words(normalized))


def topics(text: str) -> frozenset[str]:
    query = tokens(text)
    found = {intent.name for intent in INTENTS if query & tokens(intent.en + " " + intent.de)}
    # Context words must not compete with a more specific service.
    if len(found) > 1:
        found.discard("campus")
    if "buddy-program" in found and len(found) > 1:
        found.discard("buddy-program")
    return frozenset(found)


def language_for(text: str, available: frozenset[str] = frozenset()) -> Language | None:
    detected = detect_language(text)
    if detected is not None:
        return detected
    query = tokens(text)
    en = frozenset().union(*(tokens(intent.en) for intent in INTENTS))
    de = frozenset().union(*(tokens(intent.de) for intent in INTENTS))
    if query & (de - en) and not query & (en - de):
        return "de"
    if query & (en - de) and not query & (de - en):
        return "en"
    # Shared Restaurant/Taxi and source-only proper names use English, never a browser locale.
    if len(query) <= 3 and query and (query <= en | de or query <= available):
        return "en"
    return None


def content_tokens(text: str) -> frozenset[str]:
    query = tokens(text) - FILLER
    # Campus is a location scaffold when another subject is present.
    return query - {"campus"} if len(query) > 1 else query


def vocabulary(topic: str) -> frozenset[str]:
    return next(
        (tokens(intent.en + " " + intent.de) for intent in INTENTS if intent.name == topic),
        frozenset(),
    )


def confidence(text: str) -> str:
    return "high" if tokens(text) & words("where how which what wo wie welche was") else "medium"


def sensitive_query(text: str) -> bool:
    return bool(
        re.search(
            r"\b(visa|passport|immigration|customs|legal|law|insurance|health|medical|hospital|medicine|allerg\w*|vaccin\w*|malaria|visum|reisepass|gesetz\w*|versicherung|gesund\w*|medizin\w*|kranken\w*|impf\w*|pflicht\w*)\b",
            text.casefold(),
        )
    )


def current_query(text: str) -> bool:
    return bool(
        tokens(text)
        & words(
            "current currently now today latest open hours price prices fee fees cost costs requirements required mandatory curfew deadline insurance derzeit aktuell aktuelle aktuellen heute jetzt geöffnet öffnungszeiten preis preise gebühr gebühren kostet kosten vorgeschrieben erforderlich"
        )
    )


def reference_query(text: str) -> bool:
    return bool(
        tokens(text)
        & words(
            "historical previous guide source document leitfaden studienführer studierendenleitfaden historisch historischen quelle dokument"
        )
    )


def conditional(language: Language) -> str:
    return (
        "If you mean this topic, the available source says:\n\n"
        if language == "en"
        else "Falls du dieses Thema meinst, steht in der verfügbaren Quelle:\n\n"
    )
