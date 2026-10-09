"""RBAC, CSRF, transactions, audit, and DTO tests for Admin Event APIs."""

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

import app.api.admin_events as admin_events_api
from app.api.dependencies import get_image_storage_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import Event, EventStatus, EventVisibility, User, UserRole
from app.schemas.event import AdminEventListResponse
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.events import EventDeletionPlan, EventVersionConflictError, project_admin_event
from app.services.image_storage import ImageBucket, ImageStorageService, StorageObjectRef
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
ADMIN_ID = UUID("22222222-2222-4222-8222-222222222222")
MEDIA_KEY = "33333333-3333-4333-8333-333333333333.webp"
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


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
        trusted_origins=("http://testserver",),
    )


def _actor(*, role: UserRole = UserRole.ADMIN) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
        deleted_at=None,
    )


def _event(*, status: EventStatus = EventStatus.DRAFT, version: int = 1) -> Event:
    return Event(
        id=EVENT_ID,
        title_en="Buddy Day",
        title_de="Buddy-Tag",
        description_en="Community event",
        description_de="Community-Veranstaltung",
        start_date=NOW + timedelta(days=1),
        end_date=NOW + timedelta(days=1, hours=2),
        timezone="Asia/Ho_Chi_Minh",
        location_en="VGU Campus",
        location_de="VGU-Campus",
        category="community",
        organizer="VGU Buddy",
        registration_url=None,
        cover_media_id=None,
        status=status,
        visibility=EventVisibility.MEMBERS,
        registration_enabled=False,
        max_participants=None,
        registration_deadline=None,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=None,
        version=version,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _session(actor: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=actor)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(
    session: AsyncSession,
    *,
    role: UserRole = UserRole.ADMIN,
) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()
    storage = MagicMock(spec=ImageStorageService)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_image_storage_service] = lambda: storage
    pair = create_token_pair(ADMIN_ID, role, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    return (
        {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(csrf_settings): csrf.value,
        },
        {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value},
    )


def _draft_payload() -> dict[str, object]:
    return {
        "title_en": "Buddy Day",
        "title_de": "Buddy-Tag",
        "timezone": "Asia/Ho_Chi_Minh",
        "visibility": "MEMBERS",
        "registration_enabled": False,
    }


@pytest.mark.anyio
async def test_admin_list_and_detail_are_private_and_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor())
    cookies, _headers = _install(session)
    event = project_admin_event(_event())
    list_service = AsyncMock(
        return_value=AdminEventListResponse(
            items=[event], page=2, page_size=5, total=6, total_pages=2
        )
    )
    detail_service = AsyncMock(return_value=event)
    monkeypatch.setattr(admin_events_api, "list_admin_events", list_service)
    monkeypatch.setattr(admin_events_api, "get_admin_event_detail", detail_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        listing = await client.get(
            "/api/admin/events",
            params={
                "page": 2,
                "page_size": 5,
                "search": "Buddy",
                "status": "DRAFT",
                "visibility": "MEMBERS",
                "phase": "UPCOMING",
            },
        )
        detail = await client.get(f"/api/admin/events/{EVENT_ID}")

    assert listing.status_code == detail.status_code == 200
    assert listing.headers["cache-control"] == "private, no-store"
    assert listing.headers["vary"] == "Cookie"
    assert "created_by" not in listing.text
    assert "object_key" not in listing.text
    call = list_service.await_args
    assert call is not None
    assert call.kwargs["filters"].status is EventStatus.DRAFT
    assert call.kwargs["filters"].page == 2
    detail_service.assert_awaited_once_with(session, EVENT_ID)


@pytest.mark.anyio
async def test_create_is_csrf_protected_audited_and_committed_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    mock, session = _session(actor)
    cookies, headers = _install(session)
    event = _event()
    create_service = AsyncMock(return_value=event)
    audit_service = AsyncMock()
    monkeypatch.setattr(admin_events_api, "create_event_draft", create_service)
    monkeypatch.setattr(admin_events_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/admin/events", headers=headers, json=_draft_payload())

    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["id"] == str(EVENT_ID)
    create_service.assert_awaited_once()
    create_call = create_service.await_args
    assert create_call is not None
    assert create_call.args[0:2] == (session, actor)
    audit_service.assert_awaited_once()
    audit_call = audit_service.await_args
    assert audit_call is not None
    assert audit_call.kwargs["action"] == "event.create"
    assert set(audit_call.kwargs["new_value"]) == {"status", "visibility", "version"}
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/api/admin/events", _draft_payload()),
        ("put", f"/api/admin/events/{EVENT_ID}", {"version": 1, "title_en": "Changed"}),
        (
            "patch",
            f"/api/admin/events/{EVENT_ID}/status",
            {"version": 1, "status": "DRAFT"},
        ),
        ("delete", f"/api/admin/events/{EVENT_ID}?version=1", None),
    ],
)
async def test_mutations_reject_missing_csrf_before_domain_service(
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor())
    cookies, _headers = _install(session)
    services = {
        "create_event_draft": AsyncMock(),
        "update_event_draft": AsyncMock(),
        "set_event_status": AsyncMock(),
        "delete_event": AsyncMock(),
    }
    for name, service in services.items():
        monkeypatch.setattr(admin_events_api, name, service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.request(method, path, json=json_body)

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    for service in services.values():
        service.assert_not_awaited()


@pytest.mark.anyio
async def test_update_conflict_rolls_back_without_false_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    cookies, headers = _install(session)
    update_service = AsyncMock(side_effect=EventVersionConflictError("raw version detail"))
    audit_service = AsyncMock()
    monkeypatch.setattr(admin_events_api, "update_event_draft", update_service)
    monkeypatch.setattr(admin_events_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.put(
            f"/api/admin/events/{EVENT_ID}",
            headers=headers,
            json={"version": 1, "title_en": "Changed"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Event version is stale."}
    assert "raw version" not in response.text
    audit_service.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_audit_failure_rolls_back_staged_event_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    cookies, headers = _install(session)
    monkeypatch.setattr(admin_events_api, "update_event_draft", AsyncMock(return_value=_event()))
    monkeypatch.setattr(
        admin_events_api,
        "record_audit_log",
        AsyncMock(side_effect=RuntimeError("audit unavailable")),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await client.put(
                f"/api/admin/events/{EVENT_ID}",
                headers=headers,
                json={"version": 1, "title_en": "Changed"},
            )

    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_commits_before_cleanup_and_reports_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    cookies, headers = _install(session)
    reference = StorageObjectRef(bucket=ImageBucket.EVENT_MEDIA, object_key=MEDIA_KEY)
    plan = EventDeletionPlan(event_id=EVENT_ID, media=(reference,))
    order: list[str] = []

    async def commit() -> None:
        order.append("commit")

    async def cleanup(
        _storage: ImageStorageService,
        received: EventDeletionPlan,
    ) -> tuple[StorageObjectRef, ...]:
        assert received is plan
        order.append("cleanup")
        return (reference,)

    mock.commit.side_effect = commit
    monkeypatch.setattr(admin_events_api, "delete_event", AsyncMock(return_value=plan))
    monkeypatch.setattr(admin_events_api, "record_audit_log", AsyncMock())
    monkeypatch.setattr(admin_events_api, "cleanup_deleted_event_media", cleanup)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.delete(f"/api/admin/events/{EVENT_ID}?version=1", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "event_id": str(EVENT_ID),
        "cleanup_pending": True,
        "failed_object_count": 1,
    }
    assert order == ["commit", "cleanup"]
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", "/api/admin/events", None),
        ("get", f"/api/admin/events/{EVENT_ID}", None),
        ("post", "/api/admin/events", _draft_payload()),
        ("put", f"/api/admin/events/{EVENT_ID}", {"version": 1, "title_en": "Changed"}),
        (
            "patch",
            f"/api/admin/events/{EVENT_ID}/status",
            {"version": 1, "status": "DRAFT"},
        ),
        ("delete", f"/api/admin/events/{EVENT_ID}?version=1", None),
    ],
)
async def test_user_is_403_and_anonymous_is_401_for_every_admin_route(
    method: str,
    path: str,
    json_body: dict[str, object] | None,
) -> None:
    _, session = _session(_actor(role=UserRole.USER))
    user_cookies, user_headers = _install(session, role=UserRole.USER)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=user_cookies
    ) as client:
        user_response = await client.request(method, path, headers=user_headers, json=json_body)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        anonymous_response = await client.request(method, path, json=json_body)

    assert user_response.status_code == 403
    assert anonymous_response.status_code == 401


@pytest.mark.anyio
async def test_openapi_exposes_only_canonical_admin_event_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    assert set(document["paths"]["/api/admin/events"]) == {"get", "post"}
    assert set(document["paths"]["/api/admin/events/{event_id}"]) == {
        "get",
        "put",
        "delete",
    }
    assert set(document["paths"]["/api/admin/events/{event_id}/status"]) == {"patch"}
    assert "/api/admin/event-sliders" not in document["paths"]
    forbidden = {"created_by", "updated_by", "object_key", "bucket", "password_hash"}
    for schema_name in ("AdminEventResponse", "AdminEventListResponse", "EventDeleteResponse"):
        assert forbidden.isdisjoint(
            document["components"]["schemas"][schema_name].get("properties", {})
        )
