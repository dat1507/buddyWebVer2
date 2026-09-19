"""Trusted operational commands for the VGU Buddy API."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    DatabaseConfigurationError,
    StorageConfigurationError,
    get_storage_settings,
)
from app.core.database import dispose_database_engine, get_session_factory
from app.services.auth import AdminCreationError, create_admin
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ReconciliationReport,
    StorageOperationError,
    StorageReconciliationError,
    SupabaseStorageTransport,
    discover_storage_references,
    reconcile_orphaned_images,
)

DATABASE_ERROR_MESSAGE = "Admin account could not be created because the database is unavailable."
PASSWORD_INPUT_ERROR_MESSAGE = "Admin password input was cancelled."
STORAGE_ERROR_MESSAGE = "Storage reconciliation could not be completed."
STORAGE_CONFIGURATION_ERROR_MESSAGE = "Storage bucket configuration could not be completed."


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
    commands.add_parser(
        "configure-storage",
        help="Create or update the managed Supabase image buckets.",
    )
    reconcile_parser = commands.add_parser(
        "reconcile-storage",
        help="Find old unreferenced managed images; dry-run unless --apply is supplied.",
    )
    reconcile_parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete eligible orphan objects after database reference discovery.",
    )
    reconcile_parser.add_argument(
        "--minimum-age-hours",
        type=int,
        default=24,
        help="Protect objects newer than this many hours (default: 24).",
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


async def _reconcile_storage_command(
    *,
    apply: bool,
    minimum_age_hours: int,
) -> ReconciliationReport:
    if minimum_age_hours < 1:
        raise StorageReconciliationError("Minimum orphan age must be at least one hour.")

    settings = get_storage_settings()
    storage = ImageStorageService(SupabaseStorageTransport(settings))
    try:
        async with get_session_factory()() as session:
            references, reference_source_count = await discover_storage_references(session)
            if apply and reference_source_count == 0:
                raise StorageReconciliationError(
                    "No bucket/object_key reference tables exist; refusing destructive cleanup."
                )
            return await reconcile_orphaned_images(
                storage,
                references,
                older_than=datetime.now(UTC) - timedelta(hours=minimum_age_hours),
                apply=apply,
            )
    finally:
        await dispose_database_engine()


async def _configure_storage_command() -> int:
    transport = SupabaseStorageTransport(get_storage_settings())
    for bucket in ImageBucket:
        await transport.configure_bucket(bucket)
    return len(ImageBucket)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse and execute one operational command with sanitized terminal failures."""
    arguments = _parser().parse_args(argv)
    if arguments.command == "create-admin":
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

    if arguments.command == "configure-storage":
        try:
            configured = asyncio.run(_configure_storage_command())
        except (StorageConfigurationError, StorageOperationError, OSError):
            print(f"Error: {STORAGE_CONFIGURATION_ERROR_MESSAGE}", file=sys.stderr)
            return 1

        print(f"Storage buckets configured: {configured}")
        return 0

    if arguments.command == "reconcile-storage":
        try:
            report = asyncio.run(
                _reconcile_storage_command(
                    apply=arguments.apply,
                    minimum_age_hours=arguments.minimum_age_hours,
                )
            )
        except (
            DatabaseConfigurationError,
            StorageConfigurationError,
            StorageOperationError,
            StorageReconciliationError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {STORAGE_ERROR_MESSAGE}", file=sys.stderr)
            return 1

        mode = "apply" if arguments.apply else "dry-run"
        print(
            f"Storage reconciliation ({mode}): scanned={report.scanned}, "
            f"protected={report.protected}, candidates={report.candidates}, "
            f"deleted={report.deleted}, failed={report.failed}, "
            f"too_new={report.too_new}, unmanaged={report.unmanaged}"
        )
        return 1 if report.failed else 0

    return 2  # pragma: no cover - argparse owns this invariant.


if __name__ == "__main__":
    raise SystemExit(main())
