"""Public HTTP contract and failure sanitization tests for EVS-005."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.event_sliders as event_sliders_api
from app.api.dependencies import get_image_storage_service
from app.core.database import get_database_session
from app.main import app
from app.schemas.event import EventSliderCta, PublicEventSliderResponse
from app.services.image_storage import ImageStorageService, StorageOperationError

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
NOW = datetime(2026, 10, 10, 8, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _install() -> None:
    session = cast(AsyncSession, MagicMock(spec=AsyncSession))
    storage = cast(ImageStorageService, MagicMock(spec=ImageStorageService))

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_image_storage_service] = lambda: storage


def _slide() -> PublicEventSliderResponse:
    return PublicEventSliderResponse(
        id=EVENT_ID,
        title="Buddy Day",
        description="Meet the community.",
        image_url="https://storage.example.test/signed-cover",
        image_alt="Buddy Day poster",
        event_start_at=NOW,
        event_end_at=NOW,
        location="VGU Campus",
        cta=EventSliderCta(label="View event", href=f"/events/{EVENT_ID}"),
        sort_order=0,
    )


@pytest.mark.anyio
async def test_public_slider_returns_exact_adapter_shape_and_empty_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install()
    service = AsyncMock(side_effect=[[_slide()], []])
    monkeypatch.setattr(event_sliders_api, "list_public_event_sliders", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        populated = await client.get("/api/event-sliders?locale=en")
        empty = await client.get("/api/event-sliders?locale=de")

    assert populated.status_code == 200
    assert populated.headers["cache-control"] == "no-store"
    assert populated.json()[0] == {
        "id": str(EVENT_ID),
        "title": "Buddy Day",
        "description": "Meet the community.",
        "image_url": "https://storage.example.test/signed-cover",
        "image_alt": "Buddy Day poster",
        "event_start_at": "2026-10-10T08:00:00Z",
        "event_end_at": "2026-10-10T08:00:00Z",
        "location": "VGU Campus",
        "cta": {"label": "View event", "href": f"/events/{EVENT_ID}"},
        "sort_order": 0,
    }
    assert empty.status_code == 200
    assert empty.json() == []
    assert service.await_args_list[0].kwargs["locale"] == "en"
    assert service.await_args_list[1].kwargs["locale"] == "de"


@pytest.mark.anyio
async def test_invalid_locale_and_storage_failure_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install()
    service = AsyncMock(side_effect=StorageOperationError("provider secret"))
    monkeypatch.setattr(event_sliders_api, "list_public_event_sliders", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        invalid = await client.get("/api/event-sliders?locale=fr")
        unavailable = await client.get("/api/event-sliders?locale=en")

    assert invalid.status_code == 422
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "Event slider media is unavailable."}
    assert "provider" not in unavailable.text


def test_openapi_exposes_read_only_slider_without_storage_fields() -> None:
    document = app.openapi()

    assert set(document["paths"]["/api/event-sliders"]) == {"get"}
    properties = document["components"]["schemas"]["PublicEventSliderResponse"]["properties"]
    assert "bucket" not in properties
    assert "object_key" not in properties
    assert "created_by" not in properties
