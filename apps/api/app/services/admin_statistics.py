"""Read-only aggregates without profile joins or pagination."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventStatus, User, UserRole
from app.schemas.admin_statistics import AdminEventStatistics, AdminUserStatistics


async def count_admin_users(session: AsyncSession) -> AdminUserStatistics:
    observed_at = datetime.now(UTC)
    total = await session.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.USER,
            User.deleted_at.is_(None),
        )
    )
    return AdminUserStatistics(total_users=int(total or 0), observed_at=observed_at)


async def count_admin_events(session: AsyncSession) -> AdminEventStatistics:
    observed_at = datetime.now(UTC)
    row = (
        await session.execute(
            select(
                func.count(Event.id),
                func.count(Event.id).filter(Event.start_date > observed_at),
            ).where(
                Event.status == EventStatus.PUBLISHED,
                Event.published_at.is_not(None),
                Event.deleted_at.is_(None),
            )
        )
    ).one()
    return AdminEventStatistics(
        published_events=row[0], upcoming_events=row[1], observed_at=observed_at
    )
