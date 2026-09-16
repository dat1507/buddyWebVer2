"""Authentication transport response schemas."""

from pydantic import BaseModel


class CsrfTokenResponse(BaseModel):
    """Signed CSRF value that the frontend retains only in memory."""

    csrf_token: str
