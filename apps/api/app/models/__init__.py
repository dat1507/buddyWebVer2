"""Persistence model package."""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.email_verification import EmailVerificationToken
from app.models.event import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventPhase,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    EventVisibility,
    derive_event_phase,
)
from app.models.profile import (
    ProfilePhoto,
    ProfilePhotoProcessingStatus,
    StudentProfile,
    StudentType,
)
from app.models.profile_catalog import (
    Interest,
    Language,
    LanguageProficiency,
    ProfileInterest,
    ProfileLanguage,
)
from app.models.refresh_session import RefreshSession
from app.models.user import User, UserRole

__all__ = (
    "AuditLog",
    "Base",
    "EmailVerificationToken",
    "Event",
    "EventMedia",
    "EventMediaProcessingStatus",
    "EventMediaUsage",
    "EventPhase",
    "EventRegistration",
    "EventRegistrationStatus",
    "EventStatus",
    "EventVisibility",
    "Interest",
    "Language",
    "LanguageProficiency",
    "ProfilePhoto",
    "ProfilePhotoProcessingStatus",
    "ProfileInterest",
    "ProfileLanguage",
    "RefreshSession",
    "StudentProfile",
    "StudentType",
    "User",
    "UserRole",
    "derive_event_phase",
)
