"""Unit, replay, and redaction tests for the EMAIL-001A token service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailVerificationToken, User, UserRole
from app.services.email_verification import (
    EMAIL_VERIFICATION_TOKEN_BYTES,
    EMAIL_VERIFICATION_TOKEN_TTL,
    EmailVerificationTokenError,
    consume_email_verification_token,
    digest_email_verification_token,
    issue_email_verification_token,
)

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
INVALID_MESSAGE = "Verification token is invalid or expired."


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _plaintext(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _user(
    *,
    email: str = "student@example.com",
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        id=TEST_USER_ID,
        email=email,
        password_hash=TEST_PASSWORD_HASH,
        role=UserRole.USER,
        is_active=is_active,
        email_verified=False,
        email_verified_at=None,
        deleted_at=deleted_at,
    )


def _stored_token(
    raw: bytes,
    *,
    expires_at: datetime = NOW + EMAIL_VERIFICATION_TOKEN_TTL,
    consumed_at: datetime | None = None,
    superseded_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> EmailVerificationToken:
    return EmailVerificationToken(
        id=uuid4(),
        user_id=TEST_USER_ID,
        token_digest=digest_email_verification_token(_plaintext(raw)),
        email_snapshot="student@example.com",
        expires_at=expires_at,
        consumed_at=consumed_at,
        superseded_at=superseded_at,
        deleted_at=deleted_at,
        created_at=NOW - timedelta(minutes=1),
        updated_at=NOW - timedelta(minutes=1),
    )


@pytest.mark.anyio
async def test_issue_uses_32_random_bytes_and_supersedes_the_current_token() -> None:
    entropy = bytes(range(EMAIL_VERIFICATION_TOKEN_BYTES))
    previous = _stored_token(bytes(reversed(entropy)))
    user = _user()
    mock, session = _session()
    mock.scalar.side_effect = [user, previous]
    requested_sizes: list[int] = []

    def deterministic_random(size: int) -> bytes:
        requested_sizes.append(size)
        return entropy

    issued = await issue_email_verification_token(
        session,
        user.id,
        clock=lambda: NOW,
        random_bytes=deterministic_random,
    )

    assert requested_sizes == [32]
    assert issued.token == _plaintext(entropy)
    assert len(issued.token) == 43
    assert issued.expires_at == NOW + timedelta(minutes=15)
    assert issued.expires_at - NOW == EMAIL_VERIFICATION_TOKEN_TTL
    assert issued.token not in repr(issued)
    assert previous.superseded_at == NOW

    stored = mock.add.call_args.args[0]
    assert isinstance(stored, EmailVerificationToken)
    assert stored.user_id == user.id
    assert issued.token_id == stored.id
    assert stored.email_snapshot == user.email
    assert stored.created_at == NOW
    assert stored.expires_at - stored.created_at == EMAIL_VERIFICATION_TOKEN_TTL
    assert stored.token_digest == digest_email_verification_token(issued.token)
    assert stored.token_digest != issued.token.encode("ascii")
    assert not hasattr(stored, "token")
    mock.flush.assert_awaited_once_with()

    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    statements = [
        str(call.args[0].compile(dialect=dialect)) for call in mock.scalar.await_args_list
    ]
    assert all("FOR UPDATE" in statement for statement in statements)


@pytest.mark.parametrize(
    "raw",
    [bytes(range(32)), b"\x00" * 32, b"\xff" * 32],
)
def test_digest_accepts_only_canonical_urlsafe_32_byte_tokens(raw: bytes) -> None:
    plaintext = _plaintext(raw)
    digest = digest_email_verification_token(plaintext)

    assert len(plaintext) == 43
    assert set(plaintext) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )
    assert len(digest) == hashlib.sha256().digest_size
    assert digest != hashlib.sha256(raw).digest()
    assert digest == digest_email_verification_token(plaintext)


@pytest.mark.parametrize("invalid", ["", "not-a-token", "A" * 42, "A" * 44, "A" * 42 + "="])
def test_invalid_token_formats_fail_with_one_generic_error(invalid: str) -> None:
    with pytest.raises(EmailVerificationTokenError, match=f"^{INVALID_MESSAGE}$"):
        digest_email_verification_token(invalid)


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["missing", "inactive", "deleted"])
async def test_issue_rejects_unusable_owner_before_generating_entropy(state: str) -> None:
    user = _user(
        is_active=state != "inactive",
        deleted_at=NOW if state == "deleted" else None,
    )
    mock, session = _session()
    mock.scalar.return_value = None if state == "missing" else user
    random_source = MagicMock(return_value=bytes(range(32)))

    with pytest.raises(EmailVerificationTokenError, match=f"^{INVALID_MESSAGE}$"):
        await issue_email_verification_token(
            session,
            TEST_USER_ID,
            clock=lambda: NOW,
            random_bytes=random_source,
        )

    random_source.assert_not_called()
    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_issue_rejects_a_broken_random_source_without_persistence() -> None:
    previous = _stored_token(bytes(reversed(range(32))))
    mock, session = _session()
    mock.scalar.side_effect = [_user(), previous]

    with pytest.raises(ValueError, match=r"^Random source must return exactly 32 bytes\.$"):
        await issue_email_verification_token(
            session,
            TEST_USER_ID,
            clock=lambda: NOW,
            random_bytes=lambda _: b"too-short",
        )

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()
    assert previous.superseded_at is None


@pytest.mark.anyio
async def test_consume_locks_owner_then_token_and_marks_one_use() -> None:
    raw = bytes(range(32))
    stored = _stored_token(raw, expires_at=NOW + timedelta(microseconds=1))
    user = _user()
    mock, session = _session()
    mock.scalar.side_effect = [stored, user, stored]

    with patch(
        "app.services.email_verification.hmac.compare_digest",
        wraps=hmac.compare_digest,
    ) as safe_compare:
        consumed = await consume_email_verification_token(
            session,
            _plaintext(raw),
            clock=lambda: NOW,
        )

    safe_compare.assert_called_once_with(
        bytes(stored.token_digest),
        digest_email_verification_token(_plaintext(raw)),
    )
    assert consumed.user_id == user.id
    assert consumed.email_snapshot == user.email
    assert consumed.consumed_at == NOW
    assert _plaintext(raw) not in repr(consumed)
    assert stored.consumed_at == NOW
    mock.flush.assert_awaited_once_with()

    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    statements = [
        str(call.args[0].compile(dialect=dialect)) for call in mock.scalar.await_args_list
    ]
    assert "FOR UPDATE" not in statements[0]
    assert "FOR UPDATE" in statements[1]
    assert "FOR UPDATE" in statements[2]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state",
    [
        "expired-at-boundary",
        "replayed",
        "superseded",
        "deleted-token",
        "changed-email",
        "inactive-user",
        "deleted-user",
        "missing-user",
        "missing-under-lock",
        "digest-mismatch",
    ],
)
async def test_invalid_or_stale_tokens_fail_generically_without_consumption(state: str) -> None:
    raw = bytes(range(32))
    candidate = _stored_token(raw)
    locked = candidate
    user = _user()
    if state == "expired-at-boundary":
        locked.expires_at = NOW
    elif state == "replayed":
        locked.consumed_at = NOW - timedelta(seconds=1)
    elif state == "superseded":
        locked.superseded_at = NOW - timedelta(seconds=1)
    elif state == "deleted-token":
        locked.deleted_at = NOW - timedelta(seconds=1)
    elif state == "changed-email":
        user.email = "changed@example.com"
    elif state == "inactive-user":
        user.is_active = False
    elif state == "deleted-user":
        user.deleted_at = NOW
    elif state == "digest-mismatch":
        locked = _stored_token(bytes(reversed(raw)))
        locked.id = candidate.id

    mock, session = _session()
    if state == "missing-user":
        mock.scalar.side_effect = [candidate, None]
    elif state == "missing-under-lock":
        mock.scalar.side_effect = [candidate, user, None]
    else:
        mock.scalar.side_effect = [candidate, user, locked]

    with pytest.raises(EmailVerificationTokenError, match=f"^{INVALID_MESSAGE}$"):
        await consume_email_verification_token(
            session,
            _plaintext(raw),
            clock=lambda: NOW,
        )

    mock.flush.assert_not_awaited()
    assert locked.consumed_at != NOW


@pytest.mark.anyio
async def test_unknown_token_is_absent_from_errors_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    raw_token = _plaintext(bytes(reversed(range(32))))
    mock, session = _session()
    mock.scalar.return_value = None

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(EmailVerificationTokenError) as raised:
            await consume_email_verification_token(
                session,
                raw_token,
                clock=lambda: NOW,
            )

    assert str(raised.value) == INVALID_MESSAGE
    assert raw_token not in str(raised.value)
    assert raw_token not in caplog.text
    mock.flush.assert_not_awaited()
