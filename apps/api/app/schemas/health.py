"""Infrastructure health response schemas."""

from typing import Literal

from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    """Successful database probe response."""

    status: Literal["ok"] = "ok"


class LivenessResponse(BaseModel):
    """Process-only probe with no dependency I/O."""

    status: Literal["alive"] = "alive"


class ReadinessDependencies(BaseModel):
    """Sanitized states that identify the failing dependency, never its endpoint."""

    database: Literal["ok", "configured", "unconfigured", "unavailable"]
    redis: Literal["ok", "configured", "unconfigured", "unavailable"]
    email: Literal["ok", "configured", "unconfigured", "unavailable"]
    storage: Literal["ok", "configured", "unconfigured", "unavailable"]


class ReadinessResponse(BaseModel):
    """Aggregate infrastructure readiness projection."""

    status: Literal["ready", "not_ready"]
    dependencies: ReadinessDependencies
