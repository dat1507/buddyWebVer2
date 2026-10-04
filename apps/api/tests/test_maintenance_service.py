"""Provider-neutral orchestration tests for one bounded maintenance pass."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.maintenance as maintenance
from app.services.chat_cleanup import ChatCleanupReport
from app.services.database_backup_storage import DatabaseBackupArtifactStore
from app.services.invitation_expiry import InvitationExpiryReport
from app.services.semester_backup_verification import SemesterBackupExpiryReport


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _factory() -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], object())


def _storage() -> DatabaseBackupArtifactStore:
    return cast(DatabaseBackupArtifactStore, object())


@pytest.mark.anyio
async def test_maintenance_reuses_all_three_bounded_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _factory()
    storage = _storage()
    invitations = AsyncMock(return_value=InvitationExpiryReport(selected=1, expired=1))
    chat = AsyncMock(return_value=ChatCleanupReport(selected=2, deleted=2))
    backups = AsyncMock(
        return_value=SemesterBackupExpiryReport(
            selected=3,
            expired=3,
            cleaned=3,
            failed=0,
        )
    )
    invitation_event = Mock()
    chat_event = Mock()
    backup_event = Mock()
    monkeypatch.setattr(maintenance, "process_invitation_expiry_batch", invitations)
    monkeypatch.setattr(maintenance, "process_chat_cleanup_batch", chat)
    monkeypatch.setattr(maintenance, "process_expired_semester_backup_batch", backups)
    monkeypatch.setattr(maintenance, "emit_invitation_expiry_event", invitation_event)
    monkeypatch.setattr(maintenance, "emit_chat_cleanup_event", chat_event)
    monkeypatch.setattr(maintenance, "emit_semester_backup_expiry_event", backup_event)

    report = await maintenance.run_maintenance_batch(factory, storage=storage)

    assert report.invitation_expiry.expired == 1
    assert report.chat_cleanup.deleted == 2
    assert report.semester_backup_expiry.cleaned == 3
    invitations.assert_awaited_once_with(factory, batch_size=100)
    chat.assert_awaited_once_with(factory, batch_size=100)
    backups.assert_awaited_once_with(factory, storage=storage, batch_size=100)
    invitation_event.assert_called_once()
    chat_event.assert_called_once()
    backup_event.assert_called_once()
    assert invitation_event.call_args.kwargs["error_type"] is None
    assert chat_event.call_args.kwargs["error_type"] is None
    assert backup_event.call_args.kwargs["error_type"] is None


@pytest.mark.anyio
async def test_maintenance_stops_after_failure_and_emits_only_safe_error_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_error = RuntimeError("database password")
    invitations = AsyncMock(side_effect=private_error)
    chat = AsyncMock()
    backups = AsyncMock()
    invitation_event = Mock()
    monkeypatch.setattr(maintenance, "process_invitation_expiry_batch", invitations)
    monkeypatch.setattr(maintenance, "process_chat_cleanup_batch", chat)
    monkeypatch.setattr(maintenance, "process_expired_semester_backup_batch", backups)
    monkeypatch.setattr(maintenance, "emit_invitation_expiry_event", invitation_event)

    with pytest.raises(RuntimeError, match="database password"):
        await maintenance.run_maintenance_batch(_factory(), storage=_storage())

    chat.assert_not_awaited()
    backups.assert_not_awaited()
    assert invitation_event.call_args_list == [
        call(
            batch_size=100,
            selected=0,
            expired=0,
            duration_ms=pytest.approx(invitation_event.call_args.kwargs["duration_ms"]),
            error_type="RuntimeError",
        )
    ]


@pytest.mark.anyio
async def test_partial_backup_cleanup_is_reported_as_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        maintenance,
        "process_invitation_expiry_batch",
        AsyncMock(return_value=InvitationExpiryReport(selected=0, expired=0)),
    )
    monkeypatch.setattr(
        maintenance,
        "process_chat_cleanup_batch",
        AsyncMock(return_value=ChatCleanupReport(selected=0, deleted=0)),
    )
    monkeypatch.setattr(
        maintenance,
        "process_expired_semester_backup_batch",
        AsyncMock(
            return_value=SemesterBackupExpiryReport(
                selected=1,
                expired=0,
                cleaned=0,
                failed=1,
            )
        ),
    )
    backup_event = Mock()
    monkeypatch.setattr(maintenance, "emit_semester_backup_expiry_event", backup_event)

    with pytest.raises(RuntimeError, match="could not be cleaned"):
        await maintenance.run_maintenance_batch(_factory(), storage=_storage())

    assert backup_event.call_args.kwargs["failed"] == 1
    assert backup_event.call_args.kwargs["error_type"] == "RuntimeError"
