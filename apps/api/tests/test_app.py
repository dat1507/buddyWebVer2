"""Smoke tests for the FastAPI application foundation."""

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_openapi_schema_exposes_project_metadata() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"] == {
        "title": "VGU Buddy API",
        "description": "Backend API for the VGU Student Companion Platform.",
        "version": "0.1.0",
    }


@pytest.mark.anyio
async def test_unknown_route_returns_not_found() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/not-implemented")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
