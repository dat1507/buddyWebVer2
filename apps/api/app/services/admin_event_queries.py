"""Bounded Admin Event inventory and detail queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import Event, EventPhase, EventStatus, EventVisibility
from app.schemas.event import AdminEventListResponse, AdminEventResponse
from app.services.events import project_admin_event


class AdminEventQueryValidationError(ValueError):
    """Raised when an Admin inventory query exceeds its bounded contract."""


@dataclass(frozen=True, slots=True)
class AdminEventFilters:
    """Allowlisted filters for the Admin Event inventory."""

    page: int = 1
    page_size: int = 20
    search: str | None = None
    status: EventStatus | None = None
    visibility: EventVisibility | None = None
    phase: EventPhase | None = None
    from_instant: datetime | None = None
    to_instant: datetime | None = None


def _require_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdminEventQueryValidationError(f"{field_name} must be timezone-aware.")
    return value


def _validated(filters: AdminEventFilters) -> AdminEventFilters:
    if filters.page < 1 or not 1 <= filters.page_size <= 100:
        raise AdminEventQueryValidationError("Admin Event pagination is out of bounds.")
    search = filters.search.strip() if filters.search is not None else None
    if filters.search is not None and (not search or len(search) > 100):
        raise AdminEventQueryValidationError("Admin Event search is invalid.")
    if (filters.from_instant is None) != (filters.to_instant is None):
        raise AdminEventQueryValidationError("Admin Event date range requires both from and to.")
    if filters.from_instant is not None and filters.to_instant is not None:
        start = _require_aware(filters.from_instant, field_name="Admin Event range start")
        end = _require_aware(filters.to_instant, field_name="Admin Event range end")
        if end <= start:
            raise AdminEventQueryValidationError("Admin Event date range is invalid.")
    return AdminEventFilters(
        page=filters.page,
        page_size=filters.page_size,
        search=search,
        status=filters.status,
        visibility=filters.visibility,
        phase=filters.phase,
        from_instant=filters.from_instant,
        to_instant=filters.to_instant,
    )


def _clauses(
    filters: AdminEventFilters,
    *,
    now: datetime,
) -> tuple[ColumnElement[bool], ...]:
    clauses: list[ColumnElement[bool]] = [Event.deleted_at.is_(None)]
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        clauses.append(
            or_(
                Event.title_en.ilike(pattern),
                Event.title_de.ilike(pattern),
                Event.category.ilike(pattern),
                Event.organizer.ilike(pattern),
            )
        )
    if filters.status is not None:
        clauses.append(Event.status == filters.status)
    if filters.visibility is not None:
        clauses.append(Event.visibility == filters.visibility)
    if filters.phase is EventPhase.UPCOMING:
        clauses.append(Event.start_date > now)
    elif filters.phase is EventPhase.ONGOING:
        clauses.append(and_(Event.start_date <= now, Event.end_date > now))
    elif filters.phase is EventPhase.COMPLETED:
        clauses.append(Event.end_date <= now)
    if filters.from_instant is not None and filters.to_instant is not None:
        clauses.extend(
            (
                Event.start_date < filters.to_instant,
                Event.end_date > filters.from_instant,
            )
        )
    return tuple(clauses)


async def list_admin_events(
    session: AsyncSession,
    *,
    filters: AdminEventFilters,
    now: datetime | None = None,
) -> AdminEventListResponse:
    """Return all editorial states with stable pagination and no creator identity leak."""
    checked = _validated(filters)
    reference_time = _require_aware(now or datetime.now(UTC), field_name="Query time")
    clauses = _clauses(checked, now=reference_time)
    total = int(
        cast(
            int,
            await session.scalar(select(func.count()).select_from(Event).where(*clauses)),
        )
        or 0
    )
    result = await session.scalars(
        select(Event)
        .where(*clauses)
        .order_by(Event.updated_at.desc(), Event.id.asc())
        .offset((checked.page - 1) * checked.page_size)
        .limit(checked.page_size)
    )
    return AdminEventListResponse(
        # Keep the returned phase consistent with the instant used by the phase filter. Otherwise
        # a request crossing a schedule boundary can return an item outside its requested phase.
        items=[project_admin_event(event, at=reference_time) for event in result.all()],
        page=checked.page,
        page_size=checked.page_size,
        total=total,
        total_pages=(total + checked.page_size - 1) // checked.page_size,
    )


async def get_admin_event_detail(
    session: AsyncSession,
    event_id: UUID,
) -> AdminEventResponse | None:
    """Return one active Event through the existing allowlisted Admin projection."""
    event = cast(
        Event | None,
        await session.scalar(select(Event).where(Event.id == event_id, Event.deleted_at.is_(None))),
    )
    return project_admin_event(event) if event is not None else None
