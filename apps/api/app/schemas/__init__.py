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
from app.schemas.profile_photo import ProfilePhotoResponse, ProfilePhotoUrlResponse

__all__ = [
    "AdminProfileDetail",
    "AdminProfileSummary",
    "AdminUserDetail",
    "AdminUserListResponse",
    "AdminUserSummary",
    "CsrfTokenResponse",
    "CatalogLocale",
    "InterestCatalogItem",
    "InterestCatalogResponse",
    "LanguageCatalogItem",
    "LanguageCatalogResponse",
    "LoginRequest",
    "LoginResponse",
    "OwnProfileResponse",
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
