"""OPS-001 liveness/readiness dependency reporting tests."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import RedisError
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.api.health as health_api
import app.services.infrastructure_health as health_service
from app.core.config import CorsSettings, get_cors_settings
from app.main import app
from app.services.infrastructure_health import InfrastructureReadiness

TRUSTED_ORIGIN = "https://localhost:5173"


@pytest.mark.anyio
async def test_liveness_does_not_call_dependency_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = AsyncMock(side_effect=AssertionError("dependency probe must not run"))
    monkeypatch.setattr(health_api, "check_infrastructure_readiness", readiness)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    readiness.assert_not_awaited()


def test_websocket_liveness_requires_exact_trusted_origin() -> None:
    app.dependency_overrides[get_cors_settings] = lambda: CorsSettings(
        allowed_origins=(TRUSTED_ORIGIN,)
    )
    try:
        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/health/ws", headers={"origin": TRUSTED_ORIGIN}
            ) as websocket:
                assert websocket.receive_json() == {"status": "alive"}
            with pytest.raises(WebSocketDisconnect) as denied:
                with client.websocket_connect(
                    "/api/health/ws", headers={"origin": "https://attacker.example"}
                ):
                    pass
            assert denied.value.code == 1008
    finally:
        app.dependency_overrides.pop(get_cors_settings, None)


@pytest.mark.anyio
async def test_readiness_reports_each_dependency_without_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health_api,
        "check_infrastructure_readiness",
        AsyncMock(
            return_value=InfrastructureReadiness(
                database="ok",
                redis="unavailable",
                email="configured",
                storage="unconfigured",
            )
        ),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {
            "database": "ok",
            "redis": "unavailable",
            "email": "configured",
            "storage": "unconfigured",
        },
    }
    assert "endpoint" not in response.text
    assert "credential" not in response.text


@pytest.mark.anyio
async def test_ready_requires_all_four_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health_api,
        "check_infrastructure_readiness",
        AsyncMock(
            return_value=InfrastructureReadiness(
                database="ok", redis="ok", email="configured", storage="configured"
            )
        ),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.anyio
async def test_redis_status_recovers_after_an_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = AsyncMock(side_effect=[RedisError("private redis diagnostics"), True])
    monkeypatch.setattr(health_service, "check_redis", check)

    assert await health_service._redis_status() == "unavailable"
    assert await health_service._redis_status() == "ok"
