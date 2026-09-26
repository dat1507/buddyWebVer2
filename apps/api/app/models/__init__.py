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
    MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
    MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
    MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH,
    Activity,
    Interest,
    Language,
    LanguageProficiency,
    PreferenceKind,
    ProfileActivity,
    ProfileCustomPreference,
    ProfileInterest,
    ProfileLanguage,
)
from app.models.refresh_session import RefreshSession
from app.models.transactional_outbox import TransactionalOutbox
from app.models.user import User, UserRole

__all__ = (
    "Activity",
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
    "MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH",
    "MAX_CUSTOM_PREFERENCE_INPUT_LENGTH",
    "MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH",
    "PreferenceKind",
    "ProfileActivity",
    "ProfileCustomPreference",
    "ProfilePhoto",
    "ProfilePhotoProcessingStatus",
    "ProfileInterest",
    "ProfileLanguage",
    "RefreshSession",
    "StudentProfile",
    "StudentType",
    "TransactionalOutbox",
    "User",
    "UserRole",
    "derive_event_phase",
)
