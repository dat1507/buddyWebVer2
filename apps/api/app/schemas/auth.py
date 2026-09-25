"""Authentication transport request and response schemas."""

from datetime import datetime
from typing import Final, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator

from app.models import User, UserRole
from app.services.auth import EmailValidationError, canonicalize_email
from app.services.passwords import BCRYPT_MAX_PASSWORD_BYTES

MIN_REGISTRATION_PASSWORD_CHARACTERS: Final = 8


class CsrfTokenResponse(BaseModel):
    """Signed CSRF value that the frontend retains only in memory."""

    csrf_token: str


class RegistrationRequest(BaseModel):
    """Untrusted public registration input with no client-controlled role."""

    model_config = ConfigDict(extra="forbid")

    email: StrictStr
    password: StrictStr = Field(repr=False)
    consent: StrictBool

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        try:
            return canonicalize_email(value)
        except EmailValidationError as error:
            raise ValueError("Email address is invalid.") from error

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < MIN_REGISTRATION_PASSWORD_CHARACTERS:
            raise ValueError(
                f"Password must contain at least {MIN_REGISTRATION_PASSWORD_CHARACTERS} characters."
            )
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} UTF-8 bytes.")
        return value

    @field_validator("consent")
    @classmethod
    def require_consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Consent is required to register.")
        return value


class RegistrationResponse(BaseModel):
    """Minimal response that discloses no account or authentication material."""

    status: Literal["registered"] = "registered"


class EmailVerificationRequestResponse(BaseModel):
    """Generic response shared by first request, resend, and already-verified USERs."""

    status: Literal["verification_requested"] = "verification_requested"


class EmailVerificationConfirmRequest(BaseModel):
    """Opaque one-use token from the verification link; redirects are not client-controlled."""

    model_config = ConfigDict(extra="forbid")

    token: StrictStr = Field(
        repr=False,
        description="Opaque URL-safe email-verification token.",
        json_schema_extra={"writeOnly": True},
    )


class EmailVerificationConfirmResponse(BaseModel):
    """Successful confirmation with one fixed allowlisted frontend destination."""

    status: Literal["email_verified"] = "email_verified"
    redirect_to: Literal["/user"] = "/user"


class EmailChangeRequest(BaseModel):
    """Current-password authorization and the replacement canonical address."""

    model_config = ConfigDict(extra="forbid")

    new_email: StrictStr
    current_password: StrictStr = Field(
        repr=False,
        json_schema_extra={"writeOnly": True},
    )

    @field_validator("new_email")
    @classmethod
    def validate_new_email(cls, value: str) -> str:
        try:
            return canonicalize_email(value)
        except EmailValidationError as error:
            raise ValueError("Email address is invalid.") from error


class LoginRequest(BaseModel):
    """Untrusted credentials for both student and administrator login pages."""

    model_config = ConfigDict(extra="forbid")

    email: StrictStr
    password: StrictStr = Field(repr=False)


class SanitizedUserResponse(BaseModel):
    """Account fields safe for browser routing and session presentation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    email_verified: bool
    email_verified_at: datetime | None

    @classmethod
    def from_user(cls, user: User) -> Self:
        """Project authoritative USER verification without changing ADMIN authentication."""
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            email_verified=user.is_current_email_verified,
            email_verified_at=user.email_verified_at,
        )


class EmailChangeResponse(BaseModel):
    """Updated session projection after relocking the replacement address."""

    status: Literal["email_changed"] = "email_changed"
    user: SanitizedUserResponse


class LoginResponse(BaseModel):
    """Successful login payload with no access or refresh credential material."""

    user: SanitizedUserResponse
    csrf_token: str = Field(repr=False)


class RefreshResponse(BaseModel):
    """Successful rotation payload with current user state and no JWT material."""

    user: SanitizedUserResponse
    csrf_token: str = Field(repr=False)
