"""Trusted operational commands for the VGU Buddy API."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from getpass import getpass
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import (
    DatabaseConfigurationError,
    EmailConfigurationError,
    StorageConfigurationError,
    get_backup_database_settings,
    get_email_provider_settings,
    get_email_verification_delivery_settings,
    get_migration_database_settings,
    get_storage_settings,
)
from app.core.database import (
    dispose_database_engine,
    get_session_factory,
    migration_database_url,
)
from app.core.observability import (
    emit_chat_cleanup_event,
    emit_invitation_expiry_event,
    emit_semester_backup_expiry_event,
)
from app.services.auth import AdminCreationError, create_admin
from app.services.chat_cleanup import (
    DEFAULT_CHAT_CLEANUP_BATCH_SIZE,
    ChatCleanupReport,
    ChatCleanupValidationError,
    process_chat_cleanup_batch,
)
from app.services.database_backup_storage import (
    DatabaseBackupStorageError,
    SupabaseDatabaseBackupStore,
)
from app.services.email_outbox import (
    DEFAULT_OUTBOX_BATCH_SIZE,
    MAX_OUTBOX_BATCH_SIZE,
    OutboxValidationError,
    OutboxWorkerReport,
    default_email_delivery_resolver_registry,
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
from app.services.invitation_expiry import (
    DEFAULT_INVITATION_EXPIRY_BATCH_SIZE,
    InvitationExpiryReport,
    InvitationExpiryValidationError,
    process_invitation_expiry_batch,
)
from app.services.semester_avatar_backup import (
    AvatarBackupAdapter,
    AvatarBackupError,
    AvatarBackupReport,
    create_semester_avatar_backup,
)
from app.services.semester_backup_verification import (
    DEFAULT_BACKUP_EXPIRY_BATCH_SIZE,
    SemesterBackupExpiryError,
    SemesterBackupExpiryReport,
    SemesterBackupExpiryValidationError,
    SemesterBackupVerificationError,
    SemesterBackupVerificationReport,
    process_expired_semester_backup_batch,
    verify_semester_backup,
)
from app.services.semester_database_backup import (
    DatabaseBackupError,
    DatabaseBackupReport,
    PostgresBinaryCopyBackupAdapter,
    create_semester_database_backup,
)

DATABASE_ERROR_MESSAGE = "Admin account could not be created because the database is unavailable."
PASSWORD_INPUT_ERROR_MESSAGE = "Admin password input was cancelled."
STORAGE_ERROR_MESSAGE = "Storage reconciliation could not be completed."
STORAGE_CONFIGURATION_ERROR_MESSAGE = "Storage bucket configuration could not be completed."
EMAIL_WORKER_ERROR_MESSAGE = "Transactional email worker could not be started or completed."
INVITATION_EXPIRY_ERROR_MESSAGE = "Invitation expiry batch could not be completed."
CHAT_CLEANUP_ERROR_MESSAGE = "Expired Buddy message cleanup could not be completed."
LOCAL_RUNTIME_ROLE_ERROR_MESSAGE = "Local runtime database role could not be configured."
DATABASE_BACKUP_ERROR_MESSAGE = "Semester database backup could not be completed."
DATABASE_BACKUP_STORAGE_ERROR_MESSAGE = "Semester database backup storage could not be configured."
AVATAR_BACKUP_ERROR_MESSAGE = "Semester avatar backup could not be completed."
BACKUP_VERIFICATION_ERROR_MESSAGE = "Semester backup verification could not be completed."
BACKUP_EXPIRY_ERROR_MESSAGE = "Semester backup expiry cleanup could not be completed."
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
    commands.add_parser(
        "configure-local-runtime-role",
        help="Set the local Compose runtime-role password after migrations.",
    )
    commands.add_parser(
        "configure-semester-backup-storage",
        help="Create or update the private semester database-backup bucket.",
    )
    database_backup_parser = commands.add_parser(
        "backup-semester-database",
        help="Create and verify the database artifact for an existing semester backup.",
    )
    database_backup_parser.add_argument(
        "--backup-id",
        required=True,
        type=UUID,
        help="Stable UUID of the existing CREATING semester backup.",
    )
    avatar_backup_parser = commands.add_parser(
        "backup-semester-avatars",
        help="Create and verify private avatar objects for an existing semester backup.",
    )
    avatar_backup_parser.add_argument(
        "--backup-id",
        required=True,
        type=UUID,
        help="Stable UUID of the existing CREATING semester backup.",
    )
    backup_verification_parser = commands.add_parser(
        "verify-semester-backup",
        help="Verify both private packages and finalize eligible retention metadata.",
    )
    backup_verification_parser.add_argument(
        "--backup-id",
        required=True,
        type=UUID,
        help="Stable UUID of the semester backup to verify.",
    )
    backup_expiry_parser = commands.add_parser(
        "expire-semester-backups",
        help="Expire and clean one bounded batch of due private semester backups.",
    )
    backup_expiry_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BACKUP_EXPIRY_BATCH_SIZE,
        help=f"Backups per batch (default: {DEFAULT_BACKUP_EXPIRY_BATCH_SIZE}).",
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
    invitation_expiry_parser = commands.add_parser(
        "expire-invitations",
        help="Persist one bounded batch of seven-day invitation expirations.",
    )
    invitation_expiry_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_INVITATION_EXPIRY_BATCH_SIZE,
        help=f"Rows per batch (default: {DEFAULT_INVITATION_EXPIRY_BATCH_SIZE}).",
    )
    chat_cleanup_parser = commands.add_parser(
        "cleanup-expired-chat-messages",
        help="Hard-delete one bounded batch of authoritatively expired Buddy messages.",
    )
    chat_cleanup_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_CHAT_CLEANUP_BATCH_SIZE,
        help=f"Rows per batch (default: {DEFAULT_CHAT_CLEANUP_BATCH_SIZE}).",
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


async def _configure_semester_backup_storage_command() -> None:
    await SupabaseDatabaseBackupStore(get_storage_settings()).configure_bucket()


async def _database_backup_command(*, backup_id: UUID) -> DatabaseBackupReport:
    adapter = PostgresBinaryCopyBackupAdapter(get_backup_database_settings())
    storage = SupabaseDatabaseBackupStore(get_storage_settings())
    try:
        return await create_semester_database_backup(
            get_session_factory(),
            backup_id=backup_id,
            adapter=adapter,
            storage=storage,
        )
    finally:
        await dispose_database_engine()


async def _avatar_backup_command(*, backup_id: UUID) -> AvatarBackupReport:
    settings = get_storage_settings()
    adapter = AvatarBackupAdapter(ImageStorageService(SupabaseStorageTransport(settings)))
    storage = SupabaseDatabaseBackupStore(settings)
    try:
        return await create_semester_avatar_backup(
            get_session_factory(),
            backup_id=backup_id,
            adapter=adapter,
            storage=storage,
        )
    finally:
        await dispose_database_engine()


async def _backup_verification_command(*, backup_id: UUID) -> SemesterBackupVerificationReport:
    storage = SupabaseDatabaseBackupStore(get_storage_settings())
    try:
        return await verify_semester_backup(
            get_session_factory(),
            backup_id=backup_id,
            storage=storage,
        )
    finally:
        await dispose_database_engine()


async def _backup_expiry_command(*, batch_size: int) -> SemesterBackupExpiryReport:
    storage = SupabaseDatabaseBackupStore(get_storage_settings())
    started_at = perf_counter()
    report = SemesterBackupExpiryReport(selected=0, expired=0, cleaned=0, failed=0)
    error_type: str | None = None
    try:
        report = await process_expired_semester_backup_batch(
            get_session_factory(),
            storage=storage,
            batch_size=batch_size,
        )
        return report
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        duration_ms = max(0, round((perf_counter() - started_at) * 1000))
        emit_semester_backup_expiry_event(
            batch_size=batch_size,
            selected=report.selected,
            expired=report.expired,
            cleaned=report.cleaned,
            failed=report.failed,
            duration_ms=duration_ms,
            error_type=error_type,
        )
        await dispose_database_engine()


async def _configure_local_runtime_role_command() -> None:
    """Set a local-only runtime password without putting it in argv or SQL logs."""
    password = os.getenv("LOCAL_RUNTIME_DATABASE_PASSWORD")
    if os.getenv("APP_ENV") != "local" or password is None or not password:
        raise DatabaseConfigurationError("Local runtime role configuration is unavailable.")
    url = migration_database_url(get_migration_database_settings())
    if url.host not in {"127.0.0.1", "localhost", "postgres"}:
        raise DatabaseConfigurationError("Local runtime role requires a local database host.")

    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            statement = await connection.scalar(
                text(
                    "SELECT format('ALTER ROLE vgu_buddy_runtime PASSWORD %L', "
                    "CAST(:runtime_password AS text))"
                ),
                {"runtime_password": password},
            )
            if not isinstance(statement, str):
                raise DatabaseConfigurationError("Local runtime role statement was not created.")
            await connection.exec_driver_sql(statement)
    finally:
        await engine.dispose()


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
    resolvers = default_email_delivery_resolver_registry()
    worker_id = f"email-worker-{uuid4()}"
    try:
        while True:
            report = await process_transactional_outbox_batch(
                get_session_factory(),
                worker_id=worker_id,
                provider=provider,
                templates=templates,
                resolvers=resolvers,
                batch_size=batch_size,
            )
            if once:
                return report
            if report.claimed == 0:
                await asyncio.sleep(poll_seconds)
    finally:
        await dispose_database_engine()


async def _invitation_expiry_command(*, batch_size: int) -> InvitationExpiryReport:
    started_at = perf_counter()
    report = InvitationExpiryReport(selected=0, expired=0)
    error_type: str | None = None
    try:
        report = await process_invitation_expiry_batch(
            get_session_factory(),
            batch_size=batch_size,
        )
        return report
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        duration_ms = max(0, round((perf_counter() - started_at) * 1000))
        emit_invitation_expiry_event(
            batch_size=batch_size,
            selected=report.selected,
            expired=report.expired,
            duration_ms=duration_ms,
            error_type=error_type,
        )
        await dispose_database_engine()


async def _chat_cleanup_command(*, batch_size: int) -> ChatCleanupReport:
    started_at = perf_counter()
    report = ChatCleanupReport(selected=0, deleted=0)
    error_type: str | None = None
    try:
        report = await process_chat_cleanup_batch(
            get_session_factory(),
            batch_size=batch_size,
        )
        return report
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        duration_ms = max(0, round((perf_counter() - started_at) * 1000))
        emit_chat_cleanup_event(
            batch_size=batch_size,
            selected=report.selected,
            deleted=report.deleted,
            duration_ms=duration_ms,
            error_type=error_type,
        )
        await dispose_database_engine()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse and execute one operational command with sanitized terminal failures."""
    raw_arguments = list(argv) if argv is not None else sys.argv[1:]
    if any(
        argument == "--password" or argument.startswith("--password=") for argument in raw_arguments
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

    if arguments.command == "configure-local-runtime-role":
        try:
            asyncio.run(_configure_local_runtime_role_command())
        except (DatabaseConfigurationError, OSError, SQLAlchemyError):
            print(f"Error: {LOCAL_RUNTIME_ROLE_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print("Local runtime database role configured.")
        return 0

    if arguments.command == "configure-semester-backup-storage":
        try:
            asyncio.run(_configure_semester_backup_storage_command())
        except (StorageConfigurationError, DatabaseBackupStorageError, OSError):
            print(f"Error: {DATABASE_BACKUP_STORAGE_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print("Semester database backup storage configured.")
        return 0

    if arguments.command == "backup-semester-database":
        try:
            backup_report = asyncio.run(_database_backup_command(backup_id=arguments.backup_id))
        except (
            DatabaseConfigurationError,
            StorageConfigurationError,
            DatabaseBackupError,
            DatabaseBackupStorageError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {DATABASE_BACKUP_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Semester database backup: "
            f"backup_id={backup_report.backup_id}, tables={backup_report.table_count}, "
            f"rows={backup_report.row_count}, bytes={backup_report.artifact_size_bytes}, "
            f"state={backup_report.state.value}"
        )
        return 0

    if arguments.command == "backup-semester-avatars":
        try:
            avatar_report = asyncio.run(_avatar_backup_command(backup_id=arguments.backup_id))
        except (
            DatabaseConfigurationError,
            StorageConfigurationError,
            AvatarBackupError,
            DatabaseBackupStorageError,
            StorageOperationError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {AVATAR_BACKUP_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Semester avatar backup: "
            f"backup_id={avatar_report.backup_id}, objects={avatar_report.object_count}, "
            f"bytes={avatar_report.total_bytes}, state={avatar_report.state.value}"
        )
        return 0

    if arguments.command == "verify-semester-backup":
        try:
            verification_report = asyncio.run(
                _backup_verification_command(backup_id=arguments.backup_id)
            )
        except (
            DatabaseConfigurationError,
            StorageConfigurationError,
            SemesterBackupVerificationError,
            DatabaseBackupStorageError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {BACKUP_VERIFICATION_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Semester backup verification: "
            f"backup_id={verification_report.backup_id}, "
            f"state={verification_report.persisted_state.value}, "
            f"effective_state={verification_report.effective_state.value}, "
            f"database_rows={verification_report.database_rows}, "
            f"avatar_objects={verification_report.avatar_objects}, "
            f"newly_verified={str(verification_report.newly_verified).lower()}, "
            f"newly_ready={str(verification_report.newly_ready).lower()}"
        )
        return 0

    if arguments.command == "expire-semester-backups":
        try:
            backup_expiry_report = asyncio.run(
                _backup_expiry_command(batch_size=arguments.batch_size)
            )
        except (
            DatabaseConfigurationError,
            StorageConfigurationError,
            SemesterBackupExpiryError,
            SemesterBackupExpiryValidationError,
            DatabaseBackupStorageError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {BACKUP_EXPIRY_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Semester backup expiry: "
            f"selected={backup_expiry_report.selected}, "
            f"expired={backup_expiry_report.expired}, "
            f"cleaned={backup_expiry_report.cleaned}, "
            f"failed={backup_expiry_report.failed}"
        )
        return 1 if backup_expiry_report.failed else 0

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

    if arguments.command == "expire-invitations":
        try:
            expiry_report = asyncio.run(_invitation_expiry_command(batch_size=arguments.batch_size))
        except (
            DatabaseConfigurationError,
            InvitationExpiryValidationError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {INVITATION_EXPIRY_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            f"Invitation expiry: selected={expiry_report.selected}, expired={expiry_report.expired}"
        )
        return 0

    if arguments.command == "cleanup-expired-chat-messages":
        try:
            cleanup_report = asyncio.run(_chat_cleanup_command(batch_size=arguments.batch_size))
        except (
            DatabaseConfigurationError,
            ChatCleanupValidationError,
            OSError,
            SQLAlchemyError,
        ):
            print(f"Error: {CHAT_CLEANUP_ERROR_MESSAGE}", file=sys.stderr)
            return 1
        print(
            "Chat message cleanup: "
            f"selected={cleanup_report.selected}, deleted={cleanup_report.deleted}"
        )
        return 0

    return 2  # pragma: no cover - argparse owns this invariant.


if __name__ == "__main__":
    raise SystemExit(main())
