"""Transactional creation and defensive redaction of admin audit records."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Final
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User, UserRole
from app.models.audit_log import JSONValue

MAX_AUDIT_IDENTIFIER_LENGTH: Final = 100
REDACTED_AUDIT_VALUE: Final = "[REDACTED]"
_MAX_PAYLOAD_DEPTH: Final = 12

_SENSITIVE_KEY_PARTS: Final = (
    "password",
    "passphrase",
    "secret",
    "token",
    "credential",
    "authorization",
    "cookie",
    "csrf",
    "privatekey",
    "apikey",
    "signedurl",
    "signature",
    "databaseurl",
    "redisuri",
    "connectionstring",
)
_PROFILE_CONTENT_KEYS: Final = frozenset(
    {
        "profile",
        "profiledata",
        "email",
        "fullname",
        "displayname",
        "bio",
        "nationality",
        "contact",
        "phone",
        "address",
        "birthdate",
        "major",
        "studyyear",
        "interests",
        "hobbies",
        "languages",
        "availability",
        "schedule",
        "preferences",
        "avatar",
        "avatarurl",
        "photo",
        "photourl",
    }
)
_PROFILE_RESOURCE_TYPES: Final = frozenset(
    {"account", "profile", "profilephoto", "studentprofile", "user", "userprofile"}
)
_PROFILE_OPERATIONAL_KEYS: Final = frozenset(
    {
        "completionstatus",
        "deletedat",
        "emailverified",
        "isactive",
        "matchingeligible",
        "role",
        "status",
    }
)
_SIGNED_URL_QUERY_KEYS: Final = frozenset(
    {
        "credential",
        "jwt",
        "key",
        "sig",
        "signature",
        "token",
        "xamzcredential",
        "xamzsignature",
        "xgoogcredential",
        "xgoogsignature",
        "xgoogsignedheaders",
    }
)


class AuditLogValidationError(ValueError):
    """Raised before persistence when an audit event violates the safe contract."""


class AuditLogActorError(PermissionError):
    """Raised when the supplied actor is not a current active Admin."""


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _is_profile_content_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return normalized in _PROFILE_CONTENT_KEYS or any(
        normalized.endswith(profile_key) for profile_key in _PROFILE_CONTENT_KEYS
    )


def _is_signed_url(value: str) -> bool:
    query = urlsplit(value).query
    if not query:
        return False
    return any(
        _normalized_key(key) in _SIGNED_URL_QUERY_KEYS or _is_sensitive_key(key)
        for key, _value in parse_qsl(query, keep_blank_values=True)
    )


def _sanitize_value(
    value: object,
    *,
    profile_restricted: bool,
    seen: set[int],
    depth: int,
) -> JSONValue:
    if depth > _MAX_PAYLOAD_DEPTH:
        raise AuditLogValidationError("Audit payload nesting is too deep.")
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and _is_signed_url(value):
            return REDACTED_AUDIT_VALUE
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AuditLogValidationError("Audit payload numbers must be finite.")
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _sanitize_value(
            value.value,
            profile_restricted=profile_restricted,
            seen=seen,
            depth=depth + 1,
        )

    container_id = id(value)
    if container_id in seen:
        raise AuditLogValidationError("Audit payloads cannot contain cycles.")
    if isinstance(value, Mapping):
        seen.add(container_id)
        try:
            sanitized: dict[str, JSONValue] = {}
            for key, nested_value in value.items():
                if not isinstance(key, str):
                    raise AuditLogValidationError("Audit payload object keys must be strings.")
                normalized = _normalized_key(key)
                if (
                    _is_sensitive_key(key)
                    or _is_profile_content_key(key)
                    or (profile_restricted and normalized not in _PROFILE_OPERATIONAL_KEYS)
                ):
                    sanitized[key] = REDACTED_AUDIT_VALUE
                else:
                    sanitized[key] = _sanitize_value(
                        nested_value,
                        profile_restricted=profile_restricted,
                        seen=seen,
                        depth=depth + 1,
                    )
            return sanitized
        finally:
            seen.remove(container_id)
    if isinstance(value, (list, tuple)):
        seen.add(container_id)
        try:
            return [
                _sanitize_value(
                    item,
                    profile_restricted=profile_restricted,
                    seen=seen,
                    depth=depth + 1,
                )
                for item in value
            ]
        finally:
            seen.remove(container_id)
    raise AuditLogValidationError(
        f"Audit payload type {type(value).__name__!r} is not JSON-compatible."
    )


def _sanitize_mapping(
    value: Mapping[str, object] | None,
    *,
    profile_restricted: bool,
) -> dict[str, JSONValue] | None:
    if value is None:
        return None
    sanitized = _sanitize_value(
        value,
        profile_restricted=profile_restricted,
        seen=set(),
        depth=0,
    )
    if not isinstance(sanitized, dict):  # pragma: no cover - Mapping guarantees this invariant.
        raise AuditLogValidationError("Audit payload must be an object.")
    return sanitized


def _validated_identifier(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_AUDIT_IDENTIFIER_LENGTH:
        raise AuditLogValidationError(
            f"Audit {field} must contain 1-{MAX_AUDIT_IDENTIFIER_LENGTH} characters."
        )
    return normalized


async def record_audit_log(
    session: AsyncSession,
    actor: User,
    *,
    action: str,
    resource_type: str,
    resource_id: UUID,
    old_value: Mapping[str, object] | None = None,
    new_value: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
) -> AuditLog:
    """Stage one redacted record; the caller commits it with the owning mutation.

    This function deliberately never commits or rolls back. A flush failure propagates so an
    endpoint cannot report a successful mutation without its required audit record.
    """
    if (
        actor.role is not UserRole.ADMIN
        or not actor.is_active
        or actor.deleted_at is not None
        or not isinstance(actor.id, UUID)
    ):
        raise AuditLogActorError("A current active Admin is required for audit attribution.")
    if not isinstance(resource_id, UUID):
        raise AuditLogValidationError("Audit resource_id must be a UUID.")

    normalized_action = _validated_identifier(action, "action")
    normalized_resource_type = _validated_identifier(resource_type, "resource_type")
    profile_restricted = (
        _normalized_key(normalized_resource_type) in _PROFILE_RESOURCE_TYPES
    )
    audit_log = AuditLog(
        admin_id=actor.id,
        action=normalized_action,
        resource_type=normalized_resource_type,
        resource_id=resource_id,
        old_value=_sanitize_mapping(old_value, profile_restricted=profile_restricted),
        new_value=_sanitize_mapping(new_value, profile_restricted=profile_restricted),
        context=_sanitize_mapping(metadata, profile_restricted=False) or {},
    )
    session.add(audit_log)
    await session.flush()
    return audit_log
