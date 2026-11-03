"""Bounded local chatbot resources. No shared storage or private-user dependencies."""

import hashlib
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chatbot import ChatbotResponse, ErrorCode, public_answer
from app.services.chatbot.service import ChatbotService


class ChatbotConfigurationError(Exception):
    """Safe configuration failure; never retain a submitted environment value."""


class ChatbotSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    enabled: bool = False
    ai_enabled: Literal[False] = False
    client_requests: int = Field(default=30, ge=1, le=600)
    global_requests: int = Field(default=300, ge=1, le=5000)
    window_seconds: int = Field(default=60, ge=10, le=3600)
    max_clients: int = Field(default=2048, ge=1, le=10000)
    max_question_chars: int = Field(default=500, ge=1, le=500)
    max_body_bytes: int = Field(default=4096, ge=1024, le=16384)
    concurrency: int = Field(default=2, ge=1, le=4)
    deadline_ms: int = Field(default=2000, ge=50, le=5000)


@lru_cache(maxsize=1)
def get_chatbot_settings() -> ChatbotSettings:
    try:

        def flag(name: str) -> bool:
            value = os.getenv(name, "false")
            if value not in {"true", "false"}:
                raise ValueError
            return value == "true"

        values: dict[str, object] = {
            "enabled": flag("CHATBOT_API_ENABLED"),
            "ai_enabled": flag("CHATBOT_AI_ENABLED"),
        }
        for field in (
            "client_requests",
            "global_requests",
            "window_seconds",
            "max_clients",
            "max_question_chars",
            "max_body_bytes",
            "concurrency",
            "deadline_ms",
        ):
            value = os.getenv(f"CHATBOT_{field.upper()}")
            if value is not None:
                values[field] = int(value)
        return ChatbotSettings.model_validate(values)
    except (ValueError, TypeError):
        raise ChatbotConfigurationError("Chatbot configuration is unavailable.") from None


class ChatbotFailure(Exception):
    def __init__(self, status: int, code: ErrorCode, retry_after: int | None = None) -> None:
        self.status = status
        self.code = code
        self.retry_after = retry_after
        super().__init__(code)


class Lease:
    """One admission; a timed-out running worker retains it until actual completion."""

    def __init__(self, slots: threading.BoundedSemaphore) -> None:
        self._slots = slots
        self._lock = threading.Lock()
        self._released = False
        self.transferred = False

    def release(self) -> None:
        with self._lock:
            if not self._released:
                self._released = True
                self._slots.release()

    def transfer(self, future: Future[ChatbotResponse | None]) -> None:
        self.transferred = True
        future.add_done_callback(lambda _future: self.release())


class ChatbotRuntime:
    def __init__(self, settings: ChatbotSettings) -> None:
        self.settings = settings
        self._key = os.urandom(32)
        self._lock = threading.Lock()
        self._clients: dict[bytes, tuple[float, int]] = {}
        self._global_started = time.monotonic()
        self._global_count = 0
        self._slots = threading.BoundedSemaphore(settings.concurrency)
        self._executor = ThreadPoolExecutor(
            max_workers=settings.concurrency, thread_name_prefix="chatbot"
        )
        self._service_lock = threading.Lock()
        self.service: ChatbotService | None = None

    def admit(self, identifier: str) -> Lease:
        now = time.monotonic()
        key = hashlib.blake2b(identifier.encode(), key=self._key, digest_size=16).digest()
        window = self.settings.window_seconds
        with self._lock:
            if now >= self._global_started + window:
                self._global_started, self._global_count = now, 0
            if self._global_count >= self.settings.global_requests:
                raise ChatbotFailure(
                    429, "rate_limited", max(1, ceil(self._global_started + window - now))
                )
            # Explicit capacity and TTL; never evict a live client to reset its quota.
            self._clients = {id: bucket for id, bucket in self._clients.items() if bucket[0] > now}
            expiry, count = self._clients.get(key, (now + window, 0))
            if count >= self.settings.client_requests:
                raise ChatbotFailure(429, "rate_limited", max(1, ceil(expiry - now)))
            if key not in self._clients and len(self._clients) >= self.settings.max_clients:
                raise ChatbotFailure(503, "overloaded", 1)
            self._clients[key] = (expiry, count + 1)
            self._global_count += 1
        if not self._slots.acquire(blocking=False):
            raise ChatbotFailure(503, "overloaded", 1)
        return Lease(self._slots)

    def _work(self, question: str) -> ChatbotResponse | None:
        try:
            with self._service_lock:
                if self.service is None:
                    self.service = ChatbotService()
                service = self.service
            result = public_answer(service.ask(question))
            if len(result.model_dump_json().encode("utf-8")) > 16384:
                return None
            return result
        except Exception:
            # Never propagate user text, paths, provider diagnostics or internal exceptions.
            return None

    def submit(self, question: str, lease: Lease) -> Future[ChatbotResponse | None]:
        future = self._executor.submit(self._work, question)
        lease.transfer(future)
        return future

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._clients.clear()


_runtime: ChatbotRuntime | None = None
_runtime_lock = threading.Lock()


def get_chatbot_runtime(settings: ChatbotSettings) -> ChatbotRuntime:
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = ChatbotRuntime(settings)
        return _runtime


def close_chatbot_runtime() -> None:
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            _runtime.close()
            _runtime = None
    get_chatbot_settings.cache_clear()
