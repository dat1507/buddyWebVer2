"""Security and behavior tests for JWT and auth-cookie primitives."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Response
from pydantic import SecretBytes

from app.core.config import (
    AUTH_COOKIE_SECURE_VARIABLE,
    AUTH_JWT_SECRET_VARIABLE,
    AuthConfigurationError,
    AuthTokenSettings,
    get_auth_token_settings,
)
from app.models import UserRole
from app.services import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    TokenValidationError,
    clear_auth_cookies,
    create_token_pair,
    prepare_refresh_rotation,
    set_auth_cookies,
    verify_access_token,
    verify_refresh_token,
)
from app.services.tokens import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_SIGNING_KEY = bytes(range(32))


def _settings(*, secure_cookies: bool = True, key: bytes = TEST_SIGNING_KEY) -> AuthTokenSettings:
    return AuthTokenSettings(
        signing_key=SecretBytes(key),
        secure_cookies=secure_cookies,
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _base_access_payload(now: datetime) -> dict[str, object]:
    return {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": str(TEST_USER_ID),
        "sid": str(TEST_SESSION_ID),
        "jti": str(uuid4()),
        "token_type": "access",
        "role": UserRole.USER.value,
        "iat": now,
        "nbf": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }


def _sign(
    payload: dict[str, object],
    *,
    key: bytes = TEST_SIGNING_KEY,
    token_header_type: str = "JWT",
) -> str:
    return jwt.encode(
        payload,
        key,
        algorithm=JWT_ALGORITHM,
        headers={"typ": token_header_type},
    )


def test_auth_settings_decode_a_dedicated_256_bit_secret_and_default_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_secret = base64.urlsafe_b64encode(TEST_SIGNING_KEY).rstrip(b"=").decode("ascii")
    monkeypatch.setenv(AUTH_JWT_SECRET_VARIABLE, encoded_secret)
    monkeypatch.delenv(AUTH_COOKIE_SECURE_VARIABLE, raising=False)
    get_auth_token_settings.cache_clear()

    try:
        settings = get_auth_token_settings()
    finally:
        get_auth_token_settings.cache_clear()

    assert settings.signing_key.get_secret_value() == TEST_SIGNING_KEY
    assert settings.secure_cookies is True
    assert encoded_secret not in repr(settings)


@pytest.mark.parametrize(
    ("secret", "message"),
    [
        (None, AUTH_JWT_SECRET_VARIABLE),
        ("not valid base64!", "URL-safe base64"),
        (base64.b64encode(b"\xfb" * 32).decode("ascii"), "URL-safe base64"),
        (base64.urlsafe_b64encode(b"too-short").decode("ascii"), "32 random bytes"),
    ],
)
def test_auth_settings_reject_missing_or_weak_signing_keys(
    monkeypatch: pytest.MonkeyPatch,
    secret: str | None,
    message: str,
) -> None:
    if secret is None:
        monkeypatch.delenv(AUTH_JWT_SECRET_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(AUTH_JWT_SECRET_VARIABLE, secret)
    get_auth_token_settings.cache_clear()

    with pytest.raises(AuthConfigurationError, match=message):
        get_auth_token_settings()

    get_auth_token_settings.cache_clear()


def test_auth_settings_require_an_explicit_boolean_cookie_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_secret = base64.urlsafe_b64encode(TEST_SIGNING_KEY).decode("ascii")
    monkeypatch.setenv(AUTH_JWT_SECRET_VARIABLE, encoded_secret)
    monkeypatch.setenv(AUTH_COOKIE_SECURE_VARIABLE, "sometimes")
    get_auth_token_settings.cache_clear()

    with pytest.raises(AuthConfigurationError, match="exactly true or false"):
        get_auth_token_settings()

    get_auth_token_settings.cache_clear()


def test_auth_settings_reject_a_directly_constructed_weak_key() -> None:
    with pytest.raises(ValueError, match="at least 32 bytes"):
        AuthTokenSettings(signing_key=SecretBytes(b"weak"))


def test_auth_settings_allow_an_explicit_local_http_cookie_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded_secret = base64.urlsafe_b64encode(TEST_SIGNING_KEY).decode("ascii")
    monkeypatch.setenv(AUTH_JWT_SECRET_VARIABLE, encoded_secret)
    monkeypatch.setenv(AUTH_COOKIE_SECURE_VARIABLE, "false")
    get_auth_token_settings.cache_clear()

    try:
        settings = get_auth_token_settings()
    finally:
        get_auth_token_settings.cache_clear()

    assert settings.secure_cookies is False


def test_token_pair_has_scoped_claims_and_fixed_lifetimes() -> None:
    now = _now()
    pair = create_token_pair(
        TEST_USER_ID,
        UserRole.ADMIN,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now,
    )

    access = verify_access_token(pair.access_token, _settings())
    refresh = verify_refresh_token(pair.refresh_token, _settings())

    assert access.user_id == refresh.user_id == TEST_USER_ID
    assert access.session_id == refresh.session_id == TEST_SESSION_ID
    assert access.role is UserRole.ADMIN
    assert access.token_id == pair.access_token_id
    assert refresh.token_id == pair.refresh_token_id
    assert access.expires_at - access.issued_at == ACCESS_TOKEN_TTL
    assert refresh.expires_at - refresh.issued_at == REFRESH_TOKEN_TTL
    assert pair.access_token not in repr(pair)
    assert pair.refresh_token not in repr(pair)


def test_each_token_pair_uses_fresh_session_and_token_identifiers() -> None:
    first = create_token_pair(TEST_USER_ID, UserRole.USER, _settings())
    second = create_token_pair(TEST_USER_ID, UserRole.USER, _settings())

    assert first.session_id != second.session_id
    assert first.access_token_id != second.access_token_id
    assert first.refresh_token_id != second.refresh_token_id
    assert first.access_token != second.access_token
    assert first.refresh_token != second.refresh_token


def test_refresh_rotation_preserves_session_and_replaces_both_jtis() -> None:
    now = _now()
    original = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now,
    )

    rotation = prepare_refresh_rotation(
        original.refresh_token,
        UserRole.ADMIN,
        _settings(),
        now=now + timedelta(seconds=1),
    )
    replacement_access = verify_access_token(rotation.replacement.access_token, _settings())
    replacement_refresh = verify_refresh_token(rotation.replacement.refresh_token, _settings())

    assert rotation.consumed_token_id == original.refresh_token_id
    assert rotation.replacement.session_id == original.session_id
    assert rotation.replacement.access_token_id != original.access_token_id
    assert rotation.replacement.refresh_token_id != original.refresh_token_id
    assert replacement_access.role is UserRole.ADMIN
    assert replacement_refresh.session_id == TEST_SESSION_ID


def test_access_and_refresh_tokens_are_not_interchangeable() -> None:
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, _settings())

    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(pair.refresh_token, _settings())
    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_refresh_token(pair.access_token, _settings())


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
def test_malformed_tokens_fail_with_one_sanitized_error(token: str) -> None:
    with pytest.raises(TokenValidationError, match="^Token is invalid or expired\\.$") as error:
        verify_access_token(token, _settings())

    if token:
        assert token not in str(error.value)


def test_verification_rejects_wrong_key_expired_and_future_tokens() -> None:
    settings = _settings()
    wrong_key_pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(key=b"x" * 32),
    )
    expired_pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        settings,
        now=_now() - REFRESH_TOKEN_TTL - timedelta(minutes=1),
    )
    future_pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        settings,
        now=_now() + timedelta(minutes=5),
    )

    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(wrong_key_pair.access_token, settings)
    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_refresh_token(expired_pair.refresh_token, settings)
    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(future_pair.access_token, settings)


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("aud", "another-audience"),
        ("iss", "another-issuer"),
        ("sub", "not-a-uuid"),
        ("role", "SUPERADMIN"),
        ("token_type", "refresh"),
    ],
)
def test_verification_rejects_invalid_trusted_claims(claim: str, value: object) -> None:
    payload = _base_access_payload(_now())
    payload[claim] = value

    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(_sign(payload), _settings())


def test_verification_rejects_missing_claims_and_non_allowlisted_algorithm() -> None:
    payload = _base_access_payload(_now())
    del payload["jti"]
    unsigned_token = jwt.encode(payload, key="", algorithm="none")

    for token in (_sign(payload), unsigned_token):
        with pytest.raises(TokenValidationError, match="invalid or expired"):
            verify_access_token(token, _settings())


def test_verification_rejects_an_unexpected_jose_type_header() -> None:
    token = _sign(_base_access_payload(_now()), token_header_type="at+jwt")

    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(token, _settings())


def test_verification_rejects_a_signed_token_with_an_extended_lifetime() -> None:
    payload = _base_access_payload(_now())
    payload["exp"] = _now() + timedelta(hours=1)

    with pytest.raises(TokenValidationError, match="invalid or expired"):
        verify_access_token(_sign(payload), _settings())


def test_production_cookies_are_host_only_secure_httponly_and_not_cached() -> None:
    response = Response()
    pair = create_token_pair(TEST_USER_ID, UserRole.USER, _settings())

    set_auth_cookies(response, pair, _settings())

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert cookies[0].startswith("__Host-vgu_buddy_access=")
    assert cookies[1].startswith("__Host-vgu_buddy_refresh=")
    for cookie in cookies:
        assert "Domain=" not in cookie
        assert "HttpOnly" in cookie
        assert "Path=/" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" in cookie
    assert "Max-Age=900" in cookies[0]
    assert "Max-Age=604800" in cookies[1]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_local_http_cookies_use_explicit_development_names_without_secure() -> None:
    settings = _settings(secure_cookies=False)
    response = Response()

    set_auth_cookies(
        response,
        create_token_pair(TEST_USER_ID, UserRole.USER, settings),
        settings,
    )

    cookies = response.headers.getlist("set-cookie")
    assert cookies[0].startswith("vgu_buddy_access_dev=")
    assert cookies[1].startswith("vgu_buddy_refresh_dev=")
    assert all("Secure" not in cookie for cookie in cookies)
    assert all("HttpOnly" in cookie for cookie in cookies)


@pytest.mark.parametrize("secure_cookies", [True, False])
def test_clear_auth_cookies_uses_matching_names_and_scope(secure_cookies: bool) -> None:
    response = Response()

    clear_auth_cookies(response, _settings(secure_cookies=secure_cookies))

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert all("Max-Age=0" in cookie for cookie in cookies)
    assert all("HttpOnly" in cookie for cookie in cookies)
    assert all("Path=/" in cookie for cookie in cookies)
    assert all("SameSite=lax" in cookie for cookie in cookies)
    assert all(("Secure" in cookie) is secure_cookies for cookie in cookies)
    assert response.headers["cache-control"] == "no-store"
