"""Existing Event deletion integration without changing Event API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recap import Recap
from app.services.events import EventDependencyConflictError


class RecapEventRelations:
    async def published_recap_boundary(
        self, session: AsyncSession, event_id: UUID
    ) -> datetime | None:
        # Recaps may describe historical dates independently: they do not constrain Event schedules.
        return None

    async def detach_for_delete(self, session: AsyncSession, event_id: UUID) -> None:
        # Never silently convert an active restricted recap into standalone public content.
        related = await session.scalar(
            select(Recap.id)
            .where(Recap.related_event_id == event_id, Recap.deleted_at.is_(None))
            .limit(1)
        )
        if related is not None:
            raise EventDependencyConflictError("Event has related recap records.")
        # Deleted recap tombstones cannot be republished; detach their obsolete FK so deleting
        # a recap does not permanently block the original Event's existing deletion workflow.
        await session.execute(
            update(Recap)
            .where(Recap.related_event_id == event_id, Recap.deleted_at.is_not(None))
            .values(related_event_id=None)
        )


RECAP_EVENT_RELATIONS = RecapEventRelations()
