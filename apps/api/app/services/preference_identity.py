"""Deterministic identity and display-label handling for custom preferences."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Final

from app.models.profile_catalog import (
    MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
    MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH,
)

MAX_CUSTOM_PREFERENCE_INPUT_LENGTH: Final = MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH
_ALLOWED_CONTROL_WHITESPACE: Final = frozenset({"\t"})
_UNSAFE_UNICODE_CATEGORIES: Final = frozenset({"Cc", "Cf", "Cs"})


class PreferenceIdentityError(ValueError):
    """Raised when a custom preference cannot form a safe bounded identity."""


@dataclass(frozen=True, slots=True)
class PreferenceIdentity:
    """Validated user-facing label and its deterministic comparison key."""

    display_label: str
    normalized_key: str


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _contains_unsafe_control(value: str) -> bool:
    return any(
        unicodedata.category(character) in _UNSAFE_UNICODE_CATEGORIES
        and character not in _ALLOWED_CONTROL_WHITESPACE
        for character in value
    )


def _require_safe_text(value: str) -> None:
    if _contains_unsafe_control(value):
        raise PreferenceIdentityError("Preference label contains unsafe control characters.")


def normalize_preference_identity(value: str) -> PreferenceIdentity:
    """Return the display label and NFKC/whitespace/casefold identity for ``value``.

    The display label intentionally receives only whitespace cleanup, preserving the user's valid
    Unicode and casing. The comparison key follows the domain pipeline exactly: NFKC, trim and
    whitespace collapse, then Unicode casefold.
    """
    if len(value) > MAX_CUSTOM_PREFERENCE_INPUT_LENGTH:
        raise PreferenceIdentityError("Preference label exceeds the pre-normalization input limit.")
    _require_safe_text(value)

    display_label = _collapse_whitespace(value)
    if not display_label:
        raise PreferenceIdentityError("Preference label must not be empty.")
    if len(display_label) > MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH:
        raise PreferenceIdentityError("Preference display label is too long.")

    compatibility_form = unicodedata.normalize("NFKC", value)
    normalized_key = _collapse_whitespace(compatibility_form).casefold()
    _require_safe_text(display_label)
    _require_safe_text(normalized_key)
    if not normalized_key:
        raise PreferenceIdentityError("Preference normalized key must not be empty.")
    if len(normalized_key) > MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH:
        raise PreferenceIdentityError("Preference normalized key is too long.")

    return PreferenceIdentity(
        display_label=display_label,
        normalized_key=normalized_key,
    )


def normalize_preference_key(value: str) -> str:
    """Return only the validated deterministic key for duplicate checks and scoring."""
    return normalize_preference_identity(value).normalized_key
