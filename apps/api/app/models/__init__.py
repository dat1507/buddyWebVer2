"""Persistence model package."""

from app.models.base import Base
from app.models.user import UserRole

__all__ = ("Base", "UserRole")
