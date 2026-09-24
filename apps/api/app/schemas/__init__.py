"""API validation and serialization schema package."""

from app.schemas.admin_user import (
    AdminProfileDetail,
    AdminProfileSummary,
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserSummary,
)
from app.schemas.auth import (
    CsrfTokenResponse,
    EmailVerificationRequestResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegistrationRequest,
    RegistrationResponse,
    SanitizedUserResponse,
)
from app.schemas.event import (
    AdminEventResponse,
    EventDraftCreate,
    EventDraftUpdate,
    EventStatusUpdate,
)
from app.schemas.profile import (
    OwnProfileResponse,
    ProfilePreferences,
    ProfileUpdate,
    WeeklyAvailability,
    WeeklyAvailabilitySlot,
)
from app.schemas.profile_catalog import (
    CatalogLocale,
    InterestCatalogItem,
    InterestCatalogResponse,
    LanguageCatalogItem,
    LanguageCatalogResponse,
    ProfileInterestSelectionResponse,
    ProfileInterestUpdate,
    ProfileLanguageSelection,
    ProfileLanguageSelectionResponse,
    ProfileLanguageUpdate,
)
from app.schemas.profile_completion import (
    MatchingIneligibilityReason,
    ProfileCompletionResponse,
    ProfileCompletionStatus,
    ProfileMissingField,
)
from app.schemas.profile_photo import ProfilePhotoResponse, ProfilePhotoUrlResponse

__all__ = [
    "AdminEventResponse",
    "AdminProfileDetail",
    "AdminProfileSummary",
    "AdminUserDetail",
    "AdminUserListResponse",
    "AdminUserSummary",
    "CsrfTokenResponse",
    "EmailVerificationRequestResponse",
    "CatalogLocale",
    "InterestCatalogItem",
    "InterestCatalogResponse",
    "LanguageCatalogItem",
    "LanguageCatalogResponse",
    "LoginRequest",
    "LoginResponse",
    "EventDraftCreate",
    "EventDraftUpdate",
    "EventStatusUpdate",
    "OwnProfileResponse",
    "MatchingIneligibilityReason",
    "ProfileCompletionResponse",
    "ProfileCompletionStatus",
    "ProfileMissingField",
    "ProfilePreferences",
    "ProfileInterestSelectionResponse",
    "ProfileInterestUpdate",
    "ProfileLanguageSelection",
    "ProfileLanguageSelectionResponse",
    "ProfileLanguageUpdate",
    "ProfilePhotoResponse",
    "ProfilePhotoUrlResponse",
    "ProfileUpdate",
    "RefreshResponse",
    "RegistrationRequest",
    "RegistrationResponse",
    "SanitizedUserResponse",
    "WeeklyAvailability",
    "WeeklyAvailabilitySlot",
]
