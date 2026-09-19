"""API validation and serialization schema package."""

from app.schemas.auth import (
    CsrfTokenResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegistrationRequest,
    RegistrationResponse,
    SanitizedUserResponse,
)
from app.schemas.profile import (
    OwnProfileResponse,
    ProfilePreferences,
    ProfileUpdate,
    WeeklyAvailability,
    WeeklyAvailabilitySlot,
)

__all__ = [
    "CsrfTokenResponse",
    "LoginRequest",
    "LoginResponse",
    "OwnProfileResponse",
    "ProfilePreferences",
    "ProfileUpdate",
    "RefreshResponse",
    "RegistrationRequest",
    "RegistrationResponse",
    "SanitizedUserResponse",
    "WeeklyAvailability",
    "WeeklyAvailabilitySlot",
]
