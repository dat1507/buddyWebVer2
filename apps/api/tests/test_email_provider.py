"""Configuration, transport, idempotency, and redaction tests for MAIL-001."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from urllib.error import HTTPError, URLError

import pytest
from pydantic import SecretStr

import app.services.email_provider as email_provider
from app.core.config import (
    EMAIL_FROM_ADDRESS_VARIABLE,
    RESEND_API_KEY_VARIABLE,
    EmailConfigurationError,
    EmailProviderSettings,
    get_email_provider_settings,
)
from app.services.email_provider import (
    RESEND_EMAIL_ENDPOINT,
    EmailDeliveryError,
    EmailProviderResponse,
    OutboundEmail,
    ResendEmailProvider,
    UrllibEmailProviderTransport,
)

TEST_API_KEY = "re_test_only_not_a_real_credential"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_email_provider_settings.cache_clear()
    yield
    get_email_provider_settings.cache_clear()


def _settings() -> EmailProviderSettings:
    return EmailProviderSettings(
        api_key=SecretStr(TEST_API_KEY),
        from_address="VGU Buddy <buddy@example.com>",
    )


def test_email_configuration_is_server_only_redacted_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RESEND_API_KEY_VARIABLE, TEST_API_KEY)
    monkeypatch.setenv(EMAIL_FROM_ADDRESS_VARIABLE, " VGU Buddy <buddy@example.com> ")

    settings = get_email_provider_settings()

    assert settings.from_address == "VGU Buddy <buddy@example.com>"
    assert TEST_API_KEY not in repr(settings)

    get_email_provider_settings.cache_clear()
    monkeypatch.delenv(RESEND_API_KEY_VARIABLE)
    with pytest.raises(EmailConfigurationError) as raised:
        get_email_provider_settings()
    assert TEST_API_KEY not in str(raised.value)


@pytest.mark.parametrize("from_address", ["", "sender@example.com\r\nBcc: victim@example.com"])
def test_email_configuration_rejects_unsafe_sender(from_address: str) -> None:
    with pytest.raises(ValueError, match="sender identity"):
        EmailProviderSettings(api_key=SecretStr(TEST_API_KEY), from_address=from_address)


@pytest.mark.anyio
async def test_resend_adapter_uses_fixed_endpoint_plain_text_and_idempotency() -> None:
    transport = MagicMock()
    transport.post = AsyncMock(
        return_value=EmailProviderResponse(status_code=200, body=b'{"id":"provider-id"}')
    )
    provider = ResendEmailProvider(_settings(), transport=transport)
    message = OutboundEmail(
        recipient_email="student@example.com",
        subject="Subject",
        text_body="Plain text only",
    )

    delivery = await provider.send(message, idempotency_key="EMAIL_VERIFY/aggregate")

    assert delivery.provider_message_id == "provider-id"
    assert "student@example.com" not in repr(message)
    assert "Plain text only" not in repr(message)
    assert "provider-id" not in repr(delivery)
    assert TEST_API_KEY not in repr(provider)
    transport.post.assert_awaited_once()
    call = transport.post.await_args
    assert call.args == (RESEND_EMAIL_ENDPOINT,)
    assert call.kwargs["headers"]["Authorization"] == f"Bearer {TEST_API_KEY}"
    assert call.kwargs["headers"]["Idempotency-Key"] == "EMAIL_VERIFY/aggregate"
    assert json.loads(call.kwargs["body"]) == {
        "from": "VGU Buddy <buddy@example.com>",
        "to": ["student@example.com"],
        "subject": "Subject",
        "text": "Plain text only",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (409, True), (429, True), (503, True)],
)
async def test_provider_http_failures_are_sanitized_and_classified(
    status_code: int,
    retryable: bool,
) -> None:
    provider_body = b'{"message":"private provider details"}'
    transport = MagicMock()
    transport.post = AsyncMock(
        return_value=EmailProviderResponse(status_code=status_code, body=provider_body)
    )
    provider = ResendEmailProvider(_settings(), transport=transport)

    with pytest.raises(EmailDeliveryError) as raised:
        await provider.send(
            OutboundEmail("student@example.com", "Subject", "Body"),
            idempotency_key="EVENT/one",
        )

    assert raised.value.retryable is retryable
    assert raised.value.error_code == f"provider_http_{status_code}"
    assert str(raised.value) == "Email delivery failed."
    assert TEST_API_KEY not in str(raised.value)
    assert "private provider details" not in str(raised.value)


@pytest.mark.anyio
async def test_invalid_success_response_is_retryable_without_body_leak() -> None:
    transport = MagicMock()
    transport.post = AsyncMock(
        return_value=EmailProviderResponse(
            status_code=200,
            body=b'{"private":"provider details"}',
        )
    )
    provider = ResendEmailProvider(_settings(), transport=transport)

    with pytest.raises(EmailDeliveryError) as raised:
        await provider.send(
            OutboundEmail("student@example.com", "Subject", "Body"),
            idempotency_key="EVENT/two",
        )

    assert raised.value.retryable is True
    assert raised.value.error_code == "invalid_provider_response"
    assert "provider details" not in str(raised.value)


def test_urllib_transport_never_exposes_http_or_network_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = UrllibEmailProviderTransport()

    class HttpFailure:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise HTTPError(
                RESEND_EMAIL_ENDPOINT,
                503,
                f"provider leaked {TEST_API_KEY}",
                cast(Any, None),
                None,
            )

    monkeypatch.setattr(email_provider, "build_opener", lambda *_args: HttpFailure())
    response = transport._post_sync(
        RESEND_EMAIL_ENDPOINT,
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        body=b"{}",
    )
    assert response == EmailProviderResponse(status_code=503, body=b"")
    assert TEST_API_KEY not in repr(response)

    class NetworkFailure:
        def open(self, *_args: object, **_kwargs: object) -> None:
            raise URLError(f"network leaked {TEST_API_KEY}")

    monkeypatch.setattr(email_provider, "build_opener", lambda *_args: NetworkFailure())
    with pytest.raises(EmailDeliveryError) as raised:
        transport._post_sync(
            RESEND_EMAIL_ENDPOINT,
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
            body=b"{}",
        )
    assert TEST_API_KEY not in str(raised.value)
