"""Focused idempotency boundaries for the SEM-007 lifecycle bridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

import app.services.semester_management as management
from app.models import User, UserRole
from app.services.semester_database_backup import (
    DatabaseBackupAlreadyAttachedError,
    DatabaseBackupBusyError,
)

OPERATION_ID = UUID("11111111-1111-4111-8111-111111111111")
BACKUP_ID = UUID("22222222-2222-4222-8222-222222222222")
ADMIN_ID = UUID("33333333-3333-4333-8333-333333333333")


def _admin() -> User:
    return User(
        id=ADMIN_ID,
        email="semester-admin@example.invalid",
        password_hash="unused-test-hash",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )


@pytest.mark.anyio
async def test_duplicate_reset_prepare_does_not_race_a_busy_database_backup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = AsyncMock(return_value=(OPERATION_ID, BACKUP_ID))
    database = AsyncMock(side_effect=DatabaseBackupBusyError("busy"))
    avatar = AsyncMock()
    verify = AsyncMock()
    monkeypatch.setattr(management, "_prepare_reset_metadata", metadata)
    monkeypatch.setattr(management, "create_semester_database_backup", database)
    monkeypatch.setattr(management, "create_semester_avatar_backup", avatar)
    monkeypatch.setattr(management, "verify_semester_backup", verify)

    result = await management.prepare_semester_reset(
        MagicMock(),
        actor=_admin(),
        snapshot_adapter=MagicMock(),
        backup_storage=MagicMock(),
        avatar_storage=MagicMock(),
    )

    assert result == (OPERATION_ID, BACKUP_ID)
    avatar.assert_not_awaited()
    verify.assert_not_awaited()


@pytest.mark.anyio
async def test_retry_resumes_after_an_already_attached_database_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        management,
        "_prepare_reset_metadata",
        AsyncMock(return_value=(OPERATION_ID, BACKUP_ID)),
    )
    monkeypatch.setattr(
        management,
        "create_semester_database_backup",
        AsyncMock(side_effect=DatabaseBackupAlreadyAttachedError("attached")),
    )
    avatar = AsyncMock()
    verify = AsyncMock()
    monkeypatch.setattr(management, "create_semester_avatar_backup", avatar)
    monkeypatch.setattr(management, "verify_semester_backup", verify)

    result = await management.prepare_semester_reset(
        MagicMock(),
        actor=_admin(),
        snapshot_adapter=MagicMock(),
        backup_storage=MagicMock(),
        avatar_storage=MagicMock(),
    )

    assert result == (OPERATION_ID, BACKUP_ID)
    avatar.assert_awaited_once()
    verify.assert_awaited_once()
