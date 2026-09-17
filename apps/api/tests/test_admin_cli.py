"""Security and transaction tests for the trusted Admin seed CLI."""

from __future__ import annotations

import inspect
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import StringIO
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.cli as cli
import app.services.auth as auth_service
from app.core.config import DatabaseConfigurationError
from app.models import User, UserRole
from app.services import (
    MIN_ADMIN_PASSWORD_CHARACTERS,
    AdminCreationError,
    create_admin,
    verify_password,
)

TEST_PASSWORD = "Correct horse battery staple 🔒"
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


class _PostgresViolation(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("test database constraint violation")
        self.sqlstate = sqlstate


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.flush = AsyncMock()
    mock.rollback = AsyncMock()
    mock.commit = AsyncMock()
    return mock, cast(AsyncSession, mock)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_create_admin_stages_only_a_canonical_verified_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)

    user = await create_admin(session, "  Admin@VGU.EDU.VN ", TEST_PASSWORD)

    mock.add.assert_called_once_with(user)
    mock.flush.assert_awaited_once_with()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()
    assert user.email == "admin@vgu.edu.vn"
    assert user.role is UserRole.ADMIN
    assert user.is_active is True
    assert user.email_verified is True
    assert user.last_login is None
    assert user.deleted_at is None
    assert user.password_hash == TEST_PASSWORD_HASH
    assert "role" not in inspect.signature(create_admin).parameters


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("not-an-email", TEST_PASSWORD, "Email address is invalid."),
        (
            "admin@example.com",
            "a" * (MIN_ADMIN_PASSWORD_CHARACTERS - 1),
            f"Admin password must contain at least {MIN_ADMIN_PASSWORD_CHARACTERS} characters.",
        ),
        ("admin@example.com", "é" * 37, "Password must not exceed 72 UTF-8 bytes."),
    ],
)
async def test_create_admin_rejects_invalid_credentials_before_database_write(
    email: str,
    password: str,
    message: str,
) -> None:
    mock, session = _session()

    with pytest.raises(AdminCreationError, match=f"^{message.replace('.', r'\.')}$"):
        await create_admin(session, email, password)

    mock.add.assert_not_called()
    mock.flush.assert_not_awaited()
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_create_admin_hashes_the_exact_password() -> None:
    _, session = _session()
    exact_password = f"  {TEST_PASSWORD}  "

    user = await create_admin(session, "admin@example.com", exact_password)

    assert user.password_hash != exact_password
    assert verify_password(exact_password, user.password_hash) is True
    assert verify_password(exact_password.strip(), user.password_hash) is False


@pytest.mark.anyio
async def test_create_admin_maps_duplicate_email_to_generic_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    monkeypatch.setattr(auth_service, "hash_password", lambda _password: TEST_PASSWORD_HASH)
    mock.flush.side_effect = IntegrityError(
        "insert into users",
        {},
        _PostgresViolation("23505"),
    )

    with pytest.raises(AdminCreationError, match="^Admin account could not be created\\.$"):
        await create_admin(session, "admin@example.com", TEST_PASSWORD)

    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_create_admin_rolls_back_and_preserves_non_unique_integrity_error(
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
        await create_admin(session, "admin@example.com", TEST_PASSWORD)

    assert raised.value is integrity_error
    mock.rollback.assert_awaited_once_with()


def test_cli_accepts_explicit_password_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def command(email: str, password: str) -> str:
        assert email == "Admin@Example.com"
        assert password == TEST_PASSWORD
        return "admin@example.com"

    monkeypatch.setattr(cli, "_create_admin_command", command)

    exit_code = cli.main(
        ["create-admin", "--email", "Admin@Example.com", "--password", TEST_PASSWORD]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Admin account created: admin@example.com\n"
    assert captured.err == ""
    assert TEST_PASSWORD not in captured.out


def test_cli_uses_hidden_confirmation_prompt_when_password_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompts: list[str] = []
    supplied = iter((TEST_PASSWORD, TEST_PASSWORD))

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return next(supplied)

    async def command(_email: str, password: str) -> str:
        assert password == TEST_PASSWORD
        return "admin@example.com"

    monkeypatch.setattr(cli, "getpass", fake_getpass)
    monkeypatch.setattr(cli, "_create_admin_command", command)

    exit_code = cli.main(["create-admin", "--email", "admin@example.com"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert prompts == ["Admin password: ", "Confirm Admin password: "]
    assert TEST_PASSWORD not in captured.out
    assert TEST_PASSWORD not in captured.err


def test_cli_rejects_prompt_mismatch_before_database_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    supplied = iter((TEST_PASSWORD, "different secure password"))
    command = AsyncMock()
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(supplied))
    monkeypatch.setattr(cli, "_create_admin_command", command)

    exit_code = cli.main(["create-admin", "--email", "admin@example.com"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: Admin passwords do not match.\n"
    command.assert_not_awaited()


def test_cli_reads_exactly_one_password_line_from_stdin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def command(_email: str, password: str) -> str:
        assert password == TEST_PASSWORD
        return "admin@example.com"

    monkeypatch.setattr(sys, "stdin", StringIO(f"{TEST_PASSWORD}\nignored second line\n"))
    monkeypatch.setattr(cli, "_create_admin_command", command)

    exit_code = cli.main(["create-admin", "--email", "admin@example.com", "--password-stdin"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Admin account created: admin@example.com\n"
    assert TEST_PASSWORD not in captured.out
    assert TEST_PASSWORD not in captured.err


def test_cli_sanitizes_cancelled_password_prompt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = AsyncMock()

    def cancelled_prompt(_prompt: str) -> str:
        raise EOFError("terminal details")

    monkeypatch.setattr(cli, "getpass", cancelled_prompt)
    monkeypatch.setattr(cli, "_create_admin_command", command)

    exit_code = cli.main(["create-admin", "--email", "admin@example.com"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: {cli.PASSWORD_INPUT_ERROR_MESSAGE}\n"
    assert "terminal details" not in captured.err
    command.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [
        DatabaseConfigurationError("DATABASE_URL contains a secret"),
        SQLAlchemyError("database password leaked"),
        OSError("socket path leaked"),
    ],
)
def test_cli_sanitizes_database_failures(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def failing_command(_email: str, _password: str) -> str:
        raise error

    monkeypatch.setattr(cli, "_create_admin_command", failing_command)

    exit_code = cli.main(
        ["create-admin", "--email", "admin@example.com", "--password", TEST_PASSWORD]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: {cli.DATABASE_ERROR_MESSAGE}\n"
    assert str(error) not in captured.err


@pytest.mark.anyio
async def test_command_commits_once_and_disposes_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    user = User(email="admin@example.com", role=UserRole.ADMIN)

    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        yield session

    factory = MagicMock(return_value=session_context())
    dispose = AsyncMock()
    create = AsyncMock(return_value=user)
    monkeypatch.setattr(
        cli,
        "get_session_factory",
        lambda: cast(async_sessionmaker[AsyncSession], factory),
    )
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "create_admin", create)

    email = await cli._create_admin_command("admin@example.com", TEST_PASSWORD)

    assert email == "admin@example.com"
    create.assert_awaited_once_with(session, "admin@example.com", TEST_PASSWORD)
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()
    dispose.assert_awaited_once_with()


@pytest.mark.anyio
async def test_command_rolls_back_commit_failure_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    mock.commit.side_effect = SQLAlchemyError("commit failed")
    user = User(email="admin@example.com", role=UserRole.ADMIN)

    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        yield session

    factory = MagicMock(return_value=session_context())
    dispose = AsyncMock()
    monkeypatch.setattr(
        cli,
        "get_session_factory",
        lambda: cast(async_sessionmaker[AsyncSession], factory),
    )
    monkeypatch.setattr(cli, "dispose_database_engine", dispose)
    monkeypatch.setattr(cli, "create_admin", AsyncMock(return_value=user))

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        await cli._create_admin_command("admin@example.com", TEST_PASSWORD)

    mock.rollback.assert_awaited_once_with()
    dispose.assert_awaited_once_with()
