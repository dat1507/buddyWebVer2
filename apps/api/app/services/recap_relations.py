"""Existing Event deletion integration without changing Event API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
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
        # Keep historical provenance, including deleted recap tombstones, instead of silently
        # converting restricted Event content into a standalone public recap.
        related = await session.scalar(
            select(Recap.id).where(Recap.related_event_id == event_id).limit(1)
        )
        if related is not None:
            raise EventDependencyConflictError("Event has related recap records.")


RECAP_EVENT_RELATIONS = RecapEventRelations()
