"""EMAIL-004 service authorization, relock, uniqueness, and orchestration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.email_changes as email_changes
from app.core.config import EmailVerificationDeliverySettings
from app.models import User, UserRole
from app.services.email_changes import (
    EmailChangeAuthenticationError,
    EmailChangeConflictError,
    EmailChangePasswordError,
    change_current_user_email,
)
from app.services.email_verification_requests import (
    EmailVerificationRequestError,
    EmailVerificationRequestResult,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


class _PostgresUniqueViolation(Exception):
    sqlstate = "23505"


class _PostgresOtherFailure(Exception):
    sqlstate = "23514"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> EmailVerificationDeliverySettings:
    return EmailVerificationDeliverySettings(
        public_app_base_url="https://buddy.example",
        sealing_key=SecretBytes(bytes(range(32))),
    )


def _user(
    *,
    verified: bool = True,
    role: UserRole = UserRole.USER,
    active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash=PASSWORD_HASH,
        role=role,
        is_active=active,
        email_verified=False,
        email_verified_at=NOW if verified else None,
        deleted_at=deleted_at,
    )


def _session(user: User | None) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=user)
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
@pytest.mark.parametrize("verified", [False, True])
async def test_change_replaces_canonical_email_relocks_and_requests_current_address(
    verified: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user(verified=verified)
    mock, session = _session(user)
    verify = MagicMock(return_value=True)
    request = AsyncMock(return_value=EmailVerificationRequestResult(created=True))
    monkeypatch.setattr(email_changes, "verify_password", verify)
    monkeypatch.setattr(email_changes, "request_email_verification", request)

    result = await change_current_user_email(
        session,
        USER_ID,
        "  New.Student@Example.COM  ",
        "current password",
        _settings(),
    )

    assert result.user is user
    assert user.id == USER_ID
    assert user.email == "new.student@example.com"
    assert user.email_verified_at is None
    assert PASSWORD_HASH not in repr(result)
    verify.assert_called_once_with("current password", PASSWORD_HASH)
    request.assert_awaited_once_with(session, USER_ID, _settings())
    mock.flush.assert_awaited_once_with()
    statement = mock.scalar.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    assert "FOR UPDATE" in str(statement.compile(dialect=dialect))
    assert not hasattr(mock, "commit") or mock.commit.await_count == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("user", "password_matches"),
    [
        (None, True),
        (_user(role=UserRole.ADMIN), True),
        (_user(active=False), True),
        (_user(deleted_at=NOW), True),
        (_user(), False),
    ],
)
async def test_change_rejects_invalid_account_or_password_without_mutation(
    user: User | None,
    password_matches: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(user)
    monkeypatch.setattr(email_changes, "verify_password", lambda *_args: password_matches)
    request = AsyncMock()
    monkeypatch.setattr(email_changes, "request_email_verification", request)

    expected_error = (
        EmailChangePasswordError
        if user is not None and not password_matches
        else EmailChangeAuthenticationError
    )
    with pytest.raises(expected_error):
        await change_current_user_email(
            session,
            USER_ID,
            "new@example.com",
            "current password",
            _settings(),
        )

    if user is not None:
        assert user.email == "student@example.com"
    mock.flush.assert_not_awaited()
    request.assert_not_awaited()


@pytest.mark.anyio
async def test_change_rejects_same_or_invalid_address_generically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    mock, session = _session(user)
    monkeypatch.setattr(email_changes, "verify_password", lambda *_args: True)
    request = AsyncMock()
    monkeypatch.setattr(email_changes, "request_email_verification", request)

    for new_email in ("STUDENT@EXAMPLE.COM", "invalid address"):
        with pytest.raises(
            EmailChangeConflictError,
            match="^Email address could not be changed\\.$",
        ):
            await change_current_user_email(
                session,
                USER_ID,
                new_email,
                "current password",
                _settings(),
            )

    assert user.email == "student@example.com"
    mock.flush.assert_not_awaited()
    request.assert_not_awaited()


@pytest.mark.anyio
async def test_unique_race_is_generic_and_other_database_failures_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(email_changes, "verify_password", lambda *_args: True)
    request = AsyncMock()
    monkeypatch.setattr(email_changes, "request_email_verification", request)

    for original, expected in (
        (_PostgresUniqueViolation(), EmailChangeConflictError),
        (_PostgresOtherFailure(), IntegrityError),
    ):
        mock, session = _session(_user())
        mock.flush.side_effect = IntegrityError("update", {}, original)
        with pytest.raises(expected):
            await change_current_user_email(
                session,
                USER_ID,
                "shared@example.com",
                "current password",
                _settings(),
            )

    request.assert_not_awaited()


@pytest.mark.anyio
async def test_verification_request_failure_is_sanitized_for_the_email_change_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session(_user())
    monkeypatch.setattr(email_changes, "verify_password", lambda *_args: True)
    monkeypatch.setattr(
        email_changes,
        "request_email_verification",
        AsyncMock(side_effect=EmailVerificationRequestError("private account state")),
    )

    with pytest.raises(
        EmailChangeAuthenticationError,
        match="^Email change could not be authorized\\.$",
    ) as raised:
        await change_current_user_email(
            session,
            USER_ID,
            "new@example.com",
            "current password",
            _settings(),
        )

    assert "private account state" not in str(raised.value)
