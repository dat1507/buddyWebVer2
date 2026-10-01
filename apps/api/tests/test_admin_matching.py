"""Aggregate, privacy, pagination, and query-shape tests for ADMIN matching."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.admin_matching as admin_matching_service
from app.models import StudentType
from app.schemas.matching import SafeInvitationProfile
from app.services.admin_matching import (
    get_admin_matching_participant_detail,
    get_admin_matching_stats,
    list_admin_matching_participants,
)

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
PROFILE_ID = UUID("22222222-2222-4222-8222-222222222222")
SECOND_PROFILE_ID = UUID("33333333-3333-4333-8333-333333333333")
AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _result(
    *, one: tuple[object, ...] | None = None, rows: list[tuple[object, ...]] | None = None
) -> MagicMock:
    result = MagicMock()
    tuples = result.tuples.return_value
    tuples.one.return_value = one
    tuples.one_or_none.return_value = one
    tuples.all.return_value = rows or []
    return result


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock()
    mock.scalar = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _compiled(statement: object) -> tuple[str, dict[str, object]]:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    compiled = statement.compile(dialect=dialect)  # type: ignore[attr-defined]
    return str(compiled), compiled.params


@pytest.mark.anyio
async def test_stats_use_effective_expiry_and_authoritative_active_relationships() -> None:
    mock, session = _session()
    mock.execute.side_effect = [
        _result(one=(5, 3, 2)),
        _result(one=(1, 2, 3, 4, 5)),
    ]
    mock.scalar.return_value = 2

    stats = await get_admin_matching_stats(session, clock=lambda: AT)

    assert stats.model_dump() == {
        "participant_count": 5,
        "verified_participant_count": 3,
        "active_match_count": 2,
        "zero_buddy_participant_count": 2,
        "invitations": {
            "pending": 1,
            "accepted": 2,
            "declined": 3,
            "cancelled": 4,
            "expired": 5,
        },
    }
    assert mock.execute.await_count == 2
    assert mock.scalar.await_count == 1

    participant_sql, _ = _compiled(mock.execute.await_args_list[0].args[0])
    invitation_sql, invitation_params = _compiled(mock.execute.await_args_list[1].args[0])
    match_sql, _ = _compiled(mock.scalar.await_args.args[0])
    assert "UNION ALL" in participant_sql
    assert "active_buddy_counts" in participant_sql
    assert "users.deleted_at IS NULL" in participant_sql
    assert "student_profiles.deleted_at IS NULL" in participant_sql
    assert "matching_invitations.expires_at >" in invitation_sql
    assert "matching_invitations.expires_at <=" in invitation_sql
    assert "matching_invitations.deleted_at IS NULL" in invitation_sql
    assert AT in invitation_params.values()
    assert "matches.status" in match_sql
    assert "matches.deleted_at IS NULL" in match_sql
    assert "matching_invitations.message" not in invitation_sql.partition("FROM")[0]


@pytest.mark.anyio
async def test_stats_reject_naive_operational_clock() -> None:
    _, session = _session()

    with pytest.raises(ValueError, match="timezone-aware"):
        await get_admin_matching_stats(session, clock=lambda: datetime(2026, 10, 1, 12, 0))


@pytest.mark.anyio
async def test_stats_return_explicit_zero_data_state() -> None:
    mock, session = _session()
    mock.execute.side_effect = [
        _result(one=(0, 0, 0)),
        _result(one=(0, 0, 0, 0, 0)),
    ]
    mock.scalar.return_value = 0

    stats = await get_admin_matching_stats(session, clock=lambda: AT)

    assert stats.model_dump() == {
        "participant_count": 0,
        "verified_participant_count": 0,
        "active_match_count": 0,
        "zero_buddy_participant_count": 0,
        "invitations": {
            "pending": 0,
            "accepted": 0,
            "declined": 0,
            "cancelled": 0,
            "expired": 0,
        },
    }


@pytest.mark.anyio
async def test_participant_page_is_bounded_filtered_and_has_batched_buddy_counts() -> None:
    mock, session = _session()
    mock.scalar.return_value = 2
    mock.execute.return_value = _result(
        rows=[
            (
                PROFILE_ID,
                "Ada",
                StudentType.INTERNATIONAL,
                True,
                AT,
                True,
                0,
            ),
            (
                SECOND_PROFILE_ID,
                None,
                StudentType.INTERNATIONAL,
                False,
                AT,
                False,
                0,
            ),
        ]
    )

    page = await list_admin_matching_participants(
        session,
        page=2,
        page_size=2,
        student_type=StudentType.INTERNATIONAL,
        verified=True,
        zero_buddies_only=True,
    )

    assert page.page == 2
    assert page.page_size == 2
    assert page.total == 2
    assert page.total_pages == 1
    assert [item.profile_id for item in page.items] == [PROFILE_ID, SECOND_PROFILE_ID]
    assert page.items[0].buddy_count == 0
    assert page.items[1].is_active is False
    assert mock.scalar.await_count == 1
    assert mock.execute.await_count == 1

    count_sql, _ = _compiled(mock.scalar.await_args.args[0])
    list_sql, params = _compiled(mock.execute.await_args.args[0])
    selected_columns = list_sql.partition("FROM")[0]
    assert "UNION ALL" in count_sql
    assert "active_buddy_counts" in list_sql
    assert "student_profiles.student_type" in list_sql
    assert "users.email_verified_at IS NOT NULL" in list_sql
    assert "coalesce" in list_sql.lower()
    assert (
        "ORDER BY app_private.student_profiles.created_at DESC, "
        "app_private.student_profiles.id DESC"
    ) in list_sql
    assert "LIMIT" in list_sql and "OFFSET" in list_sql
    assert StudentType.INTERNATIONAL in params.values()
    for forbidden in (
        "users.email,",
        "users.password_hash",
        "matching_invitations.message",
        "buddy_messages.body",
        "profile_photos.object_key",
    ):
        assert forbidden not in selected_columns


@pytest.mark.anyio
@pytest.mark.parametrize("page,page_size", [(0, 20), (1, 0), (1, 51)])
async def test_participant_page_rejects_unbounded_values(page: int, page_size: int) -> None:
    _, session = _session()

    with pytest.raises(ValueError):
        await list_admin_matching_participants(
            session,
            page=page,
            page_size=page_size,
            student_type=None,
            verified=None,
            zero_buddies_only=False,
        )


@pytest.mark.anyio
async def test_participant_detail_reuses_one_batched_safe_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    mock.execute.return_value = _result(one=(USER_ID, True, AT, True, 3))
    profile = SafeInvitationProfile(
        id=PROFILE_ID,
        display_name="Ada",
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=None,
        interests=[],
        languages=[],
        activities=[],
        availability=None,
    )
    loader = AsyncMock(return_value={USER_ID: profile})
    monkeypatch.setattr(admin_matching_service, "load_safe_participant_profiles", loader)

    detail = await get_admin_matching_participant_detail(
        session,
        profile_id=PROFILE_ID,
        locale="de",
    )

    assert detail is not None
    assert detail.profile.id == PROFILE_ID
    assert detail.buddy_count == 3
    assert detail.email_verified is True
    loader.assert_awaited_once_with(session, (USER_ID,), locale="de")
    assert mock.execute.await_count == 1
    sql, params = _compiled(mock.execute.await_args.args[0])
    assert PROFILE_ID in params.values()
    assert "users.deleted_at IS NULL" in sql
    assert "student_profiles.deleted_at IS NULL" in sql
    assert "users.email," not in sql.partition("FROM")[0]


@pytest.mark.anyio
async def test_participant_detail_excludes_missing_or_deleted_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    mock.execute.return_value = _result(one=None)
    loader = AsyncMock()
    monkeypatch.setattr(admin_matching_service, "load_safe_participant_profiles", loader)

    assert (
        await get_admin_matching_participant_detail(
            session,
            profile_id=PROFILE_ID,
            locale="en",
        )
        is None
    )
    loader.assert_not_awaited()
