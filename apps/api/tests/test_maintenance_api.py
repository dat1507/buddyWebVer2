"""Private scheduled-maintenance authentication and response contract tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes

import app.api.maintenance as maintenance_api
from app.core.config import (
    MAINTENANCE_WORKER_CRON_SECRET_VARIABLE,
    MaintenanceConfigurationError,
    MaintenanceWorkerSettings,
    get_maintenance_worker_settings,
)
from app.main import app
from app.services.chat_cleanup import ChatCleanupReport
from app.services.invitation_expiry import InvitationExpiryReport
from app.services.maintenance import MaintenanceReport
from app.services.semester_backup_verification import SemesterBackupExpiryReport

CRON_SECRET = "maintenance-secret-that-is-long-enough"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> MaintenanceWorkerSettings:
    return MaintenanceWorkerSettings(cron_secret=SecretBytes(CRON_SECRET.encode()))


def _report() -> MaintenanceReport:
    return MaintenanceReport(
        invitation_expiry=InvitationExpiryReport(selected=2, expired=2),
        chat_cleanup=ChatCleanupReport(selected=3, deleted=3),
        semester_backup_expiry=SemesterBackupExpiryReport(
            selected=1,
            expired=1,
            cleaned=1,
            failed=0,
        ),
    )


@pytest.mark.anyio
async def test_maintenance_requires_exact_cron_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = AsyncMock()
    monkeypatch.setattr(maintenance_api, "get_maintenance_worker_settings", _settings)
    monkeypatch.setattr(maintenance_api, "run_maintenance_batch", worker)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        missing = await client.post("/api/internal/maintenance")
        wrong = await client.post(
            "/api/internal/maintenance",
            headers={"x-cron-secret": "not-the-private-secret"},
        )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json() == wrong.json() == {"error": "unauthorized"}
    assert missing.headers["cache-control"] == "no-store"
    worker.assert_not_awaited()


@pytest.mark.anyio
async def test_maintenance_returns_only_safe_aggregate_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = object()
    storage_settings = object()
    storage = object()
    worker = AsyncMock(return_value=_report())
    monkeypatch.setattr(maintenance_api, "get_maintenance_worker_settings", _settings)
    monkeypatch.setattr(maintenance_api, "get_session_factory", Mock(return_value=factory))
    monkeypatch.setattr(
        maintenance_api,
        "get_storage_settings",
        Mock(return_value=storage_settings),
    )
    storage_adapter = Mock(return_value=storage)
    monkeypatch.setattr(maintenance_api, "SupabaseDatabaseBackupStore", storage_adapter)
    monkeypatch.setattr(maintenance_api, "run_maintenance_batch", worker)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/internal/maintenance",
            headers={"x-cron-secret": CRON_SECRET},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "batch_size": 100,
        "invitation_expiry": {"selected": 2, "expired": 2},
        "chat_cleanup": {"selected": 3, "deleted": 3},
        "semester_backup_expiry": {
            "selected": 1,
            "expired": 1,
            "cleaned": 1,
            "failed": 0,
        },
    }
    assert response.headers["cache-control"] == "no-store"
    assert CRON_SECRET not in response.text
    storage_adapter.assert_called_once_with(storage_settings)
    worker.assert_awaited_once_with(factory, storage=storage)


@pytest.mark.anyio
async def test_maintenance_sanitizes_configuration_and_worker_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_settings() -> MaintenanceWorkerSettings:
        raise MaintenanceConfigurationError("private configuration detail")

    monkeypatch.setattr(
        maintenance_api,
        "get_maintenance_worker_settings",
        missing_settings,
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        missing = await client.post("/api/internal/maintenance")

    assert missing.status_code == 503
    assert missing.json() == {"error": "maintenance_configuration_unavailable"}
    assert "private configuration detail" not in missing.text

    monkeypatch.setattr(maintenance_api, "get_maintenance_worker_settings", _settings)
    monkeypatch.setattr(maintenance_api, "get_session_factory", Mock(return_value=object()))
    monkeypatch.setattr(maintenance_api, "get_storage_settings", Mock(return_value=object()))
    monkeypatch.setattr(maintenance_api, "SupabaseDatabaseBackupStore", Mock(return_value=object()))
    monkeypatch.setattr(
        maintenance_api,
        "run_maintenance_batch",
        AsyncMock(side_effect=RuntimeError("database password and storage key")),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        failed = await client.post(
            "/api/internal/maintenance",
            headers={"x-cron-secret": CRON_SECRET},
        )

    assert failed.status_code == 503
    assert failed.json() == {"error": "maintenance_unavailable"}
    assert "database password" not in failed.text
    assert "storage key" not in failed.text


def test_maintenance_secret_loader_is_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    get_maintenance_worker_settings.cache_clear()
    monkeypatch.delenv(MAINTENANCE_WORKER_CRON_SECRET_VARIABLE, raising=False)
    with pytest.raises(MaintenanceConfigurationError):
        get_maintenance_worker_settings()

    get_maintenance_worker_settings.cache_clear()
    monkeypatch.setenv(MAINTENANCE_WORKER_CRON_SECRET_VARIABLE, "too-short")
    with pytest.raises(MaintenanceConfigurationError):
        get_maintenance_worker_settings()

    get_maintenance_worker_settings.cache_clear()
    monkeypatch.setenv(MAINTENANCE_WORKER_CRON_SECRET_VARIABLE, CRON_SECRET)
    settings = get_maintenance_worker_settings()
    assert settings.cron_secret.get_secret_value() == CRON_SECRET.encode()
    assert CRON_SECRET not in repr(settings)
    get_maintenance_worker_settings.cache_clear()


@pytest.mark.anyio
async def test_maintenance_route_is_not_advertised_in_openapi() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/openapi.json")

    assert "/api/internal/maintenance" not in response.json()["paths"]
