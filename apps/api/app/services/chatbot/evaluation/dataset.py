"""Versioned synthetic cases; expected facts are IDs, never invented answer text."""

from pathlib import Path
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from app.services.chatbot.models import Contract, Entry

CASE_FILE = Path(__file__).with_name("cases.json")


class Case(Contract):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    category: Literal["A", "B", "C", "D", "E", "F"]
    question: JsonValue = Field(repr=False)
    expected_language: Literal["en", "de", "und"]
    expected_outcome: Literal["answer", "insufficient", "choose_language", "restricted", "invalid"]
    expected_ids: tuple[str, ...] = Field(max_length=3)
    requires_uncertainty: bool = False


class Dataset(Contract):
    version: Literal[1]
    provenance: str
    cases: tuple[Case, ...] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def unique_ids(self) -> "Dataset":
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation case IDs.")
        return self


def load_cases(entries: tuple[Entry, ...], path: Path = CASE_FILE) -> tuple[Case, ...]:
    cases = Dataset.model_validate_json(path.read_bytes()).cases
    verified = {entry.id for entry in entries if entry.authoritative}
    for case in cases:
        if not set(case.expected_ids) <= verified:
            raise ValueError("Expected facts must reference existing verified entries.")
        if bool(case.expected_ids) != (case.expected_outcome == "answer"):
            raise ValueError("Only answer cases may expect facts.")
    return cases
