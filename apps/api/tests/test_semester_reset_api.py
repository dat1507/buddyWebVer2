"""ADMIN, CSRF, step-up, and response privacy tests for SEM-005 APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.admin_semesters as semester_api
from app.api.dependencies import get_image_storage_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session, get_session_factory
from app.main import app
from app.models import (
    SemesterBackupState,
    SemesterOperationState,
    SemesterOperationType,
    SemesterStatus,
    User,
    UserRole,
)
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.semester_management import (
    SemesterBackupStatus,
    SemesterManagementConflictError,
    SemesterManagementStatus,
    SemesterOperationStatus,
)
from app.services.semester_reset import (
    SemesterResetPreflight,
    SemesterResetReport,
    SemesterResetStateError,
)
from app.services.semester_restore import (
    SemesterRestorePreflight,
    SemesterRestoreReport,
    SemesterRestoreStateError,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
SEMESTER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
OPERATION_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
BACKUP_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
NEW_SEMESTER_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
SIGNING_KEY = bytes(range(32))
ORIGIN = "http://testserver"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(bytes(reversed(SIGNING_KEY))),
        secure_cookies=False,
        trusted_origins=(ORIGIN,),
    )


def _actor(role: UserRole = UserRole.ADMIN) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _install(actor: User) -> tuple[dict[str, str], dict[str, str]]:
    session_mock = MagicMock(spec=AsyncSession)
    session_mock.scalar = AsyncMock(return_value=actor)
    session = cast(AsyncSession, session_mock)
    session_factory = MagicMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    auth = _auth_settings()
    csrf = _csrf_settings()
    pair = create_token_pair(ADMIN_ID, UserRole.ADMIN, auth)
    token = create_session_csrf_token(pair.session_id, csrf)
    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_auth_token_settings] = lambda: auth
    app.dependency_overrides[get_csrf_settings] = lambda: csrf
    app.dependency_overrides[semester_api._snapshot_adapter] = lambda: MagicMock()
    app.dependency_overrides[semester_api._backup_storage] = lambda: MagicMock()
    app.dependency_overrides[get_image_storage_service] = lambda: MagicMock()
    cookies = {
        DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
        csrf_cookie_name(csrf): token.value,
    }
    headers = {"Origin": ORIGIN, CSRF_HEADER_NAME: token.value}
    return cookies, headers


def _preflight() -> SemesterResetPreflight:
    return SemesterResetPreflight(
        semester_id=SEMESTER_ID,
        operation_id=OPERATION_ID,
        backup_id=BACKUP_ID,
        backup_state=SemesterBackupState.CREATING,
        backup_verified=True,
        can_execute=True,
        affected_counts={"users": 2},
        preserved_counts={"admins": 1},
        confirmation_phrase=f"RESET {SEMESTER_ID}",
    )


def _report() -> SemesterResetReport:
    return SemesterResetReport(
        operation_id=OPERATION_ID,
        backup_id=BACKUP_ID,
        closed_semester_id=SEMESTER_ID,
        new_semester_id=NEW_SEMESTER_ID,
        deleted_counts={"users": 2},
        avatar_objects_processed=1,
        operation_state=SemesterOperationState.SUCCEEDED,
        backup_state=SemesterBackupState.READY,
        idempotent_replay=False,
    )


def _restore_preflight() -> SemesterRestorePreflight:
    return SemesterRestorePreflight(
        operation_id=OPERATION_ID,
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        current_semester_id=NEW_SEMESTER_ID,
        backup_state=SemesterBackupState.READY,
        can_execute=True,
        can_finalize_new_cohort_block=False,
        restored_counts={"users": 2},
        avatar_object_count=1,
        confirmation_phrase=f"RESTORE {BACKUP_ID}",
    )


def _restore_report() -> SemesterRestoreReport:
    return SemesterRestoreReport(
        operation_id=OPERATION_ID,
        backup_id=BACKUP_ID,
        source_semester_id=SEMESTER_ID,
        restored_counts={"users": 2},
        avatar_objects_restored=1,
        operation_state=SemesterOperationState.SUCCEEDED,
        backup_state=SemesterBackupState.READY,
        idempotent_replay=False,
    )


def _management_status() -> SemesterManagementStatus:
    now = datetime(2026, 10, 2, tzinfo=UTC)
    return SemesterManagementStatus(
        current_semester_id=NEW_SEMESTER_ID,
        current_semester_status=SemesterStatus.CURRENT,
        current_student_accounts_created=0,
        reset_operation=SemesterOperationStatus(
            id=OPERATION_ID,
            operation_type=SemesterOperationType.RESET,
            state=SemesterOperationState.SUCCEEDED,
            requested_at=now,
            started_at=now,
            completed_at=now + timedelta(minutes=1),
            failure_code=None,
        ),
        restore_operation=None,
        backup=SemesterBackupStatus(
            id=BACKUP_ID,
            state=SemesterBackupState.READY,
            created_at=now,
            verified_at=now + timedelta(minutes=1),
            expires_at=now + timedelta(days=30),
        ),
        can_prepare_reset=True,
        can_prepare_restore=True,
        restore_block_reason=None,
    )


@pytest.mark.anyio
async def test_management_discovery_and_prepare_are_private_admin_csrf_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    discovery = AsyncMock(return_value=_management_status())
    reset_prepare = AsyncMock(return_value=(OPERATION_ID, BACKUP_ID))
    restore_prepare = AsyncMock(return_value=(OPERATION_ID, BACKUP_ID))
    monkeypatch.setattr(semester_api, "get_semester_management_status", discovery)
    monkeypatch.setattr(semester_api, "prepare_semester_reset", reset_prepare)
    monkeypatch.setattr(semester_api, "prepare_semester_restore", restore_prepare)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        status_response = await client.get("/api/admin/semesters/management")
        denied = await client.post("/api/admin/semesters/reset/prepare")
        reset_response = await client.post("/api/admin/semesters/reset/prepare", headers=headers)
        restore_response = await client.post(
            "/api/admin/semesters/restore/prepare", headers=headers
        )

    assert status_response.status_code == 200
    assert status_response.headers["cache-control"] == "private, no-store"
    assert status_response.json()["backup"]["state"] == "READY"
    assert status_response.json()["can_prepare_restore"] is True
    assert "confirmation_phrase" not in status_response.text
    assert denied.status_code == 403
    assert reset_response.json() == {
        "operation_id": str(OPERATION_ID),
        "backup_id": str(BACKUP_ID),
    }
    assert restore_response.status_code == 200
    reset_prepare.assert_awaited_once()
    restore_prepare.assert_awaited_once()


@pytest.mark.anyio
async def test_prepare_conflict_is_sanitized_and_user_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    service = AsyncMock(side_effect=SemesterManagementConflictError("private database detail"))
    monkeypatch.setattr(semester_api, "prepare_semester_restore", service)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        conflict = await client.post("/api/admin/semesters/restore/prepare", headers=headers)
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "Semester restore preparation is not eligible."}
    assert "database" not in conflict.text

    user_cookies, user_headers = _install(_actor(UserRole.USER))
    denied_service = AsyncMock()
    monkeypatch.setattr(semester_api, "prepare_semester_reset", denied_service)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=user_cookies
    ) as client:
        denied = await client.post("/api/admin/semesters/reset/prepare", headers=user_headers)
    assert denied.status_code == 403
    denied_service.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_preflight_is_aggregate_only_and_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, _ = _install(_actor())
    service = AsyncMock(return_value=_preflight())
    monkeypatch.setattr(semester_api, "get_semester_reset_preflight", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.get("/api/admin/semesters/reset/preflight")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["affected_counts"] == {"users": 2}
    assert response.json()["preserved_counts"] == {"admins": 1}
    forbidden = {"email", "message", "object_key", "password", "signed_url"}
    assert forbidden.isdisjoint(response.json())


@pytest.mark.anyio
async def test_admin_execute_requires_csrf_and_returns_safe_terminal_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    service = AsyncMock(return_value=_report())
    monkeypatch.setattr(semester_api, "execute_semester_reset", service)
    payload = {
        "backup_id": str(BACKUP_ID),
        "confirmation_phrase": f"RESET {SEMESTER_ID}",
        "current_password": "admin-current-password",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        denied = await client.post(
            f"/api/admin/semesters/reset/{OPERATION_ID}/execute",
            json=payload,
        )
        response = await client.post(
            f"/api/admin/semesters/reset/{OPERATION_ID}/execute",
            json=payload,
            headers=headers,
        )

    assert denied.status_code == 403
    assert response.status_code == 200
    assert response.json()["backup_state"] == "READY"
    assert response.json()["deleted_counts"] == {"users": 2}
    assert "current_password" not in response.text
    assert "confirmation_phrase" not in response.text
    service.assert_awaited_once()
    call = service.await_args
    assert call is not None
    assert call.kwargs["current_password"] == "admin-current-password"


@pytest.mark.anyio
async def test_user_role_is_denied_before_reset_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor(UserRole.USER))
    service = AsyncMock()
    monkeypatch.setattr(semester_api, "execute_semester_reset", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/semesters/reset/{OPERATION_ID}/execute",
            json={
                "backup_id": str(BACKUP_ID),
                "confirmation_phrase": f"RESET {SEMESTER_ID}",
                "current_password": "password",
            },
            headers=headers,
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_reset_state_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    service = AsyncMock(side_effect=SemesterResetStateError("private object path"))
    monkeypatch.setattr(semester_api, "execute_semester_reset", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/semesters/reset/{OPERATION_ID}/execute",
            json={
                "backup_id": str(BACKUP_ID),
                "confirmation_phrase": f"RESET {SEMESTER_ID}",
                "current_password": "password",
            },
            headers=headers,
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Semester reset is not eligible."}
    assert "private" not in response.text


@pytest.mark.anyio
async def test_openapi_marks_password_write_only_and_exposes_no_row_content() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN) as client:
        document = (await client.get("/openapi.json")).json()

    request = document["components"]["schemas"]["SemesterResetExecuteRequest"]
    response = document["components"]["schemas"]["SemesterResetExecuteResponse"]
    assert request["properties"]["current_password"]["writeOnly"] is True
    assert "current_password" not in response["properties"]
    assert {"email", "message", "object_key", "signed_url"}.isdisjoint(response["properties"])

    restore_request = document["components"]["schemas"]["SemesterRestoreExecuteRequest"]
    restore_response = document["components"]["schemas"]["SemesterRestoreExecuteResponse"]
    assert restore_request["properties"]["current_password"]["writeOnly"] is True
    assert "current_password" not in restore_response["properties"]
    assert {"email", "message", "object_key", "signed_url"}.isdisjoint(
        restore_response["properties"]
    )


@pytest.mark.anyio
async def test_restore_preflight_and_execute_are_admin_private_and_csrf_guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    preflight = AsyncMock(return_value=_restore_preflight())
    execute = AsyncMock(return_value=_restore_report())
    monkeypatch.setattr(semester_api, "get_semester_restore_preflight", preflight)
    monkeypatch.setattr(semester_api, "execute_semester_restore", execute)
    payload = {
        "backup_id": str(BACKUP_ID),
        "confirmation_phrase": f"RESTORE {BACKUP_ID}",
        "current_password": "admin-current-password",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        preflight_response = await client.get(
            f"/api/admin/semesters/restore/{OPERATION_ID}/preflight"
        )
        denied = await client.post(
            f"/api/admin/semesters/restore/{OPERATION_ID}/execute",
            json=payload,
        )
        response = await client.post(
            f"/api/admin/semesters/restore/{OPERATION_ID}/execute",
            json=payload,
            headers=headers,
        )

    assert preflight_response.status_code == 200
    assert preflight_response.headers["cache-control"] == "private, no-store"
    assert preflight_response.json()["restored_counts"] == {"users": 2}
    assert preflight_response.json()["can_finalize_new_cohort_block"] is False
    assert denied.status_code == 403
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["avatar_objects_restored"] == 1
    assert "current_password" not in response.text
    execute.assert_awaited_once()


@pytest.mark.anyio
async def test_restore_state_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor())
    service = AsyncMock(side_effect=SemesterRestoreStateError("private object path"))
    monkeypatch.setattr(semester_api, "execute_semester_restore", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/semesters/restore/{OPERATION_ID}/execute",
            json={
                "backup_id": str(BACKUP_ID),
                "confirmation_phrase": f"RESTORE {BACKUP_ID}",
                "current_password": "password",
            },
            headers=headers,
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Semester restore is not eligible."}
    assert "private" not in response.text


@pytest.mark.anyio
async def test_user_role_is_denied_before_restore_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies, headers = _install(_actor(UserRole.USER))
    service = AsyncMock()
    monkeypatch.setattr(semester_api, "execute_semester_restore", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies
    ) as client:
        response = await client.post(
            f"/api/admin/semesters/restore/{OPERATION_ID}/execute",
            json={
                "backup_id": str(BACKUP_ID),
                "confirmation_phrase": f"RESTORE {BACKUP_ID}",
                "current_password": "password",
            },
            headers=headers,
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}
    service.assert_not_awaited()
