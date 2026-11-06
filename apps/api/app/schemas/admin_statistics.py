"""Aggregate-only private Admin statistics."""

from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserStatistics(BaseModel):
    total_users: int = Field(ge=0)
    observed_at: datetime


class AdminEventStatistics(BaseModel):
    published_events: int = Field(ge=0)
    upcoming_events: int = Field(ge=0)
    observed_at: datetime
