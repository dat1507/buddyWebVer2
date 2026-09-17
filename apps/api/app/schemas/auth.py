"""Authentication transport request and response schemas."""

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator

from app.services.auth import EmailValidationError, canonicalize_email
from app.services.passwords import BCRYPT_MAX_PASSWORD_BYTES

MIN_REGISTRATION_PASSWORD_CHARACTERS: Final = 15


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
