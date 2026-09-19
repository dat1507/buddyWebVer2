"""Bounded response contracts for coordinator profile inspection."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import StudentType, UserRole
from app.schemas.profile_photo import ProfilePhotoResponse


class AdminProfileSummary(BaseModel):
    """Small profile projection used by the admin user table."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str | None
    display_name: str | None
    student_type: StudentType | None


class AdminUserSummary(BaseModel):
    """Operational account state plus a minimal student-profile identity."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    profile: AdminProfileSummary | None


class AdminUserListResponse(BaseModel):
    """One stable, bounded page of student accounts."""

    model_config = ConfigDict(extra="forbid")

    items: list[AdminUserSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AdminProfileDetail(AdminProfileSummary):
    """Profile fields needed for coordinator support, excluding matching inputs."""

    nationality: str | None
    major: str | None
    study_year: int | None
    bio: str | None
    home_university: str | None
    arrival_date: date | None
    departure_date: date | None
    matching_opt_in: bool
    onboarding_completed_at: datetime | None
    avatar: ProfilePhotoResponse | None = None


class AdminUserDetail(BaseModel):
    """Audited coordinator view of one non-deleted student account."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    profile: AdminProfileDetail | None
