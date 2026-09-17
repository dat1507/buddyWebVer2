"""Unit and security tests for persistent refresh-session rotation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthTokenSettings
from app.models import RefreshSession, User, UserRole
from app.services.refresh_sessions import (
    RefreshSessionError,
    RefreshSessionRevokedError,
    create_refresh_session,
    rotate_refresh_session,
)
from app.services.tokens import create_token_pair, verify_access_token, verify_refresh_token

TEST_USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEST_SESSION_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"
TEST_SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(TEST_SIGNING_KEY), secure_cookies=False)


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.flush = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        id=TEST_USER_ID,
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=is_active,
        email_verified=True,
        deleted_at=deleted_at,
    )


def _persisted_session(
    refresh_token_id: UUID,
    expires_at: datetime,
    *,
    user_id: UUID = TEST_USER_ID,
    revoked_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> RefreshSession:
    return RefreshSession(
        id=TEST_SESSION_ID,
        user_id=user_id,
        refresh_token_id=refresh_token_id,
        expires_at=expires_at,
        revoked_at=revoked_at,
        deleted_at=deleted_at,
    )


@pytest.mark.anyio
async def test_create_refresh_session_stages_current_family_state() -> None:
    mock, session = _session()
    user = _user()
    pair = create_token_pair(
        user.id,
        user.role,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=_now(),
    )

    refresh_session = await create_refresh_session(session, user, pair)

    mock.add.assert_called_once_with(refresh_session)
    mock.flush.assert_awaited_once_with()
    assert refresh_session.id == pair.session_id
    assert refresh_session.user_id == user.id
    assert refresh_session.refresh_token_id == pair.refresh_token_id
    assert refresh_session.expires_at == pair.refresh_expires_at
    assert refresh_session.revoked_at is None


@pytest.mark.anyio
async def test_rotation_locks_family_consumes_jti_and_uses_current_database_role() -> None:
    now = _now()
    original = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now - timedelta(minutes=1),
    )
    claims = verify_refresh_token(original.refresh_token, _settings())
    stored = _persisted_session(original.refresh_token_id, original.refresh_expires_at)
    user = _user(role=UserRole.ADMIN)
    mock, session = _session()
    mock.scalar.side_effect = [stored, user]

    result = await rotate_refresh_session(
        session,
        original.refresh_token,
        claims,
        _settings(),
        now=now,
    )

    family_statement = mock.scalar.await_args_list[0].args[0]
    user_statement = mock.scalar.await_args_list[1].args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    assert "FOR UPDATE" in str(family_statement.compile(dialect=dialect))
    assert "FOR UPDATE" in str(user_statement.compile(dialect=dialect))
    assert result.user is user
    assert result.token_pair.session_id == TEST_SESSION_ID
    assert stored.refresh_token_id == result.token_pair.refresh_token_id
    assert stored.refresh_token_id != original.refresh_token_id
    assert stored.expires_at == result.token_pair.refresh_expires_at
    assert stored.revoked_at is None
    assert verify_access_token(result.token_pair.access_token, _settings()).role is UserRole.ADMIN
    mock.flush.assert_awaited_once_with()


@pytest.mark.anyio
async def test_reused_older_jti_stages_family_revocation_before_rejection() -> None:
    now = _now()
    original = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now - timedelta(minutes=1),
    )
    claims = verify_refresh_token(original.refresh_token, _settings())
    stored = _persisted_session(uuid4(), original.refresh_expires_at)
    mock, session = _session()
    mock.scalar.return_value = stored

    with pytest.raises(
        RefreshSessionRevokedError,
        match="^Session is invalid or expired\\.$",
    ):
        await rotate_refresh_session(
            session,
            original.refresh_token,
            claims,
            _settings(),
            now=now,
        )

    assert stored.revoked_at == now
    mock.flush.assert_awaited_once_with()
    assert mock.scalar.await_count == 1


@pytest.mark.anyio
@pytest.mark.parametrize("state", ["missing", "revoked", "deleted"])
async def test_missing_or_already_invalid_family_is_rejected_without_mutation(state: str) -> None:
    now = _now()
    pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now - timedelta(minutes=1),
    )
    claims = verify_refresh_token(pair.refresh_token, _settings())
    stored = _persisted_session(
        pair.refresh_token_id,
        pair.refresh_expires_at,
        revoked_at=now - timedelta(seconds=1) if state == "revoked" else None,
        deleted_at=now - timedelta(seconds=1) if state == "deleted" else None,
    )
    mock, session = _session()
    mock.scalar.return_value = None if state == "missing" else stored

    with pytest.raises(RefreshSessionError, match="^Session is invalid or expired\\.$"):
        await rotate_refresh_session(
            session,
            pair.refresh_token,
            claims,
            _settings(),
            now=now,
        )

    mock.flush.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("condition", ["expired", "wrong-user", "inactive", "deleted-user"])
async def test_compromised_or_ineligible_family_is_revoked(condition: str) -> None:
    now = _now()
    pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now - timedelta(minutes=1),
    )
    claims = verify_refresh_token(pair.refresh_token, _settings())
    stored = _persisted_session(
        pair.refresh_token_id,
        now - timedelta(seconds=1) if condition == "expired" else pair.refresh_expires_at,
        user_id=uuid4() if condition == "wrong-user" else TEST_USER_ID,
    )
    user = _user(
        is_active=condition != "inactive",
        deleted_at=now if condition == "deleted-user" else None,
    )
    mock, session = _session()
    mock.scalar.side_effect = [stored, user]

    with pytest.raises(RefreshSessionRevokedError, match="invalid or expired"):
        await rotate_refresh_session(
            session,
            pair.refresh_token,
            claims,
            _settings(),
            now=now,
        )

    assert stored.revoked_at == now
    mock.flush.assert_awaited_once_with()
    if condition in {"expired", "wrong-user"}:
        assert mock.scalar.await_count == 1
    else:
        assert mock.scalar.await_count == 2


@pytest.mark.anyio
async def test_token_reverification_failure_is_generic_and_does_not_advance_jti() -> None:
    now = _now()
    pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
        now=now - timedelta(minutes=1),
    )
    claims = verify_refresh_token(pair.refresh_token, _settings())
    stored = _persisted_session(pair.refresh_token_id, pair.refresh_expires_at)
    mock, session = _session()
    mock.scalar.side_effect = [stored, _user()]

    with pytest.raises(RefreshSessionError, match="invalid or expired"):
        await rotate_refresh_session(
            session,
            f"{pair.refresh_token}tampered",
            claims,
            _settings(),
            now=now,
        )

    assert stored.refresh_token_id == pair.refresh_token_id
    assert stored.revoked_at is None
    mock.flush.assert_not_awaited()


@pytest.mark.anyio
async def test_rotation_rejects_naive_timestamp() -> None:
    pair = create_token_pair(
        TEST_USER_ID,
        UserRole.USER,
        _settings(),
        session_id=TEST_SESSION_ID,
    )
    claims = verify_refresh_token(pair.refresh_token, _settings())
    _, session = _session()

    with pytest.raises(ValueError, match="timezone-aware"):
        await rotate_refresh_session(
            session,
            pair.refresh_token,
            claims,
            _settings(),
            now=datetime(2026, 9, 17, 12, 0),
        )
