"""Transport, CSRF, RBAC, and signed-delivery tests for private profile photos."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.profile_photos as photo_api
from app.api.dependencies import get_image_storage_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    StorageConfigurationError,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import ProfilePhoto, ProfilePhotoProcessingStatus, User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ImageValidationError,
    StorageObjectRef,
    StorageOperationError,
)
from app.services.profile_photos import ProfilePhotoMutation, ProfilePhotoNotFoundError
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PHOTO_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
OBJECT_KEY = "dddddddd-dddd-4ddd-8ddd-dddddddddddd.png"
SIGNING_KEY = bytes(range(32))
CREATED_AT = datetime(2026, 9, 20, 10, 30, tzinfo=UTC)
SIGNED_URL = "https://project.supabase.co/storage/v1/object/sign/profile-images/object?token=value"


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


def _user(*, role: UserRole = UserRole.USER) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _photo() -> ProfilePhoto:
    return ProfilePhoto(
        id=PHOTO_ID,
        profile_id=PROFILE_ID,
        bucket=ImageBucket.PROFILE_IMAGES.value,
        object_key=OBJECT_KEY,
        mime_type="image/png",
        byte_size=120,
        width=12,
        height=10,
        is_avatar=True,
        processing_status=ProfilePhotoProcessingStatus.READY,
        created_at=CREATED_AT,
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
    token_role: UserRole = UserRole.USER,
) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_image_storage_service] = lambda: storage
    pair = create_token_pair(USER_ID, token_role, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    return (
        {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(csrf_settings): csrf.value,
        },
        {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value},
    )


@pytest.mark.anyio
async def test_upload_accepts_raw_image_after_csrf_and_returns_safe_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock(return_value=ProfilePhotoMutation(_photo(), cleanup_pending=False))
    monkeypatch.setattr(photo_api, "replace_own_avatar", service)
    headers["Content-Type"] = "image/png"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/profile/photos", headers=headers, content=b"png-bytes")

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "id": str(PHOTO_ID),
        "mime_type": "image/png",
        "byte_size": 120,
        "width": 12,
        "height": 10,
        "processing_status": "READY",
        "created_at": "2026-09-20T10:30:00Z",
    }
    assert OBJECT_KEY not in response.text
    service.assert_awaited_once_with(
        session,
        storage,
        actor,
        original_name="avatar.png",
        declared_content_type="image/png",
        content=b"png-bytes",
    )


@pytest.mark.anyio
@pytest.mark.parametrize("content_type", ["application/octet-stream", "image/svg+xml"])
async def test_upload_rejects_unsupported_content_type_before_storage(
    content_type: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock()
    monkeypatch.setattr(photo_api, "replace_own_avatar", service)
    headers["Content-Type"] = content_type

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/profile/photos", headers=headers, content=b"payload")

    assert response.status_code == 422
    assert response.json() == {"detail": "Profile photo is invalid."}
    service.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_upload_maps_validation_failure_without_reflecting_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    monkeypatch.setattr(
        photo_api,
        "replace_own_avatar",
        AsyncMock(side_effect=ImageValidationError("decoder included private filename")),
    )
    headers["Content-Type"] = "image/png"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/profile/photos", headers=headers, content=b"bad-image")

    assert response.status_code == 422
    assert "private filename" not in response.text
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_upload_stops_reading_after_raw_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    mock, session = _session(_user())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock()
    monkeypatch.setattr(photo_api, "replace_own_avatar", service)
    headers["Content-Type"] = "image/png"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post(
            "/api/profile/photos",
            headers=headers,
            content=b"x" * (5 * 1024 * 1024 + 1),
        )

    assert response.status_code == 422
    service.assert_not_awaited()
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_mutations_require_session_csrf_before_photo_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    _, storage = _storage()
    cookies, _headers = _install(session, storage)
    upload = AsyncMock()
    remove = AsyncMock()
    monkeypatch.setattr(photo_api, "replace_own_avatar", upload)
    monkeypatch.setattr(photo_api, "remove_own_avatar", remove)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        uploaded = await client.post(
            "/api/profile/photos",
            headers={"Content-Type": "image/png"},
            content=b"image",
        )
        deleted = await client.delete(f"/api/profile/photos/{PHOTO_ID}")

    assert uploaded.status_code == 403
    assert deleted.status_code == 403
    upload.assert_not_awaited()
    remove.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_cannot_mutate_student_avatar(monkeypatch: pytest.MonkeyPatch) -> None:
    mock, session = _session(_user(role=UserRole.ADMIN))
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock()
    monkeypatch.setattr(photo_api, "replace_own_avatar", service)
    headers["Content-Type"] = "image/png"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.post("/api/profile/photos", headers=headers, content=b"image")

    assert response.status_code == 403
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_delete_is_owner_bound_and_returns_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    mock, session = _session(_user())
    _, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock(return_value=False)
    monkeypatch.setattr(photo_api, "remove_own_avatar", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.delete(f"/api/profile/photos/{PHOTO_ID}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    service.assert_awaited_once_with(session, storage, mock.scalar.return_value, PHOTO_ID)


@pytest.mark.anyio
async def test_other_user_photo_id_returns_generic_404_without_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    storage_mock, storage = _storage()
    cookies, headers = _install(session, storage)
    service = AsyncMock(side_effect=ProfilePhotoNotFoundError)
    monkeypatch.setattr(photo_api, "remove_own_avatar", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.delete(f"/api/profile/photos/{PHOTO_ID}", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile photo not found."}
    storage_mock.delete_image.assert_not_awaited()


@pytest.mark.anyio
async def test_owner_receives_five_minute_signed_url_without_database_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    storage_mock, storage = _storage()
    cookies, _headers = _install(session, storage)
    authorization = AsyncMock(return_value=_photo())
    audit = AsyncMock()
    monkeypatch.setattr(photo_api, "get_authorized_profile_photo", authorization)
    monkeypatch.setattr(photo_api, "record_audit_log", audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 200
    assert response.json() == {"id": str(PHOTO_ID), "url": SIGNED_URL, "expires_in": 300}
    storage_mock.create_signed_url.assert_awaited_once_with(
        StorageObjectRef(ImageBucket.PROFILE_IMAGES, OBJECT_KEY),
        expires_in=300,
    )
    audit.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_signed_url_access_is_audited_without_url_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user(role=UserRole.ADMIN)
    mock, session = _session(actor)
    _, storage = _storage()
    cookies, _headers = _install(session, storage)
    audit = AsyncMock()
    monkeypatch.setattr(photo_api, "get_authorized_profile_photo", AsyncMock(return_value=_photo()))
    monkeypatch.setattr(photo_api, "record_audit_log", audit)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 200
    audit.assert_awaited_once_with(
        session,
        actor,
        action="profile_photo.admin_read",
        resource_type="profile_photo",
        resource_id=PHOTO_ID,
    )
    assert SIGNED_URL not in repr(audit.await_args)
    mock.commit.assert_awaited_once_with()


@pytest.mark.anyio
async def test_unauthorized_photo_delivery_never_creates_signed_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    storage_mock, storage = _storage()
    cookies, _headers = _install(session, storage)
    monkeypatch.setattr(
        photo_api,
        "get_authorized_profile_photo",
        AsyncMock(side_effect=ProfilePhotoNotFoundError),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 404
    storage_mock.create_signed_url.assert_not_awaited()


@pytest.mark.anyio
async def test_storage_failure_returns_sanitized_503(monkeypatch: pytest.MonkeyPatch) -> None:
    mock, session = _session(_user())
    storage_mock, storage = _storage()
    storage_mock.create_signed_url.side_effect = StorageOperationError("provider leaked secret")
    cookies, _headers = _install(session, storage)
    monkeypatch.setattr(photo_api, "get_authorized_profile_photo", AsyncMock(return_value=_photo()))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 503
    assert response.json() == {"detail": "Image storage is unavailable."}
    assert "provider leaked secret" not in response.text
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_missing_storage_configuration_is_sanitized() -> None:
    mock, session = _session(_user())
    storage_mock, storage = _storage()
    cookies, _headers = _install(session, storage)

    def unavailable_storage() -> ImageStorageService:
        raise StorageConfigurationError("SUPABASE_SECRET_KEY leaked")

    app.dependency_overrides[get_image_storage_service] = unavailable_storage
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 503
    assert response.json() == {"detail": "Image storage is unavailable."}
    assert "SUPABASE_SECRET_KEY" not in response.text


@pytest.mark.anyio
async def test_anonymous_delivery_stops_before_storage_dependency() -> None:
    storage_dependency_called = False

    def forbidden_storage() -> ImageStorageService:
        nonlocal storage_dependency_called
        storage_dependency_called = True
        raise AssertionError("storage dependency must not run")

    app.dependency_overrides[get_auth_token_settings] = _auth_settings
    app.dependency_overrides[get_image_storage_service] = forbidden_storage
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/profile/photos/{PHOTO_ID}/url")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert storage_dependency_called is False


@pytest.mark.anyio
async def test_openapi_exposes_only_photo_lifecycle_operations_and_safe_metadata() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    assert set(document["paths"]["/api/profile/photos"]) == {"post"}
    assert set(document["paths"]["/api/profile/photos/{photo_id}"]) == {"delete"}
    assert set(document["paths"]["/api/profile/photos/{photo_id}/url"]) == {"get"}
    metadata = document["components"]["schemas"]["ProfilePhotoResponse"]["properties"]
    assert {"bucket", "object_key", "url", "owner_id", "profile_id"}.isdisjoint(metadata)
    assert "avatar" in document["components"]["schemas"]["OwnProfileResponse"]["properties"]
