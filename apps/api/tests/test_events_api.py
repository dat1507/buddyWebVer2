"""HTTP contract, optional authentication, and leak tests for EVT-005."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.events as events_api
from app.api.dependencies import get_image_storage_service
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import EventPhase, EventStatus, EventVisibility, User, UserRole
from app.schemas.event import EventLocale, PublicEventListResponse, PublicEventResponse
from app.services.event_queries import EventQueryValidationError
from app.services.image_storage import ImageStorageService, StorageOperationError
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
USER_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _event(*, locale: str = "en") -> PublicEventResponse:
    return PublicEventResponse(
        id=EVENT_ID,
        locale=cast(EventLocale, locale),
        title="Buddy Day",
        description="Meet your Buddy community.",
        start_date=NOW + timedelta(days=1),
        end_date=NOW + timedelta(days=1, hours=2),
        timezone="Asia/Ho_Chi_Minh",
        location="VGU Campus",
        category="community",
        organizer="VGU Buddy",
        registration_url="https://example.com/register",
        registration_enabled=True,
        registration_deadline=NOW + timedelta(hours=12),
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.PUBLIC,
        phase=EventPhase.UPCOMING,
        cover=None,
    )


def _install(session: AsyncSession, storage: ImageStorageService) -> None:
    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = _settings
    app.dependency_overrides[get_image_storage_service] = lambda: storage


def _dependencies(actor: User | None = None) -> tuple[MagicMock, ImageStorageService]:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=actor)
    storage = MagicMock(spec=ImageStorageService)
    _install(cast(AsyncSession, session), cast(ImageStorageService, storage))
    return session, cast(ImageStorageService, storage)


@pytest.mark.anyio
async def test_anonymous_list_passes_filters_and_returns_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _dependencies()
    service = AsyncMock(
        return_value=PublicEventListResponse(
            items=[_event(locale="de")],
            page=2,
            page_size=5,
            total=6,
            total_pages=2,
        )
    )
    monkeypatch.setattr(events_api, "list_public_events", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/events?locale=de&category=community&phase=UPCOMING&page=2&page_size=5"
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"][0]["title"] == "Buddy Day"
    call = service.await_args
    assert call is not None
    assert call.kwargs["viewer"] is None
    assert call.kwargs["filters"].locale == "de"
    assert call.kwargs["filters"].phase is EventPhase.UPCOMING
    assert call.kwargs["filters"].page == 2


@pytest.mark.anyio
async def test_verified_user_is_resolved_from_persisted_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = User(
        id=USER_ID,
        email="member@example.com",
        password_hash="test-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
        deleted_at=None,
    )
    _, _storage = _dependencies(actor)
    service = AsyncMock(
        return_value=PublicEventListResponse(items=[], page=1, page_size=20, total=0, total_pages=0)
    )
    monkeypatch.setattr(events_api, "list_public_events", service)
    settings = _settings()
    pair = create_token_pair(USER_ID, UserRole.USER, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        response = await client.get("/api/events")

    assert response.status_code == 200
    call = service.await_args
    assert call is not None
    assert call.kwargs["viewer"] is actor


@pytest.mark.anyio
async def test_missing_hidden_and_unknown_detail_share_sanitized_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _dependencies()
    monkeypatch.setattr(events_api, "get_public_event_detail", AsyncMock(return_value=None))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/events/{EVENT_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found."}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_invalid_range_and_storage_failure_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _dependencies()
    list_service = AsyncMock(side_effect=EventQueryValidationError("raw range detail"))
    detail_service = AsyncMock(side_effect=StorageOperationError("provider secret detail"))
    monkeypatch.setattr(events_api, "list_public_events", list_service)
    monkeypatch.setattr(events_api, "get_public_event_detail", detail_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        invalid = await client.get("/api/events?from=2026-01-01T00:00:00Z&to=2026-06-01T00:00:00Z")
        unavailable = await client.get(f"/api/events/{EVENT_ID}")

    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "Event query is invalid."}
    assert "raw range" not in invalid.text
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "Event media is unavailable."}
    assert "provider" not in unavailable.text


@pytest.mark.anyio
async def test_invalid_locale_uuid_and_cookie_fail_before_event_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _dependencies()
    list_service = AsyncMock()
    detail_service = AsyncMock()
    monkeypatch.setattr(events_api, "list_public_events", list_service)
    monkeypatch.setattr(events_api, "get_public_event_detail", detail_service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        bad_locale = await client.get("/api/events?locale=fr")
        bad_uuid = await client.get("/api/events/not-a-uuid")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: "not-a-token"},
    ) as client:
        bad_cookie = await client.get("/api/events")

    assert bad_locale.status_code == 422
    assert bad_uuid.status_code == 422
    assert bad_cookie.status_code == 401
    list_service.assert_not_awaited()
    detail_service.assert_not_awaited()


@pytest.mark.anyio
async def test_openapi_exposes_read_only_allowlisted_event_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    assert set(document["paths"]["/api/events"]) == {"get"}
    assert set(document["paths"]["/api/events/{event_id}"]) == {"get"}
    forbidden = {
        "created_by",
        "updated_by",
        "cover_media_id",
        "object_key",
        "bucket",
        "max_participants",
    }
    for schema_name in (
        "PublicEventCoverResponse",
        "PublicEventResponse",
        "PublicEventListResponse",
    ):
        assert forbidden.isdisjoint(
            document["components"]["schemas"][schema_name].get("properties", {})
        )
