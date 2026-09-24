"""Provider-neutral transactional email contract and Resend adapter."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.config import EmailProviderSettings

RESEND_EMAIL_ENDPOINT: Final = "https://api.resend.com/emails"
PROVIDER_TIMEOUT_SECONDS: Final = 10.0
_MAX_PROVIDER_RESPONSE_BYTES: Final = 4096


class EmailDeliveryError(RuntimeError):
    """Sanitized provider failure with worker-safe retry metadata."""

    def __init__(self, *, retryable: bool, error_code: str) -> None:
        super().__init__("Email delivery failed.")
        self.retryable = retryable
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class OutboundEmail:
    """Rendered email whose recipient and body are excluded from representations."""

    recipient_email: str = field(repr=False)
    subject: str = field(repr=False)
    text_body: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not self.recipient_email.strip()
            or len(self.recipient_email) > 320
            or "\r" in self.recipient_email
            or "\n" in self.recipient_email
        ):
            raise ValueError("Email recipient is unsafe or invalid.")
        if not self.subject.strip() or "\r" in self.subject or "\n" in self.subject:
            raise ValueError("Email subject is unsafe or invalid.")
        if not self.text_body.strip():
            raise ValueError("Email text body must not be empty.")


@dataclass(frozen=True, slots=True)
class EmailDelivery:
    """Provider acknowledgement kept out of user-facing responses and logs."""

    provider_message_id: str = field(repr=False)


class EmailProvider(Protocol):
    async def send(
        self,
        message: OutboundEmail,
        *,
        idempotency_key: str,
    ) -> EmailDelivery: ...


@dataclass(frozen=True, slots=True)
class EmailProviderResponse:
    status_code: int
    body: bytes = field(repr=False)


class EmailProviderTransport(Protocol):
    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> EmailProviderResponse: ...


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        return None


class UrllibEmailProviderTransport:
    """Small async wrapper over a fixed-origin HTTPS request."""

    def __init__(self, *, timeout_seconds: float = PROVIDER_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    def _post_sync(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> EmailProviderResponse:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with build_opener(_RejectRedirects()).open(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                return EmailProviderResponse(
                    status_code=int(response.status),
                    body=cast(bytes, response.read(_MAX_PROVIDER_RESPONSE_BYTES)),
                )
        except HTTPError as error:
            return EmailProviderResponse(status_code=error.code, body=b"")
        except (OSError, TimeoutError, URLError):
            raise EmailDeliveryError(
                retryable=True,
                error_code="provider_unavailable",
            ) from None

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> EmailProviderResponse:
        return await asyncio.to_thread(
            self._post_sync,
            url,
            headers=headers,
            body=body,
        )


class ResendEmailProvider:
    """Send plain-text transactional email with provider-side idempotency."""

    def __init__(
        self,
        settings: EmailProviderSettings,
        *,
        transport: EmailProviderTransport | None = None,
    ) -> None:
        self._api_key = settings.api_key.get_secret_value()
        self._from_address = settings.from_address
        self._transport = transport or UrllibEmailProviderTransport()

    async def send(
        self,
        message: OutboundEmail,
        *,
        idempotency_key: str,
    ) -> EmailDelivery:
        normalized_key = idempotency_key.strip()
        if (
            not normalized_key
            or len(normalized_key) > 256
            or "\r" in normalized_key
            or "\n" in normalized_key
        ):
            raise EmailDeliveryError(retryable=False, error_code="invalid_idempotency_key")
        body = json.dumps(
            {
                "from": self._from_address,
                "to": [message.recipient_email],
                "subject": message.subject,
                "text": message.text_body,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        response = await self._transport.post(
            RESEND_EMAIL_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": normalized_key,
                "User-Agent": "vgu-buddy-api/0.1",
            },
            body=body,
        )
        if not 200 <= response.status_code < 300:
            retryable = response.status_code in {408, 409, 425, 429} or response.status_code >= 500
            raise EmailDeliveryError(
                retryable=retryable,
                error_code=f"provider_http_{response.status_code}",
            )
        try:
            payload = json.loads(response.body)
            message_id = payload.get("id") if isinstance(payload, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            message_id = None
        if not isinstance(message_id, str) or not message_id.strip() or len(message_id) > 200:
            raise EmailDeliveryError(
                retryable=True,
                error_code="invalid_provider_response",
            )
        return EmailDelivery(provider_message_id=message_id.strip())
