"""EMAIL-002 sealed delivery, request orchestration, expiry, and redaction tests."""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.email_verification_requests as request_service
from app.core.config import EmailVerificationDeliverySettings
from app.models import User, UserRole
from app.services.email_outbox import EmailTemplateError
from app.services.email_verification import IssuedEmailVerificationToken
from app.services.email_verification_requests import (
    EMAIL_VERIFICATION_REQUESTED,
    EmailVerificationTemplate,
    request_email_verification,
    seal_email_verification_token,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TOKEN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TOKEN = base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode("ascii")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> EmailVerificationDeliverySettings:
    return EmailVerificationDeliverySettings(
        public_app_base_url="https://buddy.example",
        sealing_key=SecretBytes(bytes(reversed(range(32)))),
    )


def _user(*, verified: bool = False) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=UserRole.USER,
        is_active=True,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
    )


def _session(user: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=user)
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


def test_sealed_payload_renders_only_in_memory_and_rejects_tampering_or_expiry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = _settings()
    payload = seal_email_verification_token(
        TOKEN,
        NOW + timedelta(minutes=15),
        settings,
        random_bytes=lambda size: b"n" * size,
    )

    serialized = repr(payload)
    assert TOKEN not in serialized
    assert set(payload) == {"version", "nonce", "sealed_value", "expires_at"}
    renderer = EmailVerificationTemplate(settings, clock=lambda: NOW)
    content = renderer.render(payload)
    assert content.subject == "Verify your VGU Buddy email"
    assert f"https://buddy.example/verify-email?token={TOKEN}" in content.text_body
    assert TOKEN not in repr(content)

    tampered = dict(payload)
    tampered["sealed_value"] = f"{str(payload['sealed_value'])[:-1]}A"
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(EmailTemplateError):
            renderer.render(tampered)
    with pytest.raises(EmailTemplateError) as expired:
        EmailVerificationTemplate(
            settings,
            clock=lambda: NOW + timedelta(minutes=15),
        ).render(payload)
    assert expired.value.error_code == "verification_link_expired"
    assert TOKEN not in str(expired.value)
    assert TOKEN not in caplog.text


@pytest.mark.anyio
async def test_request_stages_current_address_token_and_outbox_without_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, session = _session(user)
    issued = IssuedEmailVerificationToken(
        token_id=TOKEN_ID,
        token=TOKEN,
        expires_at=NOW + timedelta(minutes=15),
    )
    issue = AsyncMock(return_value=issued)
    enqueue = AsyncMock()
    monkeypatch.setattr(request_service, "issue_email_verification_token", issue)
    monkeypatch.setattr(request_service, "enqueue_transactional_email", enqueue)

    result = await request_email_verification(session, user.id, _settings())

    assert result.created is True
    issue.assert_awaited_once_with(session, user.id)
    assert enqueue.await_args is not None
    kwargs = enqueue.await_args.kwargs
    assert kwargs["event_type"] == EMAIL_VERIFICATION_REQUESTED
    assert kwargs["aggregate_id"] == TOKEN_ID
    assert kwargs["recipient_user_id"] == user.id
    assert kwargs["recipient_email"] == user.email
    assert kwargs["idempotency_key"] == f"{EMAIL_VERIFICATION_REQUESTED}/{TOKEN_ID}"
    assert TOKEN not in repr(kwargs["payload"])
    assert not hasattr(mock, "commit") or mock.commit.await_count == 0
    assert mock.scalar.await_args is not None
    statement = mock.scalar.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    assert "FOR UPDATE" in str(statement.compile(dialect=dialect))


@pytest.mark.anyio
async def test_already_verified_request_is_explicitly_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user(verified=True))
    issue = AsyncMock()
    enqueue = AsyncMock()
    monkeypatch.setattr(request_service, "issue_email_verification_token", issue)
    monkeypatch.setattr(request_service, "enqueue_transactional_email", enqueue)

    result = await request_email_verification(session, USER_ID, _settings())

    assert result.created is False
    issue.assert_not_awaited()
    enqueue.assert_not_awaited()
    mock.add.assert_not_called()


def test_delivery_settings_are_redacted_and_require_https_and_a_32_byte_key() -> None:
    settings = _settings()
    assert bytes(reversed(range(32))).hex() not in repr(settings)
    with pytest.raises(ValueError, match="base URL"):
        EmailVerificationDeliverySettings(
            public_app_base_url="http://buddy.example",
            sealing_key=SecretBytes(bytes(32)),
        )
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        EmailVerificationDeliverySettings(
            public_app_base_url="https://buddy.example",
            sealing_key=SecretBytes(bytes(31)),
        )
