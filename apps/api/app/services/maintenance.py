"""One bounded maintenance pass over existing expiry and retention services."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.observability import (
    emit_chat_cleanup_event,
    emit_invitation_expiry_event,
    emit_semester_backup_expiry_event,
)
from app.services.chat_cleanup import ChatCleanupReport, process_chat_cleanup_batch
from app.services.database_backup_storage import DatabaseBackupArtifactStore
from app.services.invitation_expiry import InvitationExpiryReport, process_invitation_expiry_batch
from app.services.semester_backup_verification import (
    SemesterBackupExpiryReport,
    process_expired_semester_backup_batch,
)

DEFAULT_MAINTENANCE_BATCH_SIZE: Final = 100


@dataclass(frozen=True, slots=True)
class MaintenanceReport:
    """Aggregate-only result safe to return to the trusted Cron caller."""

    invitation_expiry: InvitationExpiryReport
    chat_cleanup: ChatCleanupReport
    semester_backup_expiry: SemesterBackupExpiryReport


async def run_maintenance_batch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    storage: DatabaseBackupArtifactStore,
    batch_size: int = DEFAULT_MAINTENANCE_BATCH_SIZE,
) -> MaintenanceReport:
    """Run existing bounded jobs sequentially and preserve their atomic boundaries."""
    invitation_started = perf_counter()
    invitation_report = InvitationExpiryReport(selected=0, expired=0)
    invitation_error: str | None = None
    try:
        invitation_report = await process_invitation_expiry_batch(
            session_factory,
            batch_size=batch_size,
        )
    except Exception as error:
        invitation_error = type(error).__name__
        raise
    finally:
        emit_invitation_expiry_event(
            batch_size=batch_size,
            selected=invitation_report.selected,
            expired=invitation_report.expired,
            duration_ms=max(0, round((perf_counter() - invitation_started) * 1000)),
            error_type=invitation_error,
        )

    chat_started = perf_counter()
    chat_report = ChatCleanupReport(selected=0, deleted=0)
    chat_error: str | None = None
    try:
        chat_report = await process_chat_cleanup_batch(
            session_factory,
            batch_size=batch_size,
        )
    except Exception as error:
        chat_error = type(error).__name__
        raise
    finally:
        emit_chat_cleanup_event(
            batch_size=batch_size,
            selected=chat_report.selected,
            deleted=chat_report.deleted,
            duration_ms=max(0, round((perf_counter() - chat_started) * 1000)),
            error_type=chat_error,
        )

    backup_started = perf_counter()
    backup_report = SemesterBackupExpiryReport(selected=0, expired=0, cleaned=0, failed=0)
    backup_error: str | None = None
    try:
        backup_report = await process_expired_semester_backup_batch(
            session_factory,
            storage=storage,
            batch_size=batch_size,
        )
        if backup_report.failed:
            raise RuntimeError("One or more expired backup artifacts could not be cleaned.")
    except Exception as error:
        backup_error = type(error).__name__
        raise
    finally:
        emit_semester_backup_expiry_event(
            batch_size=batch_size,
            selected=backup_report.selected,
            expired=backup_report.expired,
            cleaned=backup_report.cleaned,
            failed=backup_report.failed,
            duration_ms=max(0, round((perf_counter() - backup_started) * 1000)),
            error_type=backup_error,
        )

    return MaintenanceReport(invitation_report, chat_report, backup_report)
