"""Authentication user model primitives."""

from enum import StrEnum


class UserRole(StrEnum):
    """Application roles that may be assigned to persisted users."""

    USER = "USER"
    ADMIN = "ADMIN"
