"""Server-only environment configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr

RUNTIME_URL_VARIABLE = "DATABASE_URL"
MIGRATION_URL_VARIABLE = "DATABASE_MIGRATION_URL"
CORS_ORIGINS_VARIABLE = "CORS_ALLOWED_ORIGINS"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class DatabaseConfigurationError(RuntimeError):
    """Raised when required server-only database configuration is invalid."""


class CorsConfigurationError(RuntimeError):
    """Raised when the credentialed CORS origin allowlist is unsafe or invalid."""


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


def _read_required_secret(variable_name: str) -> SecretStr:
    raw_value = os.getenv(variable_name)
    if raw_value is None or not raw_value.strip():
        raise DatabaseConfigurationError(
            f"Required server-only environment variable {variable_name} is not configured."
        )
    return SecretStr(raw_value)


def _normalize_cors_origin(origin: str) -> str:
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

    normalized_origins = tuple(_normalize_cors_origin(origin) for origin in configured_origins)
    return tuple(dict.fromkeys(normalized_origins))


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
