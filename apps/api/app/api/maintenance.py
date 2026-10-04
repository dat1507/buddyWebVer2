"""Private provider-neutral entry point for scheduled retention maintenance."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse

from app.core.config import (
    MaintenanceConfigurationError,
    get_maintenance_worker_settings,
    get_storage_settings,
)
from app.core.database import get_session_factory
from app.services.database_backup_storage import SupabaseDatabaseBackupStore
from app.services.maintenance import DEFAULT_MAINTENANCE_BATCH_SIZE, run_maintenance_batch

router = APIRouter(prefix="/api/internal", include_in_schema=False)


def _response(body: dict[str, object], status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post("/maintenance")
async def run_scheduled_maintenance(
    x_cron_secret: str = Header(default="", alias="x-cron-secret"),
) -> JSONResponse:
    """Authenticate one Cron call and run only bounded, retry-safe maintenance."""
    try:
        settings = get_maintenance_worker_settings()
    except MaintenanceConfigurationError:
        return _response(
            {"error": "maintenance_configuration_unavailable"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    supplied = x_cron_secret.encode()
    expected = settings.cron_secret.get_secret_value()
    if len(supplied) > 1024 or not hmac.compare_digest(supplied, expected):
        return _response({"error": "unauthorized"}, status.HTTP_401_UNAUTHORIZED)

    try:
        report = await run_maintenance_batch(
            get_session_factory(),
            storage=SupabaseDatabaseBackupStore(get_storage_settings()),
        )
    except Exception:
        return _response(
            {"error": "maintenance_unavailable"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return _response(
        {
            "status": "completed",
            "batch_size": DEFAULT_MAINTENANCE_BATCH_SIZE,
            "invitation_expiry": {
                "selected": report.invitation_expiry.selected,
                "expired": report.invitation_expiry.expired,
            },
            "chat_cleanup": {
                "selected": report.chat_cleanup.selected,
                "deleted": report.chat_cleanup.deleted,
            },
            "semester_backup_expiry": {
                "selected": report.semester_backup_expiry.selected,
                "expired": report.semester_backup_expiry.expired,
                "cleaned": report.semester_backup_expiry.cleaned,
                "failed": report.semester_backup_expiry.failed,
            },
        },
        status.HTTP_200_OK,
    )
