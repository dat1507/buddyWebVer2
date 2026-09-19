"""Server-only environment configuration."""

from __future__ import annotations

import base64
import binascii
import os
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretBytes, SecretStr, field_validator

RUNTIME_URL_VARIABLE = "DATABASE_URL"
MIGRATION_URL_VARIABLE = "DATABASE_MIGRATION_URL"
CORS_ORIGINS_VARIABLE = "CORS_ALLOWED_ORIGINS"
AUTH_JWT_SECRET_VARIABLE = "AUTH_JWT_SECRET"
AUTH_CSRF_SECRET_VARIABLE = "AUTH_CSRF_SECRET"
AUTH_COOKIE_SECURE_VARIABLE = "AUTH_COOKIE_SECURE"
SUPABASE_URL_VARIABLE = "SUPABASE_URL"
SUPABASE_SECRET_KEY_VARIABLE = "SUPABASE_SECRET_KEY"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class DatabaseConfigurationError(RuntimeError):
    """Raised when required server-only database configuration is invalid."""


class CorsConfigurationError(RuntimeError):
    """Raised when the credentialed CORS origin allowlist is unsafe or invalid."""


class AuthConfigurationError(RuntimeError):
    """Raised when server-only authentication configuration is unsafe or invalid."""


class StorageConfigurationError(RuntimeError):
    """Raised when server-only Supabase Storage configuration is unsafe or invalid."""


class RuntimeDatabaseSettings(BaseModel):
    """Least-privilege credential used only by the FastAPI process."""

    model_config = ConfigDict(frozen=True)

    url: SecretStr = Field(repr=False)


class MigrationDatabaseSettings(BaseModel):
    """Privileged direct credential used only by Alembic."""

    model_config = ConfigDict(frozen=True)

    url: SecretStr = Field(repr=False)


class CorsSettings(BaseModel):
    """Credentialed browser origins accepted by the API."""

    model_config = ConfigDict(frozen=True)

    allowed_origins: tuple[str, ...]


class AuthTokenSettings(BaseModel):
    """JWT signing key and environment-specific cookie transport policy."""

    model_config = ConfigDict(frozen=True)

    signing_key: SecretBytes = Field(repr=False)
    secure_cookies: bool = True

    @field_validator("signing_key")
    @classmethod
    def validate_signing_key_length(cls, value: SecretBytes) -> SecretBytes:
        """Keep direct construction as safe as environment-backed construction."""
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT signing key must contain at least 32 bytes.")
        return value


class CsrfSettings(BaseModel):
    """Signed CSRF token, cookie, and exact browser-origin policy."""

    model_config = ConfigDict(frozen=True)

    signing_key: SecretBytes = Field(repr=False)
    secure_cookies: bool = True
    trusted_origins: tuple[str, ...]

    @field_validator("signing_key")
    @classmethod
    def validate_signing_key_length(cls, value: SecretBytes) -> SecretBytes:
        """Reject weak secrets even when settings are constructed directly."""
        if len(value.get_secret_value()) < 32:
            raise ValueError("CSRF signing key must contain at least 32 bytes.")
        return value

    @field_validator("trusted_origins")
    @classmethod
    def validate_trusted_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Keep direct construction as strict as environment-backed construction."""
        if not value:
            raise ValueError("At least one trusted CSRF origin is required.")
        try:
            normalized = tuple(normalize_http_origin(origin) for origin in value)
        except CorsConfigurationError as error:
            raise ValueError("Trusted CSRF origins must be exact HTTP origins.") from error
        return tuple(dict.fromkeys(normalized))


class StorageSettings(BaseModel):
    """Trusted Supabase endpoint and secret key used only by the FastAPI process."""

    model_config = ConfigDict(frozen=True)

    url: str
    secret_key: SecretStr = Field(repr=False)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            return normalize_supabase_url(value)
        except StorageConfigurationError as error:
            raise ValueError("Supabase URL is unsafe or invalid.") from error

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        normalized = value.get_secret_value().strip()
        if not normalized:
            raise ValueError("Supabase secret key must not be empty.")
        return SecretStr(normalized)


def _read_required_secret(variable_name: str) -> SecretStr:
    raw_value = os.getenv(variable_name)
    if raw_value is None or not raw_value.strip():
        raise DatabaseConfigurationError(
            f"Required server-only environment variable {variable_name} is not configured."
        )
    return SecretStr(raw_value)


def normalize_http_origin(origin: str) -> str:
    """Return one canonical HTTP origin or reject unsafe origin syntax."""
    if "*" in origin:
        raise CorsConfigurationError("CORS origins must not contain wildcards.")

    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise CorsConfigurationError("CORS origins must use an absolute HTTP or HTTPS origin.")
    if parsed.username is not None or parsed.password is not None:
        raise CorsConfigurationError("CORS origins must not contain credentials.")
    if parsed.path or parsed.query or parsed.fragment:
        raise CorsConfigurationError("CORS origins must not contain a path, query, or fragment.")

    try:
        port = parsed.port
    except ValueError as error:
        raise CorsConfigurationError("CORS origin contains an invalid port.") from error

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"

    default_port = 80 if parsed.scheme == "http" else 443
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{parsed.scheme}://{host}{port_suffix}"


def _read_cors_origins() -> tuple[str, ...]:
    raw_value = os.getenv(CORS_ORIGINS_VARIABLE)
    if raw_value is None:
        return DEFAULT_CORS_ORIGINS

    configured_origins = tuple(item.strip() for item in raw_value.split(","))
    if not configured_origins or any(not item for item in configured_origins):
        raise CorsConfigurationError(
            f"{CORS_ORIGINS_VARIABLE} must be a comma-separated list of origins."
        )

    normalized_origins = tuple(normalize_http_origin(origin) for origin in configured_origins)
    return tuple(dict.fromkeys(normalized_origins))


def _read_urlsafe_signing_key(variable_name: str) -> SecretBytes:
    raw_value = os.getenv(variable_name)
    if raw_value is None or not raw_value:
        raise AuthConfigurationError(
            f"Required server-only environment variable {variable_name} is not configured."
        )

    try:
        urlsafe_characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_="
        if any(character not in urlsafe_characters for character in raw_value):
            raise ValueError
        encoded = raw_value.encode("ascii")
        padded = encoded + (b"=" * (-len(encoded) % 4))
        signing_key = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as error:
        raise AuthConfigurationError(f"{variable_name} must be a URL-safe base64 value.") from error

    if len(signing_key) < 32:
        raise AuthConfigurationError(f"{variable_name} must decode to at least 32 random bytes.")
    return SecretBytes(signing_key)


def _read_secure_cookie_policy() -> bool:
    raw_value = os.getenv(AUTH_COOKIE_SECURE_VARIABLE)
    if raw_value is None:
        return True

    normalized = raw_value.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise AuthConfigurationError(f"{AUTH_COOKIE_SECURE_VARIABLE} must be exactly true or false.")


def normalize_supabase_url(value: str) -> str:
    """Return one trusted project origin, permitting plain HTTP only on localhost."""
    parsed = urlsplit(value.strip())
    is_local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme != "https" and not is_local_http:
        raise StorageConfigurationError(
            f"{SUPABASE_URL_VARIABLE} must use HTTPS except for localhost development."
        )
    if parsed.hostname is None or parsed.username is not None or parsed.password is not None:
        raise StorageConfigurationError(f"{SUPABASE_URL_VARIABLE} must be an absolute project URL.")
    if parsed.query or parsed.fragment:
        raise StorageConfigurationError(
            f"{SUPABASE_URL_VARIABLE} must not contain a query or fragment."
        )
    if parsed.path not in {"", "/"}:
        raise StorageConfigurationError(f"{SUPABASE_URL_VARIABLE} must not contain a path.")

    try:
        port = parsed.port
    except ValueError as error:
        raise StorageConfigurationError(
            f"{SUPABASE_URL_VARIABLE} contains an invalid port."
        ) from error

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port_suffix = f":{port}" if port is not None else ""
    return f"{parsed.scheme}://{host}{port_suffix}"


def _read_supabase_url() -> str:
    raw_value = os.getenv(SUPABASE_URL_VARIABLE)
    if raw_value is None or not raw_value.strip():
        raise StorageConfigurationError(
            f"Required server-only environment variable {SUPABASE_URL_VARIABLE} is not configured."
        )
    return normalize_supabase_url(raw_value)


@lru_cache(maxsize=1)
def get_runtime_database_settings() -> RuntimeDatabaseSettings:
    """Load the application credential without reading migration credentials."""
    return RuntimeDatabaseSettings(url=_read_required_secret(RUNTIME_URL_VARIABLE))


@lru_cache(maxsize=1)
def get_migration_database_settings() -> MigrationDatabaseSettings:
    """Load the Alembic credential without exposing it to application settings."""
    return MigrationDatabaseSettings(url=_read_required_secret(MIGRATION_URL_VARIABLE))


@lru_cache(maxsize=1)
def get_cors_settings() -> CorsSettings:
    """Load and validate the exact browser origins allowed to send credentials."""
    return CorsSettings(allowed_origins=_read_cors_origins())


@lru_cache(maxsize=1)
def get_auth_token_settings() -> AuthTokenSettings:
    """Load the dedicated JWT secret and production-safe cookie policy."""
    return AuthTokenSettings(
        signing_key=_read_urlsafe_signing_key(AUTH_JWT_SECRET_VARIABLE),
        secure_cookies=_read_secure_cookie_policy(),
    )


@lru_cache(maxsize=1)
def get_csrf_settings() -> CsrfSettings:
    """Load the dedicated CSRF secret and exact browser request policy."""
    return CsrfSettings(
        signing_key=_read_urlsafe_signing_key(AUTH_CSRF_SECRET_VARIABLE),
        secure_cookies=_read_secure_cookie_policy(),
        trusted_origins=_read_cors_origins(),
    )


@lru_cache(maxsize=1)
def get_storage_settings() -> StorageSettings:
    """Load the server-only Storage credential without exposing it to browser settings."""
    raw_key = os.getenv(SUPABASE_SECRET_KEY_VARIABLE)
    if raw_key is None or not raw_key.strip():
        raise StorageConfigurationError(
            f"Required server-only environment variable {SUPABASE_SECRET_KEY_VARIABLE} "
            "is not configured."
        )
    return StorageSettings(url=_read_supabase_url(), secret_key=SecretStr(raw_key.strip()))
