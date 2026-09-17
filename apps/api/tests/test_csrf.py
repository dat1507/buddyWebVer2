"""Security and behavior tests for signed double-submit CSRF protection."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import Request, Response
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes

from app.core.config import (
    AUTH_COOKIE_SECURE_VARIABLE,
    AUTH_CSRF_SECRET_VARIABLE,
    CORS_ORIGINS_VARIABLE,
    AuthConfigurationError,
    CsrfSettings,
    get_csrf_settings,
)
from app.main import app
from app.services import (
    CSRF_HEADER_NAME,
    PREAUTH_CSRF_TTL,
    SESSION_CSRF_TTL,
    CsrfValidationError,
    clear_csrf_cookie,
    create_preauth_csrf_token,
    create_session_csrf_token,
    set_csrf_cookie,
    verify_csrf_request,
    verify_csrf_token,
)
from app.services.csrf import MAX_CSRF_TOKEN_LENGTH

ALLOWED_ORIGIN = "https://app.example.com"
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_csrf_settings_cache() -> Iterator[None]:
    get_csrf_settings.cache_clear()
    yield
    get_csrf_settings.cache_clear()


def _settings(*, secure_cookies: bool = True) -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(TEST_SIGNING_KEY),
        secure_cookies=secure_cookies,
        trusted_origins=(ALLOWED_ORIGIN,),
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _request(
    token: str,
    *,
    settings: CsrfSettings | None = None,
    method: str = "POST",
    origin: str | None = ALLOWED_ORIGIN,
    referer: str | None = None,
    header_token: str | None = None,
    cookie_token: str | None = None,
    duplicate_origin: bool = False,
    duplicate_header: bool = False,
) -> Request:
    current_settings = settings or _settings()
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode("ascii")))
        if duplicate_origin:
            headers.append((b"origin", origin.encode("ascii")))
    if referer is not None:
        headers.append((b"referer", referer.encode("ascii")))
    if header_token is not None or token:
        supplied_header = header_token if header_token is not None else token
        headers.append(
            (CSRF_HEADER_NAME.lower().encode("ascii"), supplied_header.encode("latin-1"))
        )
        if duplicate_header:
            headers.append(
                (CSRF_HEADER_NAME.lower().encode("ascii"), supplied_header.encode("latin-1"))
            )
    supplied_cookie = cookie_token if cookie_token is not None else token
    if supplied_cookie:
        cookie_name = (
            "__Host-vgu_buddy_csrf" if current_settings.secure_cookies else "vgu_buddy_csrf_dev"
        )
        headers.append((b"cookie", f"{cookie_name}={supplied_cookie}".encode("latin-1")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": "/api/test",
            "raw_path": b"/api/test",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
        }
    )


def test_csrf_settings_use_an_independent_256_bit_secret_and_exact_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_secret = base64.urlsafe_b64encode(TEST_SIGNING_KEY).rstrip(b"=").decode("ascii")
    monkeypatch.setenv(AUTH_CSRF_SECRET_VARIABLE, encoded_secret)
    monkeypatch.setenv(CORS_ORIGINS_VARIABLE, f" {ALLOWED_ORIGIN}:443,{ALLOWED_ORIGIN} ")
    monkeypatch.delenv(AUTH_COOKIE_SECURE_VARIABLE, raising=False)

    settings = get_csrf_settings()

    assert settings.signing_key.get_secret_value() == TEST_SIGNING_KEY
    assert settings.secure_cookies is True
    assert settings.trusted_origins == (ALLOWED_ORIGIN,)
    assert encoded_secret not in repr(settings)


@pytest.mark.parametrize(
    ("secret", "message"),
    [
        (None, AUTH_CSRF_SECRET_VARIABLE),
        ("not valid base64!", "URL-safe base64"),
        (base64.b64encode(b"\xfb" * 32).decode("ascii"), "URL-safe base64"),
        (base64.urlsafe_b64encode(b"too-short").decode("ascii"), "32 random bytes"),
    ],
)
def test_csrf_settings_reject_missing_or_weak_signing_keys(
    monkeypatch: pytest.MonkeyPatch,
    secret: str | None,
    message: str,
) -> None:
    if secret is None:
        monkeypatch.delenv(AUTH_CSRF_SECRET_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(AUTH_CSRF_SECRET_VARIABLE, secret)

    with pytest.raises(AuthConfigurationError, match=message):
        get_csrf_settings()


def test_csrf_settings_reject_a_directly_constructed_weak_key() -> None:
    with pytest.raises(ValueError, match="at least 32 bytes"):
        CsrfSettings(signing_key=SecretBytes(b"weak"), trusted_origins=(ALLOWED_ORIGIN,))


@pytest.mark.parametrize("origins", [(), ("*",), ("https://app.example.com/path",)])
def test_csrf_settings_reject_directly_constructed_unsafe_origins(
    origins: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="trusted CSRF origin|Trusted CSRF origins"):
        CsrfSettings(signing_key=SecretBytes(TEST_SIGNING_KEY), trusted_origins=origins)


def test_preauth_tokens_are_signed_random_and_fixed_lifetime() -> None:
    now = _now()
    first = create_preauth_csrf_token(_settings(), now=now)
    second = create_preauth_csrf_token(_settings(), now=now)

    claims = verify_csrf_token(
        first.value,
        _settings(),
        expected_scope="preauth",
        now=now,
    )

    assert first.value != second.value
    assert claims.scope == "preauth"
    assert claims.issued_at == now
    assert claims.expires_at - claims.issued_at == PREAUTH_CSRF_TTL
    assert first.value not in repr(first)


def test_session_token_is_bound_to_one_refresh_session() -> None:
    now = _now()
    token = create_session_csrf_token(TEST_SESSION_ID, _settings(), now=now)

    claims = verify_csrf_token(
        token.value,
        _settings(),
        expected_scope="session",
        session_id=TEST_SESSION_ID,
        now=now,
    )

    assert claims.expires_at - claims.issued_at == SESSION_CSRF_TTL
    with pytest.raises(CsrfValidationError, match="^CSRF validation failed\\.$"):
        verify_csrf_token(
            token.value,
            _settings(),
            expected_scope="session",
            session_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            now=now,
        )
    with pytest.raises(CsrfValidationError, match="^CSRF validation failed\\.$"):
        verify_csrf_token(token.value, _settings(), expected_scope="session", now=now)


def test_preauth_and_session_tokens_are_not_interchangeable() -> None:
    preauth = create_preauth_csrf_token(_settings())
    session = create_session_csrf_token(TEST_SESSION_ID, _settings())

    with pytest.raises(CsrfValidationError, match="validation failed"):
        verify_csrf_token(
            preauth.value,
            _settings(),
            expected_scope="session",
            session_id=TEST_SESSION_ID,
        )
    with pytest.raises(CsrfValidationError, match="validation failed"):
        verify_csrf_token(session.value, _settings(), expected_scope="preauth")


@pytest.mark.parametrize("token", ["", "not-a-token", "v1.a.b", "x" * 1025])
def test_malformed_tokens_fail_with_one_sanitized_error(token: str) -> None:
    with pytest.raises(CsrfValidationError, match="^CSRF validation failed\\.$") as error:
        verify_csrf_token(token, _settings(), expected_scope="preauth")

    if token and len(token) <= MAX_CSRF_TOKEN_LENGTH:
        assert token not in str(error.value)


def test_verification_rejects_tampered_wrong_key_expired_and_future_tokens() -> None:
    now = _now()
    valid = create_preauth_csrf_token(_settings(), now=now)
    tampered = f"{valid.value[:-1]}{'A' if valid.value[-1] != 'A' else 'B'}"
    wrong_key = CsrfSettings(
        signing_key=SecretBytes(b"x" * 32),
        trusted_origins=(ALLOWED_ORIGIN,),
    )
    expired = create_preauth_csrf_token(
        _settings(), now=now - PREAUTH_CSRF_TTL - timedelta(minutes=1)
    )
    future = create_preauth_csrf_token(_settings(), now=now + timedelta(minutes=1))

    for token, settings in (
        (tampered, _settings()),
        (valid.value, wrong_key),
        (expired.value, _settings()),
        (future.value, _settings()),
    ):
        with pytest.raises(CsrfValidationError, match="validation failed"):
            verify_csrf_token(token, settings, expected_scope="preauth", now=now)


def test_noncanonical_signature_pad_bits_are_always_rejected() -> None:
    token = create_preauth_csrf_token(_settings(), now=_now())
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    final_index = alphabet.index(token.value[-1])
    assert final_index % 4 == 0  # A 32-byte SHA-256 signature has two unused base64 pad bits.
    noncanonical = token.value[:-1] + alphabet[final_index + 1]
    with pytest.raises(CsrfValidationError, match="^CSRF validation failed\\.$"):
        verify_csrf_token(noncanonical, _settings(), expected_scope="preauth", now=_now())


def test_request_verification_accepts_exact_origin_and_referer_fallback() -> None:
    token = create_preauth_csrf_token(_settings())

    origin_claims = verify_csrf_request(
        _request(token.value), _settings(), expected_scope="preauth"
    )
    referer_claims = verify_csrf_request(
        _request(
            token.value,
            origin=None,
            referer=f"{ALLOWED_ORIGIN}/login?from=landing",
        ),
        _settings(),
        expected_scope="preauth",
    )

    assert origin_claims.scope == referer_claims.scope == "preauth"


@pytest.mark.parametrize(
    ("origin", "referer", "duplicate_origin"),
    [
        ("https://attacker.example", None, False),
        ("https://app.example.com.attacker.example", None, False),
        ("null", None, False),
        (None, None, False),
        (ALLOWED_ORIGIN, None, True),
        (None, "https://user:password@app.example.com/path", False),
    ],
)
def test_request_verification_rejects_untrusted_or_ambiguous_sources(
    origin: str | None,
    referer: str | None,
    duplicate_origin: bool,
) -> None:
    token = create_preauth_csrf_token(_settings())

    with pytest.raises(CsrfValidationError, match="validation failed"):
        verify_csrf_request(
            _request(
                token.value,
                origin=origin,
                referer=referer,
                duplicate_origin=duplicate_origin,
            ),
            _settings(),
            expected_scope="preauth",
        )


def test_request_verification_rejects_missing_mismatched_and_duplicate_evidence() -> None:
    token = create_preauth_csrf_token(_settings())
    another = create_preauth_csrf_token(_settings())
    requests = (
        _request(token.value, header_token=""),
        _request(token.value, cookie_token=""),
        _request(token.value, cookie_token=another.value),
        _request(token.value, duplicate_header=True),
        _request(token.value, method="GET"),
        _request(token.value, header_token="é", cookie_token="é"),
    )

    for request in requests:
        with pytest.raises(CsrfValidationError, match="validation failed"):
            verify_csrf_request(request, _settings(), expected_scope="preauth")


def test_production_cookie_is_host_only_secure_httponly_and_not_cached() -> None:
    response = Response()
    token = create_preauth_csrf_token(_settings())

    set_csrf_cookie(response, token, _settings())

    cookie = response.headers["set-cookie"]
    assert cookie.startswith("__Host-vgu_buddy_csrf=")
    assert "Domain=" not in cookie
    assert "HttpOnly" in cookie
    assert "Path=/" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie
    assert "Max-Age=3600" in cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_local_session_cookie_and_clear_use_matching_development_scope() -> None:
    settings = _settings(secure_cookies=False)
    response = Response()
    token = create_session_csrf_token(TEST_SESSION_ID, settings)

    set_csrf_cookie(response, token, settings)
    clear_csrf_cookie(response, settings)

    set_cookie, clear_cookie = response.headers.getlist("set-cookie")
    assert set_cookie.startswith("vgu_buddy_csrf_dev=")
    assert "Max-Age=604800" in set_cookie
    assert "Secure" not in set_cookie
    assert "HttpOnly" in set_cookie
    assert clear_cookie.startswith("vgu_buddy_csrf_dev=")
    assert "Max-Age=0" in clear_cookie
    assert "Secure" not in clear_cookie
    assert "HttpOnly" in clear_cookie
    assert "Path=/" in clear_cookie


@pytest.mark.anyio
async def test_csrf_endpoint_returns_and_sets_fresh_matching_preauth_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_secret = base64.urlsafe_b64encode(TEST_SIGNING_KEY).decode("ascii")
    monkeypatch.setenv(AUTH_CSRF_SECRET_VARIABLE, encoded_secret)
    monkeypatch.setenv(AUTH_COOKIE_SECURE_VARIABLE, "false")
    monkeypatch.setenv(CORS_ORIGINS_VARIABLE, ALLOWED_ORIGIN)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        first = await client.get("/api/auth/csrf")
        second = await client.get("/api/auth/csrf")

    first_token = first.json()["csrf_token"]
    second_token = second.json()["csrf_token"]
    assert first.status_code == second.status_code == 200
    assert first.cookies["vgu_buddy_csrf_dev"] == first_token
    assert second.cookies["vgu_buddy_csrf_dev"] == second_token
    assert first_token != second_token
    assert "HttpOnly" in first.headers["set-cookie"]
    assert "Secure" not in first.headers["set-cookie"]
    assert first.headers["cache-control"] == "no-store"
    verify_csrf_token(first_token, get_csrf_settings(), expected_scope="preauth")


@pytest.mark.anyio
async def test_csrf_endpoint_fails_closed_with_a_sanitized_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(AUTH_CSRF_SECRET_VARIABLE, raising=False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/auth/csrf")

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured."}
    assert AUTH_CSRF_SECRET_VARIABLE not in response.text
