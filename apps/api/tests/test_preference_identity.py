"""PREF-002 deterministic custom-preference identity contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from app.models import (
    MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
    MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH,
    PreferenceKind,
)
from app.services.preference_identity import (
    MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
    PreferenceIdentity,
    PreferenceIdentityError,
    normalize_preference_identity,
    normalize_preference_key,
)


@pytest.mark.parametrize(
    ("source", "display_label", "normalized_key"),
    [
        ("Photography", "Photography", "photography"),
        ("photography", "photography", "photography"),
        ("Straße", "Straße", "strasse"),
        ("STRASSE", "STRASSE", "strasse"),
        ("Ｐｈｏｔｏｇｒａｐｈｙ", "Ｐｈｏｔｏｇｒａｐｈｙ", "photography"),
        ("oﬃce", "oﬃce", "office"),
        ("  Street   Photography  ", "Street Photography", "street photography"),
        ("Street\tPhotography", "Street Photography", "street photography"),
        ("Street\u00a0\u2003Photography", "Street Photography", "street photography"),
        ("Tiếng Việt", "Tiếng Việt", "tiếng việt"),
    ],
)
def test_normalization_golden_vectors(
    source: str,
    display_label: str,
    normalized_key: str,
) -> None:
    identity = normalize_preference_identity(source)

    assert identity == PreferenceIdentity(
        display_label=display_label,
        normalized_key=normalized_key,
    )
    assert normalize_preference_key(source) == normalized_key


def test_unicode_casefold_is_stronger_than_lowercase() -> None:
    assert "Straße".lower() != "STRASSE".lower()
    assert normalize_preference_key("Straße") == normalize_preference_key("STRASSE")


@pytest.mark.parametrize(
    "source",
    [
        "Photography",
        "  Street   Photography  ",
        "Straße",
        "Ｐｈｏｔｏｇｒａｐｈｙ",
        "oﬃce",
        "Tiếng\u00a0Việt",
    ],
)
def test_normalized_key_is_idempotent(source: str) -> None:
    first = normalize_preference_key(source)

    assert normalize_preference_key(first) == first


def test_identity_value_object_is_immutable() -> None:
    identity = normalize_preference_identity("Photography")

    with pytest.raises(FrozenInstanceError):
        identity.display_label = "Changed"  # type: ignore[misc]


def test_semantically_different_labels_remain_distinct() -> None:
    assert normalize_preference_key("Football") != normalize_preference_key("Soccer")


def test_pref_001_identity_uses_profile_kind_and_normalized_key() -> None:
    profile_id = UUID(int=1)
    interest_identity = (
        profile_id,
        PreferenceKind.INTEREST,
        normalize_preference_key("  Photography "),
    )

    assert interest_identity == (
        profile_id,
        PreferenceKind.INTEREST,
        normalize_preference_key("PHOTOGRAPHY"),
    )
    assert interest_identity != (
        profile_id,
        PreferenceKind.INTEREST,
        normalize_preference_key("Football"),
    )
    assert interest_identity != (
        profile_id,
        PreferenceKind.ACTIVITY,
        normalize_preference_key("Photography"),
    )


@pytest.mark.parametrize(
    "source",
    [
        "",
        " \t \u00a0 ",
        "Photography\x00",
        "Photography\r",
        "Photography\n",
        "Photo\u200bgraphy",
        "Photo\u202egraphy",
        "Photo\ud800graphy",
    ],
)
def test_empty_and_unsafe_control_inputs_are_rejected(source: str) -> None:
    with pytest.raises(PreferenceIdentityError):
        normalize_preference_identity(source)


def test_input_is_bounded_before_normalization() -> None:
    assert MAX_CUSTOM_PREFERENCE_INPUT_LENGTH == (MAX_CUSTOM_PREFERENCE_NORMALIZED_KEY_LENGTH)

    with pytest.raises(PreferenceIdentityError, match="pre-normalization"):
        normalize_preference_identity("x" * (MAX_CUSTOM_PREFERENCE_INPUT_LENGTH + 1))


def test_display_label_is_bounded_after_whitespace_cleanup() -> None:
    assert len("x" * MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH) == (
        MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH
    )
    assert (
        normalize_preference_identity(
            "x" * MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH
        ).display_label
        == "x" * MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH
    )

    with pytest.raises(PreferenceIdentityError, match="display label"):
        normalize_preference_identity("x" * (MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH + 1))


def test_compatibility_expansion_is_bounded_after_normalization() -> None:
    source = "㍿" * 100
    assert len(source) <= MAX_CUSTOM_PREFERENCE_INPUT_LENGTH
    assert len(source) <= MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH

    with pytest.raises(PreferenceIdentityError, match="normalized key"):
        normalize_preference_identity(source)
