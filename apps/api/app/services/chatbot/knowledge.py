"""Load only packaged public JSON; never accept user-selected paths or remote content."""

from pathlib import Path

from pydantic import TypeAdapter

from app.services.chatbot.language import words
from app.services.chatbot.models import Entry

DATA_DIRECTORY = Path(__file__).with_name("data")
MAX_ENTRIES = 200
MAX_FILE_BYTES = 512_000


class KnowledgeUnavailable(Exception):
    """Sanitized knowledge availability failure."""


def load_knowledge(directory: Path = DATA_DIRECTORY) -> tuple[Entry, ...]:
    try:
        entries: list[Entry] = []
        files = sorted(directory.glob("*.json"))
        if not files or len(files) > 20:
            raise ValueError("Knowledge files missing or excessive.")
        for path in files:
            with path.open("rb") as source:
                data = source.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("Knowledge file too large.")
            entries.extend(TypeAdapter(list[Entry]).validate_json(data))
        if not entries or len(entries) > MAX_ENTRIES:
            raise ValueError("Knowledge size invalid.")
        if len({entry.id for entry in entries}) != len(entries):
            raise ValueError("Duplicate knowledge identifiers.")
        for language in ("en", "de"):
            seen: dict[frozenset[str], str] = {}
            for entry in entries:
                if not entry.authoritative:
                    continue
                for question in entry.localized(language).questions:
                    key = words(question)
                    if key in seen and seen[key] != entry.id:
                        raise ValueError("Conflicting verified FAQ aliases.")
                    seen[key] = entry.id
        return tuple(entries)
    except (OSError, ValueError):
        raise KnowledgeUnavailable("Public knowledge is unavailable.") from None
