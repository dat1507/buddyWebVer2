"""Query projection tests for coordinator-facing student reads."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentType, UserRole
from app.services.admin_users import get_admin_user_detail, list_admin_users

USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
CREATED_AT = datetime(2026, 9, 20, 8, 30, tzinfo=UTC)


def _session_with_rows(
    rows: list[tuple[object, ...]],
    *,
    total: int = 0,
    one: bool = False,
) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=total)
    tuple_result = MagicMock()
    if one:
        tuple_result.one_or_none.return_value = rows[0] if rows else None
    else:
        tuple_result.all.return_value = rows
    result = MagicMock()
    result.tuples.return_value = tuple_result
    mock.execute = AsyncMock(return_value=result)
    return mock, cast(AsyncSession, mock)


def _compiled(statement: object) -> tuple[str, dict[str, object]]:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    compiled = statement.compile(dialect=dialect)  # type: ignore[attr-defined]
    return str(compiled), compiled.params


@pytest.mark.anyio
async def test_list_uses_allowlisted_projection_stable_paging_and_literal_search() -> None:
    row = (
        USER_ID,
        "student@example.com",
        UserRole.USER,
        True,
        True,
        CREATED_AT,
        PROFILE_ID,
        "Ada Student",
        "Ada",
        StudentType.INTERNATIONAL,
    )
    mock, session = _session_with_rows([row], total=6)

    result = await list_admin_users(
        session,
        page=2,
        page_size=5,
        search=r" 100%_buddy ",
    )

    assert result.page == 2
    assert result.page_size == 5
    assert result.total == 6
    assert result.total_pages == 2
    assert result.items[0].profile is not None
    assert result.items[0].profile.display_name == "Ada"

    count_sql, count_params = _compiled(mock.scalar.await_args.args[0])
    list_sql, list_params = _compiled(mock.execute.await_args.args[0])
    selected_columns = list_sql.partition("FROM")[0]
    for forbidden in (
        "password_hash",
        "last_login",
        "availability",
        "preferences",
        "object_key",
        "profile_photos",
    ):
        assert forbidden not in selected_columns
    assert "users.role" in count_sql
    assert "users.deleted_at IS NULL" in list_sql
    assert "student_profiles.deleted_at IS NULL" in list_sql
    assert "ORDER BY" in list_sql
    assert "LIMIT" in list_sql and "OFFSET" in list_sql
    expected_pattern = r"%100\%\_buddy%"
    assert expected_pattern in count_params.values()
    assert expected_pattern in list_params.values()


@pytest.mark.anyio
async def test_detail_excludes_matching_inputs_storage_and_credentials() -> None:
    row = (
        USER_ID,
        "student@example.com",
        UserRole.USER,
        True,
        True,
        CREATED_AT,
        PROFILE_ID,
        "Ada Student",
        "Ada",
        StudentType.INTERNATIONAL,
        "German",
        "Computer Science",
        2,
        "Buddy profile",
        "Example University",
        date(2026, 9, 1),
        date(2027, 2, 28),
        True,
        CREATED_AT,
    )
    mock, session = _session_with_rows([row], one=True)

    result = await get_admin_user_detail(session, USER_ID)

    assert result is not None
    assert result.id == USER_ID
    assert result.profile is not None
    assert result.profile.home_university == "Example University"
    sql, params = _compiled(mock.execute.await_args.args[0])
    selected_columns = sql.partition("FROM")[0]
    for forbidden in (
        "password_hash",
        "last_login",
        "availability",
        "preferences",
        "object_key",
        "profile_photos",
    ):
        assert forbidden not in selected_columns
    assert USER_ID in params.values()
    assert "users.role" in sql
    assert "users.deleted_at IS NULL" in sql


@pytest.mark.anyio
async def test_detail_returns_none_for_unknown_or_ineligible_account() -> None:
    _, session = _session_with_rows([], one=True)

    assert await get_admin_user_detail(session, USER_ID) is None
