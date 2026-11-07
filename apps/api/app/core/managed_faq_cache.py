"""Per-process managed publication snapshots with bounded asynchronous refresh."""

import asyncio
import time

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import DatabaseConfigurationError
from app.core.database import get_session_factory
from app.services.chatbot.knowledge import KnowledgeUnavailable
from app.services.chatbot.managed import KnowledgeIssue, ManagedFaq, validate_snapshot
from app.services.managed_faq import generation, published_snapshot

REFRESH_SECONDS = 15
RETRY_SECONDS = 3


class ManagedFaqCache:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._until = 0.0
        self._generation: int | None = None
        self._entries: tuple[ManagedFaq, ...] = ()

    async def get(self, timeout: float) -> tuple[ManagedFaq, ...]:
        if time.monotonic() < self._until:
            return self._entries
        try:
            async with asyncio.timeout(timeout):
                async with self._lock:
                    if time.monotonic() < self._until:
                        return self._entries
                    try:
                        async with get_session_factory()() as session:
                            current = await generation(session)
                            if current != self._generation:
                                version, entries = await published_snapshot(session)
                                self._entries = await asyncio.to_thread(validate_snapshot, entries)
                                self._generation = version
                        self._until = time.monotonic() + REFRESH_SECONDS
                    except (
                        DatabaseConfigurationError,
                        SQLAlchemyError,
                        KnowledgeIssue,
                        KnowledgeUnavailable,
                        OSError,
                    ):
                        self._entries = ()
                        self._generation = None
                        self._until = time.monotonic() + RETRY_SECONDS
                    return self._entries
        except TimeoutError:
            return ()
