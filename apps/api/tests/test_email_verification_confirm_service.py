"""EMAIL-003 atomic confirmation, ownership, boundary, and replay tests."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailVerificationToken, User, UserRole
from app.services.email_verification import (
    EMAIL_VERIFICATION_TOKEN_TTL,
    EmailVerificationTokenError,
    confirm_email_verification_token,
    digest_email_verification_token,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
RAW = bytes(range(32))
TOKEN = base64.urlsafe_b64encode(RAW).rstrip(b"=").decode("ascii")
INVALID_MESSAGE = "Verification token is invalid or expired."


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _user(
    *,
    role: UserRole = UserRole.USER,
    email: str = "student@example.com",
    active: bool = True,
    deleted_at: datetime | None = None,
    verified_at: datetime | None = None,
) -> User:
    return User(
        id=USER_ID,
        email=email,
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=active,
        email_verified=False,
        email_verified_at=verified_at,
        deleted_at=deleted_at,
    )


def _token(
    *,
    expires_at: datetime = NOW + EMAIL_VERIFICATION_TOKEN_TTL,
    consumed_at: datetime | None = None,
) -> EmailVerificationToken:
    created_at = expires_at - EMAIL_VERIFICATION_TOKEN_TTL
    return EmailVerificationToken(
        id=uuid4(),
        user_id=USER_ID,
        token_digest=digest_email_verification_token(TOKEN),
        email_snapshot="student@example.com",
        expires_at=expires_at,
        consumed_at=consumed_at,
        created_at=created_at,
        updated_at=created_at,
    )


def _session(*values: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=values)
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_confirm_consumes_once_and_stamps_the_authenticated_current_email() -> None:
    user = _user()
    stored = _token()
    mock, session = _session(stored, user, stored, user)

    result = await confirm_email_verification_token(
        session,
        TOKEN,
        USER_ID,
        clock=lambda: NOW + timedelta(minutes=1),
    )

    expected_time = NOW + timedelta(minutes=1)
    assert result.user_id == USER_ID
    assert result.email_verified_at == expected_time
    assert TOKEN not in repr(result)
    assert stored.consumed_at == expected_time
    assert user.email_verified_at == expected_time
    assert mock.flush.await_count == 2
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    statements = [
        str(call.args[0].compile(dialect=dialect)) for call in mock.scalar.await_args_list
    ]
    assert "FOR UPDATE" not in statements[0]
    assert all("FOR UPDATE" in statement for statement in statements[1:])


@pytest.mark.anyio
@pytest.mark.parametrize(
    "state",
    [
        "expired-at-boundary",
        "replayed",
        "changed-email",
        "inactive-user",
        "deleted-user",
        "wrong-session-user",
        "already-verified",
        "admin-owner",
    ],
)
async def test_invalid_expired_or_wrong_owner_confirmation_fails_generically(
    state: str,
) -> None:
    user = _user()
    stored = _token()
    expected_user_id = USER_ID
    if state == "expired-at-boundary":
        stored.expires_at = NOW
    elif state == "replayed":
        stored.consumed_at = NOW - timedelta(seconds=1)
    elif state == "changed-email":
        user.email = "changed@example.com"
    elif state == "inactive-user":
        user.is_active = False
    elif state == "deleted-user":
        user.deleted_at = NOW
    elif state == "wrong-session-user":
        expected_user_id = OTHER_USER_ID
    elif state == "already-verified":
        user.email_verified_at = NOW - timedelta(minutes=1)
    elif state == "admin-owner":
        user.role = UserRole.ADMIN

    values: list[object] = [stored, user, stored]
    if state in {"wrong-session-user", "already-verified", "admin-owner"}:
        if state != "wrong-session-user":
            values.append(user)
    mock, session = _session(*values)

    with pytest.raises(EmailVerificationTokenError, match=f"^{INVALID_MESSAGE}$") as raised:
        await confirm_email_verification_token(
            session,
            TOKEN,
            expected_user_id,
            clock=lambda: NOW,
        )

    assert TOKEN not in str(raised.value)
    if state != "already-verified":
        assert user.email_verified_at is None
    if state in {
        "expired-at-boundary",
        "replayed",
        "changed-email",
        "inactive-user",
        "deleted-user",
    }:
        mock.flush.assert_not_awaited()
