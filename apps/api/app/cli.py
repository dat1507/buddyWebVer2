"""Trusted operational commands for the VGU Buddy API."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import DatabaseConfigurationError
from app.core.database import dispose_database_engine, get_session_factory
from app.services.auth import AdminCreationError, create_admin

DATABASE_ERROR_MESSAGE = "Admin account could not be created because the database is unavailable."
PASSWORD_INPUT_ERROR_MESSAGE = "Admin password input was cancelled."


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="VGU Buddy operational commands.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = commands.add_parser(
        "create-admin",
        help="Create one active, verified Admin account.",
    )
    create_admin_parser.add_argument("--email", required=True, help="Admin email address.")
    password_source = create_admin_parser.add_mutually_exclusive_group()
    password_source.add_argument(
        "--password",
        help="Admin password; omit this option to use a hidden confirmation prompt.",
    )
    password_source.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the Admin password from one standard-input line.",
    )
    return parser


def _read_password(arguments: argparse.Namespace) -> str:
    try:
        supplied_password = arguments.password
        if isinstance(supplied_password, str):
            return supplied_password
        if arguments.password_stdin:
            return sys.stdin.readline().rstrip("\r\n")

        password = getpass("Admin password: ")
        confirmation = getpass("Confirm Admin password: ")
    except (EOFError, KeyboardInterrupt, OSError):
        raise AdminCreationError(PASSWORD_INPUT_ERROR_MESSAGE) from None
    if password != confirmation:
        raise AdminCreationError("Admin passwords do not match.")
    return password


async def _create_admin_command(email: str, password: str) -> str:
    try:
        async with get_session_factory()() as session:
            user = await create_admin(session, email, password)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return user.email
    finally:
        await dispose_database_engine()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse and execute one operational command with sanitized terminal failures."""
    arguments = _parser().parse_args(argv)
    if arguments.command != "create-admin":  # pragma: no cover - argparse owns this invariant.
        return 2

    try:
        password = _read_password(arguments)
        email = asyncio.run(_create_admin_command(arguments.email, password))
    except AdminCreationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except DatabaseConfigurationError:
        print(f"Error: {DATABASE_ERROR_MESSAGE}", file=sys.stderr)
        return 1
    except (OSError, SQLAlchemyError):
        print(f"Error: {DATABASE_ERROR_MESSAGE}", file=sys.stderr)
        return 1

    print(f"Admin account created: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
