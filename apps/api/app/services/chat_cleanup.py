"""Bounded, atomic physical cleanup for authoritatively expired Buddy messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DEFAULT_CHAT_CLEANUP_BATCH_SIZE: Final = 20
MAX_CHAT_CLEANUP_BATCH_SIZE: Final = 100


class ChatCleanupValidationError(ValueError):
    """Raised when cleanup receives an unsafe operational bound or timestamp."""


@dataclass(frozen=True, slots=True)
class ChatCleanupReport:
    """Safe aggregate result from one atomic cleanup batch."""

    selected: int
    deleted: int


def _utc_instant(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ChatCleanupValidationError("Chat cleanup timestamp must be timezone-aware.")
    return value.astimezone(UTC)


async def cleanup_expired_buddy_message_batch(
    session: AsyncSession,
    *,
    batch_size: int = DEFAULT_CHAT_CLEANUP_BATCH_SIZE,
    cleanup_now: datetime | None = None,
) -> tuple[UUID, ...]:
    """Delete one deterministic due batch inside the caller transaction.

    Production calls omit ``cleanup_now`` so PostgreSQL captures one
    ``statement_timestamp()``. Tests may supply a past, timezone-aware instant;
    the database function rejects future values as defense in depth.
    """
    if not 1 <= batch_size <= MAX_CHAT_CLEANUP_BATCH_SIZE:
        raise ChatCleanupValidationError("Chat cleanup batch size is outside the supported range.")

    parameters: dict[str, object] = {"batch_size": batch_size}
    if cleanup_now is None:
        statement = text(
            "SELECT message_id FROM app_private.cleanup_expired_buddy_messages(:batch_size)"
        )
    else:
        parameters["cleanup_now"] = _utc_instant(cleanup_now)
        statement = text(
            "SELECT message_id FROM "
            "app_private.cleanup_expired_buddy_messages(:batch_size, :cleanup_now)"
        )

    result = await session.execute(statement, parameters)
    return tuple(cast(UUID, message_id) for message_id in result.scalars().all())


async def process_chat_cleanup_batch(
    factory: async_sessionmaker[AsyncSession],
    *,
    batch_size: int = DEFAULT_CHAT_CLEANUP_BATCH_SIZE,
    cleanup_now: datetime | None = None,
) -> ChatCleanupReport:
    """Commit one short cleanup transaction; roll back all work on failure."""
    async with factory() as session:
        try:
            deleted_ids = await cleanup_expired_buddy_message_batch(
                session,
                batch_size=batch_size,
                cleanup_now=cleanup_now,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    count = len(deleted_ids)
    return ChatCleanupReport(selected=count, deleted=count)
