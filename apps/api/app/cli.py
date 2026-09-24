"""Trusted operational commands for the VGU Buddy API."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from getpass import getpass
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    DatabaseConfigurationError,
    EmailConfigurationError,
    StorageConfigurationError,
    get_email_provider_settings,
    get_email_verification_delivery_settings,
    get_storage_settings,
)
from app.core.database import dispose_database_engine, get_session_factory
from app.services.auth import AdminCreationError, create_admin
from app.services.email_outbox import (
    DEFAULT_OUTBOX_BATCH_SIZE,
    MAX_OUTBOX_BATCH_SIZE,
    OutboxValidationError,
    OutboxWorkerReport,
    default_email_template_registry,
    process_transactional_outbox_batch,
)
from app.services.email_provider import ResendEmailProvider
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
EMAIL_WORKER_ERROR_MESSAGE = "Transactional email worker could not be started or completed."
UNSAFE_PASSWORD_ARGUMENT_MESSAGE = (
    "Command-line passwords are not supported; use the hidden prompt or --password-stdin."
)


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
    create_admin_parser.add_argument(
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
    email_worker_parser = commands.add_parser(
        "email-worker",
        help="Continuously process the transactional email outbox.",
    )
    email_worker_parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one bounded batch and exit.",
    )
    email_worker_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_OUTBOX_BATCH_SIZE,
        help=f"Rows per batch (default: {DEFAULT_OUTBOX_BATCH_SIZE}).",
    )
    email_worker_parser.add_argument(
        "--poll-seconds",
        type=float,
        default=5.0,
        help="Idle polling interval for continuous mode (default: 5).",
    )
    return parser


def _read_password(arguments: argparse.Namespace) -> str:
    try:
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


async def _email_worker_command(
    *,
    once: bool,
    batch_size: int,
    poll_seconds: float,
) -> OutboxWorkerReport:
    if not 1 <= batch_size <= MAX_OUTBOX_BATCH_SIZE or poll_seconds < 0.1:
        raise OutboxValidationError("Email worker bounds are invalid.")
    provider = ResendEmailProvider(get_email_provider_settings())
    templates = default_email_template_registry(get_email_verification_delivery_settings())
    worker_id = f"email-worker-{uuid4()}"
    try:
        while True:
            report = await process_transactional_outbox_batch(
                get_session_factory(),
                worker_id=worker_id,
                provider=provider,
                templates=templates,
                batch_size=batch_size,
            )
            if once:
                return report
            if report.claimed == 0:
                await asyncio.sleep(poll_seconds)
    finally:
        await dispose_database_engine()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse and execute one operational command with sanitized terminal failures."""
    raw_arguments = list(argv) if argv is not None else sys.argv[1:]
    if any(
        argument == "--password" or argument.startswith("--password=")
        for argument in raw_arguments
    ):
        print(f"Error: {UNSAFE_PASSWORD_ARGUMENT_MESSAGE}", file=sys.stderr)
        return 2

    arguments = _parser().parse_args(raw_arguments)
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
            storage_report = asyncio.run(
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
            f"Storage reconciliation ({mode}): scanned={storage_report.scanned}, "
            f"protected={storage_report.protected}, candidates={storage_report.candidates}, "
            f"deleted={storage_report.deleted}, failed={storage_report.failed}, "
            f"too_new={storage_report.too_new}, unmanaged={storage_report.unmanaged}"
        )
        return 1 if storage_report.failed else 0

    if arguments.command == "email-worker":
        try:
            email_report = asyncio.run(
                _email_worker_command(
                    once=arguments.once,
                    batch_size=arguments.batch_size,
                    poll_seconds=arguments.poll_seconds,
                )
            )
        except (
            DatabaseConfigurationError,
            EmailConfigurationError,
            OutboxValidationError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {EMAIL_WORKER_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Transactional email outbox: "
            f"claimed={email_report.claimed}, sent={email_report.sent}, "
            f"retry_scheduled={email_report.retry_scheduled}, "
            f"terminal_failed={email_report.terminal_failed}, skipped={email_report.skipped}"
        )
        return 0 if email_report.terminal_failed == 0 else 1

    return 2  # pragma: no cover - argparse owns this invariant.


if __name__ == "__main__":
    raise SystemExit(main())
