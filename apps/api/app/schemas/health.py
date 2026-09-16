"""Infrastructure health response schemas."""

from typing import Literal

from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    """Successful database probe response."""

    status: Literal["ok"] = "ok"
