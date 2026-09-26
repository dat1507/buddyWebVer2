"""Structured, redacted API telemetry with a deliberately small field allowlist."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from time import perf_counter
from typing import Final, Literal, cast
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOGGER_NAME: Final = "vgu_buddy.operations"
REQUEST_ID_HEADER: Final = b"x-request-id"
UNMATCHED_ROUTE: Final = "<unmatched>"

LogLevel = Literal["info", "warning", "error"]


def get_operations_logger() -> logging.Logger:
    """Return the isolated JSON logger used by API operational telemetry."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def emit_api_request_event(
    *,
    request_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: int,
    error_type: str | None = None,
) -> None:
    """Emit only the fixed request metadata contract; never accept arbitrary fields."""
    payload: dict[str, str | int] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "vgu-buddy-api",
        "event": "api_request_completed",
        "request_id": request_id,
        "method": method,
        "route": route,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if error_type is not None:
        payload["error_type"] = error_type

    level: LogLevel
    if status_code >= 500:
        level = "error"
    elif status_code >= 400:
        level = "warning"
    else:
        level = "info"
    getattr(get_operations_logger(), level)(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    )


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    if not isinstance(template, str) or not template.startswith("/"):
        return UNMATCHED_ROUTE
    return template


class ApiObservabilityMiddleware:
    """Attach a server-generated request ID and emit one redacted event per HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        method = cast(str, scope.get("method", "UNKNOWN"))
        started_at = perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = cast(int, message["status"])
                headers = list(message.get("headers", []))
                if not any(name.lower() == REQUEST_ID_HEADER for name, _value in headers):
                    headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                message = cast(Message, {**message, "headers": headers})
            await send(message)

        error_type: str | None = None
        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as error:
            error_type = type(error).__name__
            status_code = 500
            if response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
                headers={
                    "Cache-Control": "no-store",
                    "Pragma": "no-cache",
                    "X-Request-ID": request_id,
                },
            )
            await response(scope, receive, send)
            raise
        finally:
            duration_ms = max(0, round((perf_counter() - started_at) * 1000))
            emit_api_request_event(
                request_id=request_id,
                method=method,
                route=_route_template(scope),
                status_code=status_code,
                duration_ms=duration_ms,
                error_type=error_type,
            )
