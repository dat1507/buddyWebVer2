"""Transport, RBAC, audit, rollback, and disclosure tests for Event media APIs."""

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

import app.api.event_media as event_media_api
from app.api.dependencies import get_image_storage_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import (
    Event,
    EventMedia,
    EventMediaProcessingStatus,
    EventMediaUsage,
    EventStatus,
    EventVisibility,
    User,
    UserRole,
)
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.event_media import (
    AuthorizedEventMedia,
    EventCoverReplacement,
    EventMediaDeletion,
    EventMediaNotFoundError,
)
from app.services.image_storage import ImageBucket, ImageStorageService, StorageObjectRef
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

EVENT_ID = UUID("11111111-1111-4111-8111-111111111111")
MEDIA_ID = UUID("22222222-2222-4222-8222-222222222222")
ADMIN_ID = UUID("33333333-3333-4333-8333-333333333333")
OBJECT_KEY = "44444444-4444-4444-8444-444444444444.webp"
OLD_KEY = "55555555-5555-4555-8555-555555555555.webp"
NOW = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)
SIGNING_KEY = bytes(range(32))
SIGNED_URL = "https://storage.example.test/signed?token=redacted"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> tuple[AuthTokenSettings, CsrfSettings]:
    auth = AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)
    csrf = CsrfSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
        trusted_origins=("http://testserver",),
    )
    return auth, csrf


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


def _event(*, version: int = 4) -> Event:
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
        cover_media_id=MEDIA_ID,
        status=EventStatus.DRAFT,
        visibility=EventVisibility.MEMBERS,
        registration_enabled=False,
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
        published_at=None,
        version=version,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _media() -> EventMedia:
    return EventMedia(
        id=MEDIA_ID,
        event_id=EVENT_ID,
        bucket=ImageBucket.EVENT_MEDIA.value,
        object_key=OBJECT_KEY,
        usage=EventMediaUsage.EVENT_COVER,
        alt_en="Event poster",
        alt_de="Veranstaltungsplakat",
        mime_type="image/webp",
        byte_size=2048,
        width=1200,
        height=800,
        sort_order=0,
        processing_status=EventMediaProcessingStatus.READY,
        created_by=ADMIN_ID,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def _replacement() -> EventCoverReplacement:
    return EventCoverReplacement(
        event=_event(),
        media=_media(),
        new_reference=StorageObjectRef(ImageBucket.EVENT_MEDIA, OBJECT_KEY),
        previous_reference=StorageObjectRef(ImageBucket.EVENT_MEDIA, OLD_KEY),
    )


def _session(actor: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=actor)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _storage() -> tuple[MagicMock, ImageStorageService]:
    mock = MagicMock(spec=ImageStorageService)
    mock.create_signed_url = AsyncMock(return_value=SIGNED_URL)
    mock.delete_image = AsyncMock()
    return mock, cast(ImageStorageService, mock)


def _install(
    session: AsyncSession,
    storage: ImageStorageService,
    *,
    token_role: UserRole = UserRole.ADMIN,
) -> tuple[dict[str, str], dict[str, str]]:
    auth, csrf_settings = _settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_image_storage_service] = lambda: storage
    pair = create_token_pair(ADMIN_ID, token_role, auth)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    return (
        {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(csrf_settings): csrf.value,
        },
        {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value},
    )


@pytest.mark.anyio
async def test_cover_upload_is_private_audited_committed_and_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    mock, session = _session(actor)
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    stage = AsyncMock(return_value=_replacement())
    audit = AsyncMock()
    cleanup = AsyncMock(return_value=False)
    monkeypatch.setattr(event_media_api, "stage_event_cover_replacement", stage)
    monkeypatch.setattr(event_media_api, "record_audit_log", audit)
    monkeypatch.setattr(event_media_api, "cleanup_replaced_cover", cleanup)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/events/{EVENT_ID}/media",
            headers=headers,
            data={"version": "3", "alt_en": "Event poster", "alt_de": "Poster"},
            files={"file": ("cover.png", b"png-bytes", "image/png")},
        )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["cleanup_pending"] is True
    assert response.json()["event"]["version"] == 4
    assert response.json()["media"]["id"] == str(MEDIA_ID)
    assert OBJECT_KEY not in response.text
    assert "bucket" not in response.text
    stage.assert_awaited_once()
    audit.assert_awaited_once()
    mock.commit.assert_awaited_once_with()
    cleanup.assert_awaited_once()


@pytest.mark.anyio
async def test_invalid_multipart_is_rejected_before_storage_or_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    stage = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(event_media_api, "stage_event_cover_replacement", stage)
    monkeypatch.setattr(event_media_api, "record_audit_log", audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/events/{EVENT_ID}/media",
            headers={**headers, "Content-Type": "application/json"},
            content=b"{}",
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Event media is invalid."}
    stage.assert_not_awaited()
    audit.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_audit_failure_rolls_back_and_compensates_new_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    replacement = _replacement()
    compensate = AsyncMock(return_value=True)
    monkeypatch.setattr(
        event_media_api, "stage_event_cover_replacement", AsyncMock(return_value=replacement)
    )
    monkeypatch.setattr(
        event_media_api, "record_audit_log", AsyncMock(side_effect=RuntimeError("audit down"))
    )
    monkeypatch.setattr(event_media_api, "compensate_cover_replacement", compensate)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            f"/api/admin/events/{EVENT_ID}/media",
            headers=headers,
            data={"version": "3", "alt_en": "Event poster", "alt_de": "Poster"},
            files={"file": ("cover.png", b"png-bytes", "image/png")},
        )

    assert response.status_code == 500
    mock.commit.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()
    compensate.assert_awaited_once_with(storage, replacement)


@pytest.mark.anyio
async def test_cross_event_media_id_is_generic_404_and_never_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    update = AsyncMock(side_effect=EventMediaNotFoundError)
    audit = AsyncMock()
    monkeypatch.setattr(event_media_api, "update_event_media_metadata", update)
    monkeypatch.setattr(event_media_api, "record_audit_log", audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.patch(
            f"/api/admin/events/{EVENT_ID}/media/{MEDIA_ID}",
            headers=headers,
            json={"version": 4, "alt_en": "Changed"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Event media not found."}
    audit.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_delete_commits_before_best_effort_storage_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    deletion = EventMediaDeletion(
        event_id=EVENT_ID,
        media_id=MEDIA_ID,
        event_version=5,
        reference=StorageObjectRef(ImageBucket.EVENT_MEDIA, OBJECT_KEY),
    )
    delete = AsyncMock(return_value=deletion)
    audit = AsyncMock()
    cleanup = AsyncMock(return_value=False)
    monkeypatch.setattr(event_media_api, "delete_event_media", delete)
    monkeypatch.setattr(event_media_api, "record_audit_log", audit)
    monkeypatch.setattr(event_media_api, "cleanup_deleted_media", cleanup)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.delete(
            f"/api/admin/events/{EVENT_ID}/media/{MEDIA_ID}",
            params={"version": 4},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["cleanup_pending"] is True
    mock.commit.assert_awaited_once_with()
    cleanup.assert_awaited_once_with(storage, deletion)


@pytest.mark.anyio
async def test_admin_mutation_uses_persisted_role_and_requires_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor(role=UserRole.USER))
    _, storage = _storage()
    cookies, headers = _install(session, storage, token_role=UserRole.ADMIN)
    stage = AsyncMock()
    monkeypatch.setattr(event_media_api, "stage_event_cover_replacement", stage)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        forbidden = await client.post(
            f"/api/admin/events/{EVENT_ID}/media",
            headers=headers,
            data={"version": "3", "alt_en": "Poster", "alt_de": "Plakat"},
            files={"file": ("cover.png", b"image", "image/png")},
        )

    assert forbidden.status_code == 403
    stage.assert_not_awaited()

    _, admin_session = _session(_actor())
    admin_cookies, _admin_headers = _install(admin_session, storage)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=admin_cookies
    ) as client:
        no_csrf = await client.post(
            f"/api/admin/events/{EVENT_ID}/media",
            data={"version": "3", "alt_en": "Poster", "alt_de": "Plakat"},
            files={"file": ("cover.png", b"image", "image/png")},
        )

    assert no_csrf.status_code == 403
    stage.assert_not_awaited()


@pytest.mark.anyio
async def test_authorized_media_url_is_short_lived_no_store_and_least_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor())
    storage_mock, storage = _storage()
    _cookies, _headers = _install(session, storage)
    media = _media()
    authorized = AuthorizedEventMedia(
        media=media,
        reference=StorageObjectRef(ImageBucket.EVENT_MEDIA, OBJECT_KEY),
    )
    authorize = AsyncMock(return_value=authorized)
    monkeypatch.setattr(event_media_api, "get_authorized_event_media", authorize)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/events/{EVENT_ID}/media/{MEDIA_ID}/url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "id": str(MEDIA_ID),
        "event_id": str(EVENT_ID),
        "url": SIGNED_URL,
        "expires_in": 300,
    }
    assert OBJECT_KEY not in response.text
    assert "bucket" not in response.text
    storage_mock.create_signed_url.assert_awaited_once_with(authorized.reference, expires_in=300)


@pytest.mark.anyio
async def test_unauthorized_media_is_indistinguishable_from_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor())
    storage_mock, storage = _storage()
    _cookies, _headers = _install(session, storage)
    monkeypatch.setattr(event_media_api, "get_authorized_event_media", AsyncMock(return_value=None))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/events/{EVENT_ID}/media/{MEDIA_ID}/url")

    assert response.status_code == 404
    assert response.json() == {"detail": "Event media not found."}
    storage_mock.create_signed_url.assert_not_awaited()


def test_openapi_declares_event_media_routes_without_storage_identity() -> None:
    document = app.openapi()
    paths = document["paths"]

    assert "post" in paths["/api/admin/events/{event_id}/media"]
    assert "patch" in paths["/api/admin/events/{event_id}/media/{media_id}"]
    assert "delete" in paths["/api/admin/events/{event_id}/media/{media_id}"]
    assert "get" in paths["/api/events/{event_id}/media/{media_id}/url"]
    response_schema = document["components"]["schemas"]["AdminEventMediaResponse"]
    assert "bucket" not in response_schema["properties"]
    assert "object_key" not in response_schema["properties"]
