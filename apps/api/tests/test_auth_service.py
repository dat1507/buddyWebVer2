"""Security and behavior tests for registration, login, and role services."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.auth as auth_service
from app.models import User, UserRole
from app.services import (
    MAX_EMAIL_LENGTH,
    AccountRegistrationError,
    AuthenticationError,
    EmailValidationError,
    RoleVerificationError,
    authenticate_user,
    canonicalize_email,
    hash_password,
    register_user,
    verify_password,
    verify_user_role,
)

TEST_PASSWORD = "Correct horse battery staple 🔒"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)
LOGIN_TIME = datetime(2026, 9, 16, 14, 30, tzinfo=UTC)


class _PostgresViolation(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("test database constraint violation")
        self.sqlstate = sqlstate


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.flush = AsyncMock()
    mock.rollback = AsyncMock()
    mock.commit = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> User:
    return User(
        email="student@example.com",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        is_active=is_active,
        email_verified=False,
        deleted_at=deleted_at,
    )


@pytest.mark.parametrize(
    ("supplied", "expected"),
    [
        ("  Student@Example.COM  ", "student@example.com"),
        ("First.Last+buddy@Students.VGU.EDU.VN", "first.last+buddy@students.vgu.edu.vn"),
        ("a@b.co", "a@b.co"),
    ],
)
def test_email_is_trimmed_validated_and_canonicalized(supplied: str, expected: str) -> None:
    assert canonicalize_email(supplied) == expected


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "missing-at.example.com",
        "two@@example.com",
        "@example.com",
        "student@",
        "student@localhost",
        ".student@example.com",
        "student.@example.com",
        "student..buddy@example.com",
        "student name@example.com",
        "student@example..com",
        "student@-example.com",
        "student@example-.com",
        "stüdent@example.com",
        f"{'a' * 65}@example.com",
        f"a@{'b' * MAX_EMAIL_LENGTH}.com",
    ],
)
def test_invalid_email_contract_fails_with_no_reflected_value(email: str) -> None:
    with pytest.raises(EmailValidationError, match="^Email address is invalid\\.$") as error:
        canonicalize_email(email)

    if email:
        assert email not in str(error.value)


@pytest.mark.anyio
async def test_registration_stages_only_a_canonical_least_privilege_user() -> None:
    mock, session = _session()

    user = await register_user(session, "  Student@Example.COM ", TEST_PASSWORD)

    mock.add.assert_called_once_with(user)
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()
    assert user.email == "student@example.com"
    assert user.role is UserRole.USER
    assert user.is_active is True
    assert user.email_verified is False
    assert user.email_verified_at is None
    assert user.last_login is None
    assert user.deleted_at is None
    assert user.password_hash != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, user.password_hash) is True
    assert "role" not in inspect.signature(register_user).parameters


@pytest.mark.anyio
async def test_registration_maps_only_unique_violation_to_a_generic_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    mock.flush.side_effect = IntegrityError(
        "insert into users",
        {},
        _PostgresViolation("23505"),
    )

    with pytest.raises(AccountRegistrationError, match="^Account registration failed\\.$") as error:
        await register_user(session, "student@example.com", TEST_PASSWORD)

    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    assert "student@example.com" not in str(error.value)


@pytest.mark.anyio
async def test_registration_rolls_back_and_preserves_non_unique_integrity_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    integrity_error = IntegrityError(
        "insert into users",
        {},
        _PostgresViolation("23514"),
    )
    mock.flush.side_effect = integrity_error

    with pytest.raises(IntegrityError) as raised:
        await register_user(session, "student@example.com", TEST_PASSWORD)

    assert raised.value is integrity_error
    mock.rollback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_authentication_queries_canonical_email_and_stages_last_login() -> None:
    mock, session = _session()
    user = _user(role=UserRole.ADMIN)
    mock.scalar.return_value = user

    authenticated = await authenticate_user(
        session,
        "  Student@Example.COM ",
        TEST_PASSWORD,
        now=LOGIN_TIME,
    )

    statement = mock.scalar.await_args.args[0]
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    compiled = str(statement.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
    assert authenticated is user
    assert "student@example.com" in compiled
    assert TEST_PASSWORD not in compiled
    assert authenticated.role is UserRole.ADMIN
    assert authenticated.last_login == LOGIN_TIME
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("user", "password", "email"),
    [
        (None, TEST_PASSWORD, "unknown@example.com"),
        (_user(), "wrong password", "student@example.com"),
        (_user(is_active=False), TEST_PASSWORD, "student@example.com"),
        (
            _user(deleted_at=datetime(2026, 9, 1, tzinfo=UTC)),
            TEST_PASSWORD,
            "student@example.com",
        ),
        (None, TEST_PASSWORD, "not-an-email"),
    ],
)
async def test_all_credential_and_account_state_failures_are_generic(
    user: User | None,
    password: str,
    email: str,
) -> None:
    mock, session = _session()
    mock.scalar.return_value = user

    with pytest.raises(AuthenticationError, match="^Invalid email or password\\.$") as error:
        await authenticate_user(session, email, password, now=LOGIN_TIME)

    assert email not in str(error.value)
    if user is not None:
        assert user.last_login is None
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_unknown_and_malformed_email_paths_still_verify_a_dummy_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    mock.scalar.return_value = None
    verified_hashes: list[str] = []

    def capture_verification(_password: str, password_hash: str) -> bool:
        verified_hashes.append(password_hash)
        return False

    monkeypatch.setattr(auth_service, "verify_password", capture_verification)

    for email in ("unknown@example.com", "not-an-email"):
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await authenticate_user(session, email, TEST_PASSWORD)

    assert verified_hashes == [
        auth_service._DUMMY_PASSWORD_HASH,
        auth_service._DUMMY_PASSWORD_HASH,
    ]


@pytest.mark.anyio
async def test_authentication_rejects_naive_last_login_timestamp() -> None:
    mock, session = _session()
    mock.scalar.return_value = _user()

    with pytest.raises(ValueError, match="timezone-aware"):
        await authenticate_user(
            session,
            "student@example.com",
            TEST_PASSWORD,
            now=datetime(2026, 9, 16, 14, 30),
        )


@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
def test_role_verification_uses_the_persisted_role(role: UserRole) -> None:
    user = _user(role=role)

    assert verify_user_role(user, role) is user

    other_role = UserRole.ADMIN if role is UserRole.USER else UserRole.USER
    with pytest.raises(RoleVerificationError, match="^Insufficient permissions\\.$"):
        verify_user_role(user, other_role)


@pytest.mark.parametrize(
    "user",
    [
        _user(is_active=False),
        _user(deleted_at=datetime(2026, 9, 1, tzinfo=UTC)),
    ],
)
def test_role_verification_rejects_inactive_or_deleted_users(user: User) -> None:
    with pytest.raises(RoleVerificationError, match="^Insufficient permissions\\.$"):
        verify_user_role(user, user.role)


def test_role_verification_rejects_a_string_that_only_looks_like_an_enum() -> None:
    user = _user(role=UserRole.USER)
    user.role = cast(UserRole, "ADMIN")

    with pytest.raises(RoleVerificationError, match="^Insufficient permissions\\.$"):
        verify_user_role(user, UserRole.ADMIN)
