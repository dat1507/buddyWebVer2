"""Read-only Admin aggregate regressions."""

from collections.abc import Callable
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_statistics import count_admin_events, count_admin_users


@pytest.mark.anyio
async def test_aggregate_predicates() -> None:
    dialect_factory = cast(Callable[[], Dialect], PGDialect)
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=7)
    assert (await count_admin_users(cast(AsyncSession, session))).total_users == 7
    sql = str(
        session.scalar.call_args.args[0].compile(
            dialect=dialect_factory(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "'USER'" in sql and "deleted_at IS NULL" in sql
    assert "is_active" not in sql and "JOIN" not in sql and "semester" not in sql
    rows = MagicMock()
    rows.one.return_value = (4, 2)
    session.execute = AsyncMock(return_value=rows)
    result = await count_admin_events(cast(AsyncSession, session))
    assert (result.published_events, result.upcoming_events) == (4, 2)
    sql = str(
        session.execute.call_args.args[0].compile(
            dialect=dialect_factory(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "'PUBLISHED'" in sql and "published_at IS NOT NULL" in sql
    assert "deleted_at IS NULL" in sql and "start_date >" in sql
    assert "visibility" not in sql and "LIMIT" not in sql
    session.commit.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["users", "events"])
async def test_guard_and_private_counts(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime

    from httpx2 import ASGITransport, AsyncClient
    from test_admin_events_api import _actor, _install, _session

    import app.api.admin_events as events
    import app.api.admin_users as users
    from app.main import app
    from app.models import UserRole
    from app.schemas.admin_statistics import AdminEventStatistics, AdminUserStatistics

    observed_at = datetime.now(UTC)
    value = (
        AdminUserStatistics(total_users=0, observed_at=observed_at)
        if path == "users"
        else AdminEventStatistics(published_events=0, upcoming_events=0, observed_at=observed_at)
    )
    service = AsyncMock(return_value=value)
    monkeypatch.setattr(
        users if path == "users" else events,
        "count_admin_users" if path == "users" else "count_admin_events",
        service,
    )
    _, initial_session = _session(_actor())
    _install(initial_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            assert (await client.get(f"/api/admin/{path}/stats")).status_code == 401
            _, session = _session(_actor(role=UserRole.USER))
            cookies, _ = _install(session, role=UserRole.USER)
            client.cookies.update(cookies)
            assert (await client.get(f"/api/admin/{path}/stats")).status_code == 403
            _, session = _session(_actor())
            cookies, _ = _install(session)
            client.cookies.update(cookies)
            response = await client.get(f"/api/admin/{path}/stats")
            assert response.status_code == 200
            assert "no-store" in response.headers["cache-control"]
            service.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_real_counts_on_isolated_sqlite() -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import create_engine

    from app.models import Event, User

    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        schema = User.__table__.schema
        if schema:
            connection.exec_driver_sql(f"ATTACH DATABASE ':memory:' AS {schema}")
        users = f"{schema}." if schema else ""
        users += User.__tablename__
        events = f"{schema}." if schema else ""
        events += Event.__tablename__
        connection.exec_driver_sql(f"CREATE TABLE {users} (id TEXT, role TEXT, deleted_at TEXT)")
        connection.exec_driver_sql(
            f"INSERT INTO {users} VALUES ('1','USER',NULL), ('2','ADMIN',NULL), ('3','USER','deleted'), ('4','USER',NULL)"
        )
        connection.exec_driver_sql(
            f"CREATE TABLE {events} (id TEXT, status TEXT, published_at DATETIME, deleted_at DATETIME, start_date DATETIME)"
        )
        now = datetime.now(UTC)
        for i, status, published, deleted, start in [
            (1, "PUBLISHED", now, None, now + timedelta(days=1)),
            (2, "PUBLISHED", now, None, now - timedelta(days=1)),
            (3, "PUBLISHED", now, None, None),
            (4, "DRAFT", None, None, now + timedelta(days=1)),
            (5, "CANCELLED", now, None, now + timedelta(days=1)),
            (6, "PUBLISHED", now, now, now + timedelta(days=1)),
            (7, "PUBLISHED", None, None, now + timedelta(days=1)),
        ]:
            connection.exec_driver_sql(
                f"INSERT INTO {events} VALUES (?,?,?,?,?)",
                (str(i), status, published, deleted, start),
            )
        session = MagicMock(spec=AsyncSession)
        session.scalar = AsyncMock(side_effect=connection.scalar)
        session.execute = AsyncMock(side_effect=connection.execute)
        assert (await count_admin_users(cast(AsyncSession, session))).total_users == 2
        result = await count_admin_events(cast(AsyncSession, session))
        assert (result.published_events, result.upcoming_events) == (3, 1)
    engine.dispose()
