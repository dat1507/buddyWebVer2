"""Privacy-safe contracts for ADMIN matching monitoring."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from app.models import StudentType
from app.schemas.matching import SafeInvitationProfile


class AdminInvitationStateCounts(BaseModel):
    """Effective invitation totals without participant or message data."""

    model_config = ConfigDict(extra="forbid")

    pending: int = Field(ge=0)
    accepted: int = Field(ge=0)
    declined: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    expired: int = Field(ge=0)


class AdminMatchingStats(BaseModel):
    """Operational matching totals derived from authoritative persisted state."""

    model_config = ConfigDict(extra="forbid")

    participant_count: int = Field(ge=0)
    verified_participant_count: int = Field(ge=0)
    active_match_count: int = Field(ge=0)
    zero_buddy_participant_count: int = Field(ge=0)
    invitations: AdminInvitationStateCounts


class AdminMatchingParticipantSummary(BaseModel):
    """Minimal participant identity and operational matching state."""

    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    display_name: StrictStr | None = Field(default=None, max_length=80)
    student_type: StudentType | None
    is_active: StrictBool
    email_verified: StrictBool
    matching_opt_in: StrictBool
    buddy_count: int = Field(ge=0)


class AdminMatchingParticipantListResponse(BaseModel):
    """One deterministic, bounded participant-monitoring page."""

    model_config = ConfigDict(extra="forbid")

    items: list[AdminMatchingParticipantSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=50)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AdminMatchingParticipantDetail(BaseModel):
    """Audited matching-safe profile detail without account or communication data."""

    model_config = ConfigDict(extra="forbid")

    profile: SafeInvitationProfile
    is_active: StrictBool
    email_verified: StrictBool
    matching_opt_in: StrictBool
    buddy_count: int = Field(ge=0)
