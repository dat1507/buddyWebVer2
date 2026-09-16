"""Security and behavior tests for the bcrypt password service."""

import pytest

from app.services import (
    BCRYPT_MAX_PASSWORD_BYTES,
    BCRYPT_ROUNDS,
    PasswordHashingError,
    hash_password,
    verify_password,
)


def test_hash_password_uses_bcrypt_2b_with_cost_12() -> None:
    password = "correct horse battery staple"

    password_hash = hash_password(password)

    assert password_hash.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")
    assert len(password_hash) == 60
    assert password not in password_hash
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong password", password_hash) is False


def test_hash_password_uses_a_fresh_random_salt() -> None:
    first_hash = hash_password("same password")
    second_hash = hash_password("same password")

    assert first_hash != second_hash
    assert verify_password("same password", first_hash) is True
    assert verify_password("same password", second_hash) is True


def test_passwords_are_not_trimmed_or_unicode_normalized() -> None:
    exact_password = "  Caf\u00e9 \U0001f512  "
    password_hash = hash_password(exact_password)

    assert verify_password(exact_password, password_hash) is True
    assert verify_password(exact_password.strip(), password_hash) is False
    assert verify_password("  Cafe\u0301 \U0001f512  ", password_hash) is False


def test_bcrypt_72_byte_boundary_is_enforced_without_truncation() -> None:
    maximum_ascii_password = "a" * BCRYPT_MAX_PASSWORD_BYTES
    maximum_unicode_password = "\u00e9" * (BCRYPT_MAX_PASSWORD_BYTES // 2)

    ascii_hash = hash_password(maximum_ascii_password)
    unicode_hash = hash_password(maximum_unicode_password)

    assert verify_password(maximum_ascii_password, ascii_hash) is True
    assert verify_password(maximum_unicode_password, unicode_hash) is True

    with pytest.raises(PasswordHashingError, match="72 UTF-8 bytes"):
        hash_password(f"{maximum_ascii_password}a")
    with pytest.raises(PasswordHashingError, match="72 UTF-8 bytes"):
        hash_password(f"{maximum_unicode_password}\u00e9")

    assert verify_password(f"{maximum_ascii_password}a", ascii_hash) is False


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(PasswordHashingError, match="must not be empty"):
        hash_password("")


@pytest.mark.parametrize(
    "password_hash",
    [
        "",
        "not-a-bcrypt-hash",
        "$2b$12$too-short",
        "$2z$12$......................0123456789012345678901234567890",
        "n\u00f6t-ascii",
    ],
)
def test_verify_password_fails_closed_for_malformed_hashes(password_hash: str) -> None:
    assert verify_password("candidate", password_hash) is False


def test_verify_password_fails_closed_for_invalid_candidate() -> None:
    valid_hash = hash_password("valid password")

    assert verify_password("", valid_hash) is False
    assert verify_password("a" * (BCRYPT_MAX_PASSWORD_BYTES + 1), valid_hash) is False
