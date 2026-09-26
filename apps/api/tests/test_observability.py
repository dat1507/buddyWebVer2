"""OPS-003 structured, redacted API observability contract."""

import io
import json
import logging
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.observability import (
    LOGGER_NAME,
    ApiObservabilityMiddleware,
    emit_api_request_event,
    get_operations_logger,
)


@pytest.fixture
def operations_log() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    logger = get_operations_logger()
    original_handlers = list(logger.handlers)
    logger.handlers = [logging.StreamHandler(stream)]
    try:
        yield stream
    finally:
        logger.handlers = original_handlers
        logging.getLogger(LOGGER_NAME).propagate = False


def test_structured_event_has_fixed_safe_fields(operations_log: io.StringIO) -> None:
    emit_api_request_event(
        request_id="00000000-0000-4000-8000-000000000000",
        method="POST",
        route="/api/auth/verify-email",
        status_code=503,
        duration_ms=17,
        error_type="DatabaseError",
    )

    event = json.loads(operations_log.getvalue())
    assert event == {
        "timestamp": event["timestamp"],
        "service": "vgu-buddy-api",
        "event": "api_request_completed",
        "request_id": "00000000-0000-4000-8000-000000000000",
        "method": "POST",
        "route": "/api/auth/verify-email",
        "status_code": 503,
        "duration_ms": 17,
        "error_type": "DatabaseError",
    }
    assert not {
        "query",
        "body",
        "headers",
        "token",
        "authorization",
        "cookie",
        "signed_url",
        "message",
    }.intersection(event)


@pytest.mark.anyio
async def test_middleware_logs_route_template_and_never_query_or_body(
    operations_log: io.StringIO,
) -> None:
    test_app = FastAPI()
    test_app.add_middleware(ApiObservabilityMiddleware)

    @test_app.post("/items/{item_id}")
    async def item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/items/safe-id?token=verification-secret",
            json={"message": "sensitive body"},
        )

    event = json.loads(operations_log.getvalue())
    assert response.status_code == 200
    assert response.headers["x-request-id"] == event["request_id"]
    assert event["route"] == "/items/{item_id}"
    assert "verification-secret" not in operations_log.getvalue()
    assert "sensitive body" not in operations_log.getvalue()
    assert "safe-id" not in operations_log.getvalue()


@pytest.mark.anyio
async def test_middleware_sanitizes_unhandled_failure(operations_log: io.StringIO) -> None:
    test_app = FastAPI()
    test_app.add_middleware(ApiObservabilityMiddleware)

    @test_app.get("/failure")
    async def failure() -> None:
        raise RuntimeError("database-url-with-password")

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/failure")

    event = json.loads(operations_log.getvalue())
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert response.headers["x-request-id"] == event["request_id"]
    assert event["error_type"] == "RuntimeError"
    assert "database-url-with-password" not in operations_log.getvalue()
