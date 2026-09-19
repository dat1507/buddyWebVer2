"""Least-data queries for authorized coordinator profile inspection."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import StudentProfile, User, UserRole
from app.schemas.admin_user import (
    AdminProfileDetail,
    AdminProfileSummary,
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserSummary,
)


def _active_profile_join() -> ColumnElement[bool]:
    return and_(
        StudentProfile.user_id == User.id,
        StudentProfile.deleted_at.is_(None),
    )


def _student_accounts() -> tuple[ColumnElement[bool], ...]:
    return (
        User.role == UserRole.USER,
        User.deleted_at.is_(None),
    )


def _escaped_contains(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search_filter(search: str | None) -> ColumnElement[bool] | None:
    normalized = search.strip() if search is not None else ""
    if not normalized:
        return None
    pattern = _escaped_contains(normalized)
    return or_(
        User.email.ilike(pattern, escape="\\"),
        StudentProfile.full_name.ilike(pattern, escape="\\"),
        StudentProfile.display_name.ilike(pattern, escape="\\"),
    )


async def list_admin_users(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
) -> AdminUserListResponse:
    """Return a deterministic page selected from allowlisted account/profile columns only."""
    count_statement = (
        select(func.count(User.id))
        .select_from(User)
        .outerjoin(StudentProfile, _active_profile_join())
        .where(*_student_accounts())
    )
    count_filter = _search_filter(search)
    if count_filter is not None:
        count_statement = count_statement.where(count_filter)
    total = int(await session.scalar(count_statement) or 0)

    statement = (
        select(
            User.id,
            User.email,
            User.role,
            User.is_active,
            User.email_verified,
            User.created_at,
            StudentProfile.id,
            StudentProfile.full_name,
            StudentProfile.display_name,
            StudentProfile.student_type,
        )
        .select_from(User)
        .outerjoin(StudentProfile, _active_profile_join())
        .where(*_student_accounts())
    )
    search_filter = _search_filter(search)
    if search_filter is not None:
        statement = statement.where(search_filter)
    statement = (
        statement.order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(statement)).tuples().all()

    items = [
        AdminUserSummary(
            id=user_id,
            email=email,
            role=role,
            is_active=is_active,
            email_verified=email_verified,
            created_at=created_at,
            profile=(
                AdminProfileSummary(
                    id=profile_id,
                    full_name=full_name,
                    display_name=display_name,
                    student_type=student_type,
                )
                if profile_id is not None
                else None
            ),
        )
        for (
            user_id,
            email,
            role,
            is_active,
            email_verified,
            created_at,
            profile_id,
            full_name,
            display_name,
            student_type,
        ) in rows
    ]
    return AdminUserListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


async def get_admin_user_detail(
    session: AsyncSession,
    user_id: UUID,
) -> AdminUserDetail | None:
    """Read one student through an explicit projection that omits sensitive matching data."""
    statement = (
        select(
            User.id,
            User.email,
            User.role,
            User.is_active,
            User.email_verified,
            User.created_at,
            StudentProfile.id,
            StudentProfile.full_name,
            StudentProfile.display_name,
            StudentProfile.student_type,
            StudentProfile.nationality,
            StudentProfile.major,
            StudentProfile.study_year,
            StudentProfile.bio,
            StudentProfile.home_university,
            StudentProfile.arrival_date,
            StudentProfile.departure_date,
            StudentProfile.matching_opt_in,
            StudentProfile.onboarding_completed_at,
        )
        .select_from(User)
        .outerjoin(StudentProfile, _active_profile_join())
        .where(User.id == user_id, *_student_accounts())
    )
    row = (await session.execute(statement)).tuples().one_or_none()
    if row is None:
        return None

    (
        account_id,
        email,
        role,
        is_active,
        email_verified,
        created_at,
        profile_id,
        full_name,
        display_name,
        student_type,
        nationality,
        major,
        study_year,
        bio,
        home_university,
        arrival_date,
        departure_date,
        matching_opt_in,
        onboarding_completed_at,
    ) = row
    profile = None
    if profile_id is not None:
        profile = AdminProfileDetail(
            id=profile_id,
            full_name=full_name,
            display_name=display_name,
            student_type=student_type,
            nationality=nationality,
            major=major,
            study_year=study_year,
            bio=bio,
            home_university=home_university,
            arrival_date=arrival_date,
            departure_date=departure_date,
            matching_opt_in=matching_opt_in,
            onboarding_completed_at=onboarding_completed_at,
        )
    return AdminUserDetail(
        id=account_id,
        email=email,
        role=role,
        is_active=is_active,
        email_verified=email_verified,
        created_at=created_at,
        profile=profile,
    )
