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
    SemesterBackupStatusResponse,
    SemesterManagementStatusResponse,
    SemesterOperationPreparedResponse,
    SemesterOperationStatusResponse,
    SemesterResetExecuteRequest,
    SemesterResetExecuteResponse,
    SemesterResetPreflightResponse,
    SemesterRestoreExecuteRequest,
    SemesterRestoreExecuteResponse,
    SemesterRestorePreflightResponse,
)
from app.services.csrf import CsrfTokenClaims
from app.services.database_backup_storage import SupabaseDatabaseBackupStore
from app.services.image_storage import ImageStorageService
from app.services.semester_database_backup import PostgresBinaryCopyBackupAdapter
from app.services.semester_management import (
    SemesterManagementConflictError,
    SemesterManagementError,
    SemesterManagementStatus,
    get_semester_management_status,
    prepare_semester_reset,
    prepare_semester_restore,
)
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
from app.services.semester_restore import (
    SemesterRestoreAuthorizationError,
    SemesterRestoreBusyError,
    SemesterRestoreError,
    SemesterRestorePackageError,
    SemesterRestoreStateError,
    SemesterRestoreStorageError,
    execute_semester_restore,
    get_semester_restore_preflight,
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


def _management_response(result: SemesterManagementStatus) -> SemesterManagementStatusResponse:
    operation_fields = (
        "id",
        "operation_type",
        "state",
        "requested_at",
        "started_at",
        "completed_at",
        "failure_code",
    )
    reset = (
        SemesterOperationStatusResponse(
            **{field: getattr(result.reset_operation, field) for field in operation_fields}
        )
        if result.reset_operation is not None
        else None
    )
    restore = (
        SemesterOperationStatusResponse(
            **{field: getattr(result.restore_operation, field) for field in operation_fields}
        )
        if result.restore_operation is not None
        else None
    )
    backup = (
        SemesterBackupStatusResponse(
            id=result.backup.id,
            state=result.backup.state,
            created_at=result.backup.created_at,
            verified_at=result.backup.verified_at,
            expires_at=result.backup.expires_at,
        )
        if result.backup is not None
        else None
    )
    return SemesterManagementStatusResponse(
        current_semester_id=result.current_semester_id,
        current_semester_status=result.current_semester_status,
        current_student_accounts_created=result.current_student_accounts_created,
        reset_operation=reset,
        restore_operation=restore,
        backup=backup,
        can_prepare_reset=result.can_prepare_reset,
        can_prepare_restore=result.can_prepare_restore,
        restore_block_reason=result.restore_block_reason,
    )


@router.get("/management", response_model=SemesterManagementStatusResponse)
async def read_semester_management_status(
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SemesterManagementStatusResponse:
    try:
        result = await get_semester_management_status(session, current_admin)
    except SemesterManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester management status is unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return _management_response(result)


@router.post("/reset/prepare", response_model=SemesterOperationPreparedResponse)
async def prepare_admin_semester_reset(
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    snapshot_adapter: Annotated[PostgresBinaryCopyBackupAdapter, Depends(_snapshot_adapter)],
    backup_storage: Annotated[SupabaseDatabaseBackupStore, Depends(_backup_storage)],
    avatar_storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> SemesterOperationPreparedResponse:
    try:
        operation_id, backup_id = await prepare_semester_reset(
            session_factory,
            actor=current_admin,
            snapshot_adapter=snapshot_adapter,
            backup_storage=backup_storage,
            avatar_storage=avatar_storage,
        )
    except SemesterManagementConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester reset preparation is not eligible.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except SemesterManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester reset preparation failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterOperationPreparedResponse(operation_id=operation_id, backup_id=backup_id)


@router.post("/restore/prepare", response_model=SemesterOperationPreparedResponse)
async def prepare_admin_semester_restore(
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> SemesterOperationPreparedResponse:
    try:
        operation_id, backup_id = await prepare_semester_restore(session_factory, current_admin)
    except SemesterManagementConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester restore preparation is not eligible.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except SemesterManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester restore preparation failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterOperationPreparedResponse(operation_id=operation_id, backup_id=backup_id)


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


@router.get(
    "/restore/{operation_id}/preflight",
    response_model=SemesterRestorePreflightResponse,
)
async def read_semester_restore_preflight(
    operation_id: UUID,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SemesterRestorePreflightResponse:
    """Return only persisted restore eligibility and aggregate package counts."""
    try:
        result = await get_semester_restore_preflight(
            session,
            current_admin,
            operation_id=operation_id,
        )
    except SemesterRestoreStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester restore preflight is unavailable.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterRestorePreflightResponse(
        operation_id=result.operation_id,
        backup_id=result.backup_id,
        source_semester_id=result.source_semester_id,
        current_semester_id=result.current_semester_id,
        backup_state=result.backup_state,
        can_execute=result.can_execute,
        can_finalize_new_cohort_block=result.can_finalize_new_cohort_block,
        restored_counts=result.restored_counts,
        avatar_object_count=result.avatar_object_count,
        confirmation_phrase=result.confirmation_phrase,
    )


@router.post(
    "/restore/{operation_id}/execute",
    response_model=SemesterRestoreExecuteResponse,
    responses={
        409: {"description": "Restore state, backup, or exclusive barrier is not eligible."},
        503: {"description": "Restore storage or database execution failed safely."},
    },
)
async def execute_admin_semester_restore(
    operation_id: UUID,
    payload: SemesterRestoreExecuteRequest,
    response: Response,
    current_admin: Annotated[User, Depends(require_admin)],
    _csrf: Annotated[CsrfTokenClaims, Depends(require_session_csrf)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_session_factory),
    ],
    restore_adapter: Annotated[PostgresBinaryCopyBackupAdapter, Depends(_snapshot_adapter)],
    backup_storage: Annotated[SupabaseDatabaseBackupStore, Depends(_backup_storage)],
    avatar_storage: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> SemesterRestoreExecuteResponse:
    """Execute one phrase-confirmed, immediately re-authenticated restore."""
    try:
        report = await execute_semester_restore(
            session_factory,
            operation_id=operation_id,
            backup_id=payload.backup_id,
            admin_id=current_admin.id,
            current_password=payload.current_password,
            confirmation_phrase=payload.confirmation_phrase,
            restore_adapter=restore_adapter,
            backup_storage=backup_storage,
            avatar_storage=avatar_storage,
        )
    except SemesterRestoreAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Semester restore authorization failed.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except (SemesterRestoreBusyError, SemesterRestoreStateError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester restore is not eligible.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except (
        SemesterRestoreStorageError,
        SemesterRestorePackageError,
        DBAPIError,
        SQLAlchemyError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester restore failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    except SemesterRestoreError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semester restore failed safely.",
            headers=_NO_STORE_HEADERS,
        ) from error
    _mark_private(response)
    return SemesterRestoreExecuteResponse(
        operation_id=report.operation_id,
        backup_id=report.backup_id,
        source_semester_id=report.source_semester_id,
        restored_counts=report.restored_counts,
        avatar_objects_restored=report.avatar_objects_restored,
        operation_state=report.operation_state,
        backup_state=report.backup_state,
        idempotent_replay=report.idempotent_replay,
    )
