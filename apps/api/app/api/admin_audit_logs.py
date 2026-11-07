"""Read-only, bounded audit history for administrators."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.core.database import get_database_session
from app.models import AuditLog, User, UserRole

Category = Literal[
    "events", "recaps", "users", "matching", "semesters", "knowledge", "settings", "other"
]
Period = Literal["today", "week", "month", "custom"]
Resource = Literal[
    "event",
    "recap",
    "student_profile",
    "profile_photo",
    "semester_operation",
    "managed_faq",
    "site_theme",
    "other",
]
AuditStatus = Literal["DRAFT", "PUBLISHED", "CANCELLED", "ARCHIVED"]

_ACTIONS = frozenset(
    {
        "site_theme.publish",
        "knowledge.create",
        "knowledge.update",
        "knowledge.publish",
        "knowledge.unpublish",
        "knowledge.restore",
        "event.create",
        "event.update",
        "event.delete",
        "event.status_update",
        "event.media_replace",
        "event.media_update",
        "event.media_delete",
        "profile.admin_read",
        "profile_photo.admin_read",
        "matching.participant_admin_read",
        "recap.create",
        "recap.update",
        "recap.status",
        "recap.photos_update",
        "recap.photo_upload",
        "recap.photo_delete",
        "recap.delete",
        "recap.cleanup",
        "recap.automatic_eviction",
        "semester.reset_execute",
        "semester.restore_execute",
    }
)
_RESOURCES: dict[str, Resource] = {
    "event": "event",
    "recap": "recap",
    "student_profile": "student_profile",
    "profile_photo": "profile_photo",
    "semester_operation": "semester_operation",
    "managed_faq": "managed_faq",
    "site_theme": "site_theme",
}
_STATUSES: dict[str, AuditStatus] = {
    "DRAFT": "DRAFT",
    "PUBLISHED": "PUBLISHED",
    "CANCELLED": "CANCELLED",
    "ARCHIVED": "ARCHIVED",
}
_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
_PRIVATE = {"Cache-Control": "private, no-store", "Pragma": "no-cache"}
require_admin = require_role(UserRole.ADMIN)
router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit-logs"])

# Matching and Users share the same stored resource type.
_category = case(
    (
        and_(
            AuditLog.resource_type == "student_profile",
            AuditLog.action == "matching.participant_admin_read",
        ),
        "matching",
    ),
    (AuditLog.resource_type.in_(("student_profile", "profile_photo")), "users"),
    (AuditLog.resource_type == "event", "events"),
    (AuditLog.resource_type == "recap", "recaps"),
    (AuditLog.resource_type == "semester_operation", "semesters"),
    (AuditLog.resource_type == "managed_faq", "knowledge"),
    (AuditLog.resource_type == "site_theme", "settings"),
    else_="other",
)


class AuditActivity(BaseModel):
    id: UUID
    created_at: datetime
    admin_id: UUID
    admin_email: str | None
    action: str
    category: Category
    resource_type: Resource
    resource_id: UUID | None
    before_status: AuditStatus | None
    after_status: AuditStatus | None


class AuditPage(BaseModel):
    items: list[AuditActivity]
    page: int
    page_size: int
    total: int
    total_pages: int


class ActorOption(BaseModel):
    id: UUID
    email: str


class ActorPage(BaseModel):
    items: list[ActorOption]
    has_more: bool


def _date_range(
    period: Period,
    start: date | None,
    end: date | None,
    today: date,
) -> tuple[datetime, datetime]:
    if period != "custom":
        start = today - timedelta(days={"today": 0, "week": 6, "month": 29}[period])
        end = today
    if (
        start is None
        or end is None
        or end < start
        or end >= date.max
        or start.year < 2000
        or (end - start).days >= 366
    ):
        raise HTTPException(422, "Choose a valid date range of up to 366 days.", headers=_PRIVATE)
    return (
        datetime.combine(start, time.min, _ZONE),
        datetime.combine(end + timedelta(days=1), time.min, _ZONE),
    )


def _status(resource: Resource, value: str | None) -> AuditStatus | None:
    if value is None or resource not in {"event", "recap"}:
        return None
    if (resource == "event" and value == "ARCHIVED") or (
        resource == "recap" and value == "CANCELLED"
    ):
        return None
    return _STATUSES.get(value)


@router.get("/actors")
async def list_actors(
    response: Response,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
) -> ActorPage:
    """Read a page of recorded administrators, including inactive Admin accounts."""
    response.headers.update(_PRIVATE)
    size = 100
    has_activity = select(AuditLog.id).where(AuditLog.admin_id == User.id).exists()
    rows = (
        await session.execute(
            select(User.id, User.email)
            .where(User.role == UserRole.ADMIN, has_activity)
            .order_by(User.email, User.id)
            .offset((page - 1) * size)
            .limit(size + 1)
        )
    ).all()
    return ActorPage(
        items=[ActorOption(id=row.id, email=row.email) for row in rows[:size]],
        has_more=len(rows) > size,
    )


@router.get("")
async def list_audit_logs(
    response: Response,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    admin_id: UUID | None = None,
    category: Category | None = None,
    period: Period = "month",
    start: date | None = None,
    end: date | None = None,
) -> AuditPage:
    """Use recorded actor IDs and project only typed, allowlisted detail fields."""
    response.headers.update(_PRIVATE)
    lower, upper = _date_range(period, start, end, datetime.now(UTC).astimezone(_ZONE).date())
    filters = [AuditLog.created_at >= lower, AuditLog.created_at < upper]
    if admin_id is not None:
        filters.append(AuditLog.admin_id == admin_id)
    if category is not None:
        filters.append(_category == category)

    total = await session.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    rows = (
        await session.execute(
            select(
                AuditLog.id,
                AuditLog.created_at,
                AuditLog.admin_id,
                User.email,
                AuditLog.action,
                _category.label("category"),
                AuditLog.resource_type,
                AuditLog.resource_id,
                AuditLog.old_value["status"].astext.label("before_status"),
                AuditLog.new_value["status"].astext.label("after_status"),
                AuditLog.old_value["version"].astext.label("before_version"),
                AuditLog.new_value["version"].astext.label("after_version"),
            )
            .outerjoin(User, and_(User.id == AuditLog.admin_id, User.role == UserRole.ADMIN))
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = []
    for row in rows:
        resource = _RESOURCES.get(row.resource_type, "other")
        action = row.action if row.action in _ACTIONS else "unknown"
        before = _status(resource, row.before_status)
        after = _status(resource, row.after_status)
        if (
            action == "event.status_update"
            and resource == "event"
            and after
            in {
                "PUBLISHED",
                "CANCELLED",
            }
        ):
            versions = (row.before_version, row.after_version)
            if (before is not None and before != after) or (
                all(
                    isinstance(v, str) and v.isascii() and v.isdecimal() and len(v) <= 10
                    for v in versions
                )
                and int(versions[1]) == int(versions[0]) + 1
            ):
                action = f"{action}.{after}"
        items.append(
            AuditActivity(
                id=row.id,
                created_at=row.created_at,
                admin_id=row.admin_id,
                admin_email=row.email,
                action=action,
                category=row.category,
                resource_type=resource,
                resource_id=row.resource_id
                if resource in {"event", "recap", "semester_operation", "managed_faq"}
                else None,
                before_status=before,
                after_status=after,
            )
        )
    return AuditPage(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )
