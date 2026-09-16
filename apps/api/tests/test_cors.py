"""Credentialed CORS configuration and browser-boundary tests."""

from collections.abc import Iterator

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.config import (
    CORS_ORIGINS_VARIABLE,
    DEFAULT_CORS_ORIGINS,
    CorsConfigurationError,
    get_cors_settings,
)
from app.main import CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, app

ALLOWED_ORIGIN = "http://localhost:5173"
UNKNOWN_ORIGIN = "https://attacker.example"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_cors_settings_cache() -> Iterator[None]:
    get_cors_settings.cache_clear()
    yield
    get_cors_settings.cache_clear()


def test_cors_defaults_are_exact_local_frontend_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CORS_ORIGINS_VARIABLE, raising=False)

    settings = get_cors_settings()

    assert settings.allowed_origins == DEFAULT_CORS_ORIGINS
    assert "*" not in settings.allowed_origins
    assert "*" not in CORS_ALLOWED_METHODS
    assert "*" not in CORS_ALLOWED_HEADERS


def test_cors_origins_are_trimmed_normalized_and_deduplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        CORS_ORIGINS_VARIABLE,
        " https://APP.example:443,http://localhost:80,https://app.example ",
    )

    settings = get_cors_settings()

    assert settings.allowed_origins == ("https://app.example", "http://localhost")


@pytest.mark.parametrize(
    "configured_value",
    [
        "",
        "*",
        "https://*.example.com",
        "ftp://app.example.com",
        "https://user:password@app.example.com",
        "https://app.example.com/",
        "https://app.example.com/path",
        "https://app.example.com?preview=true",
        "https://app.example.com#fragment",
        "https://app.example.com,",
        "https://app.example.com:invalid",
    ],
)
def test_invalid_or_unsafe_cors_origins_fail_fast(
    monkeypatch: pytest.MonkeyPatch, configured_value: str
) -> None:
    monkeypatch.setenv(CORS_ORIGINS_VARIABLE, configured_value)

    with pytest.raises(CorsConfigurationError):
        get_cors_settings()


@pytest.mark.anyio
async def test_allowlisted_credentialed_preflight_returns_explicit_policy() -> None:
    headers = {
        "Origin": ALLOWED_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,X-CSRF-Token",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.options("/api/health/database", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert set(response.headers["access-control-allow-methods"].split(", ")) == set(
        CORS_ALLOWED_METHODS
    )
    allowed_headers = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }
    assert {"content-type", "x-csrf-token"} <= allowed_headers
    assert response.headers["vary"] == "Origin"


@pytest.mark.anyio
async def test_allowlisted_simple_request_exposes_credentialed_cors_headers() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/openapi.json",
            headers={"Origin": ALLOWED_ORIGIN, "Cookie": "session=test-only"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.anyio
async def test_unknown_origin_is_rejected_during_preflight() -> None:
    headers = {
        "Origin": UNKNOWN_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,X-CSRF-Token",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.options("/api/health/database", headers=headers)

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("requested_method", "requested_headers"),
    [
        ("TRACE", "Content-Type"),
        ("POST", "Authorization"),
        ("POST", "X-Unapproved-Header"),
    ],
)
async def test_unapproved_methods_and_headers_fail_preflight(
    requested_method: str, requested_headers: str
) -> None:
    headers = {
        "Origin": ALLOWED_ORIGIN,
        "Access-Control-Request-Method": requested_method,
        "Access-Control-Request-Headers": requested_headers,
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.options("/api/health/database", headers=headers)

    assert response.status_code == 400
