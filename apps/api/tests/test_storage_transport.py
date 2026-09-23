"""Configuration and HTTP-boundary tests for server-only Supabase Storage access."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, cast
from unittest.mock import AsyncMock
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

import app.services.image_storage as image_storage
from app.core.config import (
    SUPABASE_SECRET_KEY_VARIABLE,
    SUPABASE_URL_VARIABLE,
    StorageConfigurationError,
    StorageSettings,
    get_storage_settings,
)
from app.services.image_storage import (
    ImageBucket,
    StorageObjectRef,
    StorageOperationError,
    SupabaseStorageTransport,
)

TEST_SECRET = "sb_secret_test-only-value"


@pytest.fixture(autouse=True)
def clear_storage_settings_cache() -> Iterator[None]:
    get_storage_settings.cache_clear()
    yield
    get_storage_settings.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> StorageSettings:
    return StorageSettings(
        url="https://project.supabase.co",
        secret_key=SecretStr(TEST_SECRET),
    )


def test_storage_settings_require_safe_server_only_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SUPABASE_URL_VARIABLE, "https://Project.Supabase.co/")
    monkeypatch.setenv(SUPABASE_SECRET_KEY_VARIABLE, TEST_SECRET)

    settings = get_storage_settings()

    assert settings.url == "https://project.supabase.co"
    assert settings.secret_key.get_secret_value() == TEST_SECRET
    assert TEST_SECRET not in repr(settings)


@pytest.mark.parametrize(
    "url",
    (
        "http://project.supabase.co",
        "https://user:password@project.supabase.co",
        "https://project.supabase.co/storage/v1",
        "https://project.supabase.co?key=value",
    ),
)
def test_storage_settings_reject_unsafe_project_urls(
    url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SUPABASE_URL_VARIABLE, url)
    monkeypatch.setenv(SUPABASE_SECRET_KEY_VARIABLE, TEST_SECRET)

    with pytest.raises(StorageConfigurationError):
        get_storage_settings()


def test_storage_settings_allow_local_http_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SUPABASE_URL_VARIABLE, "http://127.0.0.1:54321")
    monkeypatch.setenv(SUPABASE_SECRET_KEY_VARIABLE, TEST_SECRET)

    assert get_storage_settings().url == "http://127.0.0.1:54321"


def test_transport_uses_current_and_legacy_key_headers_correctly() -> None:
    current = SupabaseStorageTransport(_settings())._authentication_headers()
    legacy_key = "eyJheader.payload.signature"
    legacy = SupabaseStorageTransport(
        StorageSettings(
            url="https://project.supabase.co",
            secret_key=SecretStr(legacy_key),
        )
    )._authentication_headers()

    assert current["apikey"] == TEST_SECRET
    assert "Authorization" not in current
    assert legacy["apikey"] == legacy_key
    assert legacy["Authorization"] == f"Bearer {legacy_key}"


@pytest.mark.anyio
async def test_transport_upload_is_non_upsert_and_never_places_key_in_url() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(return_value=b"{}")
    transport._request = request  # type: ignore[method-assign]
    reference = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        "00000000-0000-4000-8000-000000000011.png",
    )

    await transport.upload(reference, b"processed image", "image/png")

    request.assert_awaited_once_with(
        "POST",
        "https://project.supabase.co/storage/v1/object/profile-images/"
        "00000000-0000-4000-8000-000000000011.png",
        body=b"processed image",
        content_type="image/png",
        extra_headers={"x-upsert": "false", "cache-control": "3600"},
    )
    assert request.await_args is not None
    assert TEST_SECRET not in request.await_args.args[1]


@pytest.mark.anyio
async def test_transport_updates_existing_bucket_configuration() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(return_value=b"{}")
    transport._request = request  # type: ignore[method-assign]

    await transport.configure_bucket(ImageBucket.EVENT_SLIDER_IMAGES)

    assert request.await_count == 2
    assert request.await_args_list[0].args == (
        "GET",
        "https://project.supabase.co/storage/v1/bucket/event-slider-images",
    )
    update = request.await_args_list[1]
    assert update.args == (
        "PUT",
        "https://project.supabase.co/storage/v1/bucket/event-slider-images",
    )
    assert update.kwargs["content_type"] == "application/json"
    assert json.loads(update.kwargs["body"]) == {
        "public": True,
        "file_size_limit": 5 * 1024 * 1024,
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
    }
    assert "id" not in json.loads(update.kwargs["body"])
    assert "name" not in json.loads(update.kwargs["body"])


@pytest.mark.anyio
async def test_transport_repeatedly_converges_existing_bucket_configuration() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(return_value=b"{}")
    transport._request = request  # type: ignore[method-assign]

    await transport.configure_bucket(ImageBucket.PROFILE_IMAGES)
    await transport.configure_bucket(ImageBucket.PROFILE_IMAGES)

    assert [call.args[0] for call in request.await_args_list] == ["GET", "PUT", "GET", "PUT"]
    for update in (request.await_args_list[1], request.await_args_list[3]):
        assert json.loads(update.kwargs["body"]) == {
            "public": False,
            "file_size_limit": 5 * 1024 * 1024,
            "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
        }


@pytest.mark.anyio
async def test_transport_creates_missing_bucket_configuration() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(
        side_effect=(
            StorageOperationError("missing", status_code=404),
            b"{}",
        )
    )
    transport._request = request  # type: ignore[method-assign]

    await transport.configure_bucket(ImageBucket.PROFILE_IMAGES)

    assert [call.args[:2] for call in request.await_args_list] == [
        ("GET", "https://project.supabase.co/storage/v1/bucket/profile-images"),
        ("POST", "https://project.supabase.co/storage/v1/bucket"),
    ]
    create = request.await_args_list[1]
    assert create.kwargs["content_type"] == "application/json"
    assert json.loads(create.kwargs["body"]) == {
        "id": "profile-images",
        "name": "profile-images",
        "public": False,
        "file_size_limit": 5 * 1024 * 1024,
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
    }


@pytest.mark.anyio
async def test_transport_converges_bucket_after_concurrent_create() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(
        side_effect=(
            StorageOperationError("missing", status_code=404),
            StorageOperationError("conflict", status_code=409),
            b"{}",
        )
    )
    transport._request = request  # type: ignore[method-assign]

    await transport.configure_bucket(ImageBucket.EVENT_MEDIA)

    assert [call.args[0] for call in request.await_args_list] == ["GET", "POST", "PUT"]
    create_body = json.loads(request.await_args_list[1].kwargs["body"])
    update_body = json.loads(request.await_args_list[2].kwargs["body"])
    assert create_body["id"] == "event-media"
    assert create_body["name"] == "event-media"
    assert update_body == {
        "public": False,
        "file_size_limit": 5 * 1024 * 1024,
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
    }


@pytest.mark.anyio
async def test_transport_lists_objects_with_aware_creation_time() -> None:
    transport = SupabaseStorageTransport(_settings())
    request = AsyncMock(
        return_value=(
            b'[{"name":"00000000-0000-4000-8000-000000000014.png",'
            b'"created_at":"2026-09-19T10:20:30Z"}]'
        )
    )
    transport._request = request  # type: ignore[method-assign]

    objects = await transport.list_objects(
        ImageBucket.PROFILE_IMAGES,
        limit=100,
        offset=200,
    )

    assert objects[0].object_key.endswith("000000000014.png")
    assert objects[0].created_at == datetime(2026, 9, 19, 10, 20, 30, tzinfo=UTC)
    assert request.await_args is not None
    request_body = json.loads(request.await_args.kwargs["body"])
    assert request_body == {
        "prefix": "",
        "limit": 100,
        "offset": 200,
        "sortBy": {"column": "name", "order": "asc"},
    }


@pytest.mark.anyio
async def test_transport_rejects_cross_origin_signed_url() -> None:
    transport = SupabaseStorageTransport(_settings())
    transport._request = AsyncMock(  # type: ignore[method-assign]
        return_value=b'{"signedURL":"https://attacker.example/object?token=stolen"}'
    )
    reference = StorageObjectRef(
        ImageBucket.EVENT_MEDIA,
        "00000000-0000-4000-8000-000000000012.jpg",
    )

    with pytest.raises(StorageOperationError, match="invalid signed URL"):
        await transport.create_signed_url(reference, 60)


@pytest.mark.anyio
async def test_transport_expands_storage_relative_signed_url() -> None:
    transport = SupabaseStorageTransport(_settings())
    transport._request = AsyncMock(  # type: ignore[method-assign]
        return_value=b'{"signedURL":"/object/sign/event-media/image.jpg?token=value"}'
    )
    reference = StorageObjectRef(
        ImageBucket.EVENT_MEDIA,
        "00000000-0000-4000-8000-000000000013.jpg",
    )

    signed_url = await transport.create_signed_url(reference, 60)

    assert signed_url == (
        "https://project.supabase.co/storage/v1/object/sign/event-media/image.jpg?token=value"
    )


def test_transport_sanitizes_http_failures_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SupabaseStorageTransport(_settings())

    class FailingOpener:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise HTTPError(
                "https://project.supabase.co/storage/v1/object",
                503,
                f"upstream included {TEST_SECRET}",
                cast(Any, None),
                None,
            )

    monkeypatch.setattr(image_storage, "build_opener", lambda *_args: FailingOpener())

    with pytest.raises(StorageOperationError) as raised:
        transport._request_sync(
            "GET",
            "https://project.supabase.co/storage/v1/object",
        )

    assert str(raised.value) == "Storage request failed with HTTP status 503."
    assert raised.value.status_code == 503
    assert TEST_SECRET not in str(raised.value)


def test_transport_normalizes_structured_provider_not_found_without_exposing_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SupabaseStorageTransport(_settings())
    provider_body = b'{"statusCode":"404","error":"Bucket not found","message":"private"}'

    class FailingOpener:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise HTTPError(
                "https://project.supabase.co/storage/v1/bucket/missing",
                400,
                "Bad Request",
                cast(Any, None),
                BytesIO(provider_body),
            )

    monkeypatch.setattr(image_storage, "build_opener", lambda *_args: FailingOpener())

    with pytest.raises(StorageOperationError) as raised:
        transport._request_sync(
            "GET",
            "https://project.supabase.co/storage/v1/bucket/missing",
        )

    assert str(raised.value) == "Storage request failed with HTTP status 400."
    assert raised.value.status_code == 404
    assert "Bucket not found" not in str(raised.value)
    assert "private" not in str(raised.value)
