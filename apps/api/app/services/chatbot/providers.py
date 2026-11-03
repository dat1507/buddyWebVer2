"""Future provider seam. No network implementation or credentials in Phase 3.1."""

from dataclasses import dataclass, field
from typing import Protocol

from app.services.chatbot.models import MAX_ANSWER, MAX_CONTEXT, MAX_QUESTION, Language


@dataclass(frozen=True)
class ProviderRequest:
    question: str = field(repr=False)
    language: Language
    context: str = field(repr=False)
    instructions: str = field(default="", repr=False)
    max_input_tokens: int = 8192
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not 0 < len(self.question) <= MAX_QUESTION or len(self.context) > MAX_CONTEXT:
            raise ValueError("Provider input exceeds bounds.")
        if not 256 <= self.max_input_tokens <= 8192 or not 1 <= self.max_output_tokens <= 2048:
            raise ValueError("Provider token budget is invalid.")
        if self.input_token_upper_bound > self.max_input_tokens:
            raise ValueError("Provider input exceeds conservative token budget.")

    @property
    def input_token_upper_bound(self) -> int:
        # Conservative UTF-8 byte bound for the shortlisted byte-tokenized Llama models,
        # plus explicit protocol/special-token reserve. Not measured model token usage.
        return (
            sum(
                len(value.encode("utf-8"))
                for value in (
                    self.question,
                    self.context,
                    self.instructions,
                )
            )
            + 256
        )


@dataclass(frozen=True)
class ProviderAnswer:
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        if not 0 < len(self.text) <= MAX_ANSWER:
            raise ValueError("Provider output exceeds bounds.")


class ProviderUnavailable(Exception):
    """Safe disabled/unavailable signal; never expose vendor diagnostics."""


class ProviderQuotaExceeded(ProviderUnavailable):
    """Quota exhaustion must fall back without retries."""


class ProviderCredentialsMissing(ProviderUnavailable):
    """No credential discovery or billing activation is attempted."""


class AnswerProvider(Protocol):
    async def generate(self, request: ProviderRequest) -> ProviderAnswer: ...


class DisabledProvider:
    async def generate(self, request: ProviderRequest) -> ProviderAnswer:
        raise ProviderUnavailable("AI generation is disabled.")
