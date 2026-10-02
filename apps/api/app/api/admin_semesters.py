"""ADMIN-only preflight and safeguarded semester reset endpoints."""

from __future__ import annotations

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import (
    get_image_storage_service,
    require_role,
    require_session_csrf,
)
from app.core.config import (
    BackupDatabaseSettings,
    StorageSettings,
    get_backup_database_settings,
    get_storage_settings,
)
from app.core.database import get_database_session, get_session_factory
from app.models import User, UserRole
from app.schemas.semester import (
    SemesterResetExecuteRequest,
    SemesterResetExecuteResponse,
    SemesterResetPreflightResponse,
)
from app.services.csrf import CsrfTokenClaims
from app.services.database_backup_storage import SupabaseDatabaseBackupStore
from app.services.image_storage import ImageStorageService
from app.services.semester_database_backup import PostgresBinaryCopyBackupAdapter
from app.services.semester_reset import (
    SemesterResetAuthorizationError,
    SemesterResetBusyError,
    SemesterResetError,
    SemesterResetSnapshotError,
    SemesterResetStateError,
    SemesterResetStorageError,
    execute_semester_reset,
    get_semester_reset_preflight,
)

_NO_STORE_HEADERS: Final = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "Vary": "Cookie",
}
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(
    prefix="/api/admin/semesters",
    tags=["admin-semesters"],
    responses={
        401: {"description": "Authentication required."},
        403: {"description": "An ADMIN session and destructive confirmation are required."},
    },
)


def _mark_private(response: Response) -> None:
    for name, value in _NO_STORE_HEADERS.items():
        response.headers[name] = value


def _backup_storage(
    settings: Annotated[StorageSettings, Depends(get_storage_settings)],
) -> SupabaseDatabaseBackupStore:
    return SupabaseDatabaseBackupStore(settings)


def _snapshot_adapter(
    settings: Annotated[BackupDatabaseSettings, Depends(get_backup_database_settings)],
) -> PostgresBinaryCopyBackupAdapter:
    return PostgresBinaryCopyBackupAdapter(settings)


@router.get("/reset/preflight", response_model=SemesterResetPreflightResponse)
async def read_semester_reset_preflight(
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SemesterResetPreflightResponse:
    """Return only aggregate impact and the stable destructive phrase."""
    try:
        result = await get_semester_reset_preflight(session, current_admin)
    except SemesterResetStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester reset preflight is unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterResetPreflightResponse(
        semester_id=result.semester_id,
        operation_id=result.operation_id,
        backup_id=result.backup_id,
        backup_state=result.backup_state,
        backup_verified=result.backup_verified,
        can_execute=result.can_execute,
        affected_counts=result.affected_counts,
        preserved_counts=result.preserved_counts,
        confirmation_phrase=result.confirmation_phrase,
    )


@router.post(
    "/reset/{operation_id}/execute",
    response_model=SemesterResetExecuteResponse,
    responses={
        409: {"description": "Reset state, backup, or exclusive barrier is not eligible."},
        503: {"description": "Reset storage or database execution failed safely."},
    },
)
async def execute_admin_semester_reset(
    operation_id: UUID,
    payload: SemesterResetExecuteRequest,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
    snapshot_adapter: Annotated[PostgresBinaryCopyBackupAdapter, Depends(_snapshot_adapter)],
    backup_storage: Annotated[SupabaseDatabaseBackupStore, Depends(_backup_storage)],
    avatar_storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> SemesterResetExecuteResponse:
    """Execute one phrase-confirmed, immediately re-authenticated reset."""
    try:
        report = await execute_semester_reset(
            session_factory,
            operation_id=operation_id,
            backup_id=payload.backup_id,
            admin_id=current_admin.id,
            current_password=payload.current_password,
            confirmation_phrase=payload.confirmation_phrase,
            snapshot_adapter=snapshot_adapter,
            backup_storage=backup_storage,
            avatar_storage=avatar_storage,
        )
    except SemesterResetAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Semester reset authorization failed.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except (SemesterResetBusyError, SemesterResetStateError, SemesterResetSnapshotError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester reset is not eligible.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except (SemesterResetStorageError, DBAPIError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester reset failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except SemesterResetError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester reset failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterResetExecuteResponse(
        operation_id=report.operation_id,
        backup_id=report.backup_id,
        closed_semester_id=report.closed_semester_id,
        new_semester_id=report.new_semester_id,
        deleted_counts=report.deleted_counts,
        avatar_objects_processed=report.avatar_objects_processed,
        operation_state=report.operation_state,
        backup_state=report.backup_state,
        idempotent_replay=report.idempotent_replay,
    )
