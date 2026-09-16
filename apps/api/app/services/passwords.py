"""Password hashing primitives for application-owned authentication."""

from typing import Final

import bcrypt

BCRYPT_ROUNDS: Final = 12
BCRYPT_MAX_PASSWORD_BYTES: Final = 72


class PasswordHashingError(ValueError):
    """Raised when a password cannot be represented safely by bcrypt."""


def _encode_password(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if not encoded:
        raise PasswordHashingError("Password must not be empty.")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise PasswordHashingError(
            f"Password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} UTF-8 bytes."
        )
    return encoded


def hash_password(password: str) -> str:
    """Hash a non-empty password with a fresh bcrypt salt and cost 12."""
    encoded = _encode_password(password)
    hashed = bcrypt.hashpw(
        encoded,
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS, prefix=b"2b"),
    )
    return hashed.decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password and fail closed for invalid input or stored hashes."""
    try:
        encoded = _encode_password(password)
        encoded_hash = password_hash.encode("ascii")
        return bcrypt.checkpw(encoded, encoded_hash)
    except (PasswordHashingError, UnicodeEncodeError, ValueError):
        return False
