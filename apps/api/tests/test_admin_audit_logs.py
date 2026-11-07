"""Authorization, SQL bounds, attribution and read-time projection regressions."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_audit_logs import _date_range
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ADMIN_A = UUID(int=1)
ADMIN_B = UUID(int=2)
EVENT = UUID(int=3)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def session() -> Iterator[MagicMock]:
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())
    settings = AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    yield session
    app.dependency_overrides.clear()


def cookies(session: MagicMock, role: UserRole) -> dict[str, str]:
    settings = get_auth_token_settings_for_test()
    session.scalar = AsyncMock(
        return_value=User(
            id=ADMIN_A,
            email="admin-a@example.com",
            role=role,
            is_active=True,
            email_verified=True,
        )
    )
    pair = create_token_pair(ADMIN_A, role, settings)
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token}


def get_auth_token_settings_for_test() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(bytes(range(32))), secure_cookies=False)


def row(admin_id: UUID, email: str | None, action: str, **values: object) -> SimpleNamespace:
    return SimpleNamespace(
        **(
            {
                "id": uuid4(),
                "created_at": datetime(2026, 11, 6, 17, tzinfo=UTC),
                "admin_id": admin_id,
                "email": email,
                "action": action,
                "category": "events",
                "resource_type": "event",
                "resource_id": EVENT,
                "before_status": None,
                "after_status": None,
                "before_version": None,
                "after_version": None,
            }
            | values
        )
    )


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["", "/actors"])
async def test_requires_admin(session: MagicMock, path: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        url = "/api/admin/audit-logs" + path
        assert (await client.get(url)).status_code == 401
        client.cookies.update(cookies(session, UserRole.USER))
        assert (await client.get(url)).status_code == 403
    session.execute.assert_not_awaited()


@pytest.mark.anyio
async def test_projection_filters_and_fixed_query_count(session: MagicMock) -> None:
    actor = cookies(session, UserRole.ADMIN)
    session.scalar.side_effect = [session.scalar.return_value, 25]
    session.execute.return_value.all.return_value = [
        row(
            ADMIN_A,
            "admin-a@example.com",
            "event.status_update",
            after_status="PUBLISHED",
            before_version="1",
            after_version="2",
        ),
        row(
            ADMIN_B,
            "admin-b@example.com",
            "event.update",
            before_status="<script>secret</script>",
            after_status="https://example.invalid/?token=x",
        ),
        row(
            ADMIN_B,
            None,
            "event.status_update",
            after_status="CANCELLED",
            before_version="2",
            after_version="2",
        ),
        row(ADMIN_A, "admin-a@example.com", "<script>private payload</script>"),
    ]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=actor,
    ) as client:
        res = await client.get(
            "/api/admin/audit-logs",
            params={
                "page": 2,
                "page_size": 5,
                "category": "events",
                "admin_id": str(ADMIN_A),
                "period": "custom",
                "start": "2026-11-07",
                "end": "2026-11-07",
            },
        )
    assert res.status_code == 200
    assert res.headers["cache-control"] == "private, no-store"
    assert res.json()["total_pages"] == 5
    first, second, noop, unknown = res.json()["items"]
    assert first["admin_email"] == "admin-a@example.com"
    assert second["admin_email"] == "admin-b@example.com"
    assert first["resource_id"] == second["resource_id"] == str(EVENT)
    assert first["action"] == "event.status_update.PUBLISHED"
    assert second["before_status"] is None and second["after_status"] is None
    assert noop["action"] == "event.status_update" and noop["admin_email"] is None
    assert unknown["action"] == "unknown" and unknown["category"] == "events"
    assert all(word not in res.text for word in ("script", "secret", "token", "metadata"))
    assert session.scalar.await_count == 2  # authentication and count
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
    )
    sql = str(stmt)
    assert "LEFT OUTER JOIN" in sql and "audit_logs.admin_id =" in sql
    assert "audit_logs.created_at >=" in sql and "audit_logs.created_at <" in sql
    assert "ORDER BY app_private.audit_logs.created_at DESC, app_private.audit_logs.id DESC" in sql
    assert "CASE" in sql and "LIMIT" in sql and "OFFSET" in sql
    assert ADMIN_A in stmt.params.values() and "events" in stmt.params.values()
    bounds = [
        value.astimezone(UTC) for value in stmt.params.values() if isinstance(value, datetime)
    ]
    assert bounds == [datetime(2026, 11, 6, 17, tzinfo=UTC), datetime(2026, 11, 7, 17, tzinfo=UTC)]
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.delete.assert_not_awaited()


@pytest.mark.anyio
async def test_actor_options_use_a_bounded_existence_query(session: MagicMock) -> None:
    actor = cookies(session, UserRole.ADMIN)
    session.execute.return_value.all.return_value = [
        SimpleNamespace(id=ADMIN_B, email="admin-b@example.com"),
    ]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=actor,
    ) as client:
        res = await client.get("/api/admin/audit-logs/actors")
        invalid = await client.get(
            "/api/admin/audit-logs?period=custom&start=2025-01-01&end=2026-11-07"
        )
    assert res.json() == {
        "items": [{"id": str(ADMIN_B), "email": "admin-b@example.com"}],
        "has_more": False,
    }
    assert invalid.status_code == 422
    session.execute.assert_awaited_once()
    stmt = session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
    )
    assert "EXISTS" in str(stmt) and 101 in stmt.params.values()
    assert "is_active" not in str(stmt)  # inactive recorded administrators remain selectable


@pytest.mark.parametrize(("period", "expected_day"), [("today", 7), ("week", 1), ("month", 9)])
def test_local_calendar_periods(period: str, expected_day: int) -> None:
    from typing import cast

    from app.api.admin_audit_logs import Period

    start, end = _date_range(cast(Period, period), None, None, date(2026, 11, 7))
    assert start.day == expected_day and end.day == 8
    assert start.hour == end.hour == 0
    assert start.utcoffset() == timedelta(hours=7)
