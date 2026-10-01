"""BUDDY-002 owner filtering, snapshot projection, pagination, and privacy tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.current_buddies as buddies
from app.models import (
    LanguageProficiency,
    ProfilePhoto,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.schemas.matching import (
    SafeInvitationProfile,
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
)
from app.services.buddy_access import VerifiedBuddyPrincipal

NOW = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
CURRENT_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
CURRENT_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
FIRST_BUDDY_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
FIRST_BUDDY_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
SECOND_BUDDY_USER_ID = UUID("30000000-0000-4000-8000-000000000001")
SECOND_BUDDY_PROFILE_ID = UUID("30000000-0000-4000-8000-000000000002")
FIRST_MATCH_ID = UUID("40000000-0000-4000-8000-000000000001")
SECOND_MATCH_ID = UUID("40000000-0000-4000-8000-000000000002")
FIRST_CONVERSATION_ID = UUID("50000000-0000-4000-8000-000000000001")
SECOND_CONVERSATION_ID = UUID("50000000-0000-4000-8000-000000000002")
PHOTO_ID = UUID("60000000-0000-4000-8000-000000000001")
INTEREST_ID = UUID("70000000-0000-4000-8000-000000000001")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _TupleResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def tuples(self) -> _TupleResult:
        return self

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


def _principal() -> VerifiedBuddyPrincipal:
    return VerifiedBuddyPrincipal(
        user=User(
            id=CURRENT_USER_ID,
            email="private@example.invalid",
            password_hash="private-test-hash",
            role=UserRole.USER,
            is_active=True,
            email_verified=True,
            email_verified_at=NOW,
        ),
        profile=StudentProfile(
            id=CURRENT_PROFILE_ID,
            user_id=CURRENT_USER_ID,
            full_name="Private Current Name",
            student_type=StudentType.VIETNAMESE,
        ),
    )


def _profile(profile_id: UUID, display_name: str) -> SafeInvitationProfile:
    return SafeInvitationProfile(
        id=profile_id,
        display_name=display_name,
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=SafeMatchingAvatar(id=PHOTO_ID, width=640, height=480),
        interests=[
            SafeMatchingPreference(
                id=INTEREST_ID,
                code="music",
                label="Music",
                is_custom=False,
            )
        ],
        languages=[
            SafeMatchingLanguage(
                code="en",
                label="English",
                proficiency=LanguageProficiency.FLUENT,
                is_custom=False,
            )
        ],
        activities=[],
        availability=None,
    )


def _snapshot(*, interest_points: float = 40) -> dict[str, object]:
    return {
        "reference_week_start": "2026-09-28",
        "interests": {"similarity": 1.0, "weight": 40, "points": interest_points},
        "activities": {"similarity": 0.5, "weight": 35, "points": 17.5},
        "availability": {"similarity": 0.0, "weight": 15, "points": 0.0},
        "languages": {"similarity": 1.0, "weight": 5, "points": 5.0},
        "major": {"similarity": 0.0, "weight": 5, "points": 0.0},
    }


def _row(
    *,
    match_id: UUID = FIRST_MATCH_ID,
    first_user_id: UUID = CURRENT_USER_ID,
    second_user_id: UUID = FIRST_BUDDY_USER_ID,
    conversation_id: UUID | None = FIRST_CONVERSATION_ID,
    score_breakdown: dict[str, object] | None = None,
    score: int = 63,
) -> buddies._CurrentBuddyRow:
    return buddies._CurrentBuddyRow(
        match_id=match_id,
        participant_one_user_id=first_user_id,
        participant_two_user_id=second_user_id,
        score=score,
        score_breakdown=score_breakdown or _snapshot(),
        activated_at=NOW,
        conversation_id=conversation_id,
    )


@pytest.mark.anyio
async def test_match_page_query_is_owner_scoped_active_bounded_and_deterministic() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=1)
    mock.execute = AsyncMock(
        return_value=_TupleResult(
            [
                (
                    FIRST_MATCH_ID,
                    CURRENT_USER_ID,
                    FIRST_BUDDY_USER_ID,
                    63,
                    _snapshot(),
                    NOW,
                    FIRST_CONVERSATION_ID,
                )
            ]
        )
    )

    rows, total = await buddies._list_current_buddy_rows(
        cast(AsyncSession, mock),
        owner_user_id=CURRENT_USER_ID,
        page=2,
        page_size=20,
    )

    assert total == 1
    assert rows == (_row(),)
    statements = [mock.scalar.await_args.args[0], mock.execute.await_args.args[0]]
    rendered = "\n".join(str(statement).upper() for statement in statements)
    assert "MATCHES.PARTICIPANT_ONE_USER_ID" in rendered
    assert "MATCHES.PARTICIPANT_TWO_USER_ID" in rendered
    assert "MATCHES.STATUS" in rendered
    assert "MATCHES.DELETED_AT IS NULL" in rendered
    assert "BUDDY_CONVERSATIONS" in rendered
    assert "ACTIVATED_AT DESC" in rendered and "MATCHES.ID DESC" in rendered
    assert "LIMIT" in rendered and "OFFSET" in rendered
    for forbidden in ("MATCHING_INVITATIONS", "MESSAGE", "EMAIL", "PASSWORD_HASH"):
        assert forbidden not in rendered


@pytest.mark.anyio
async def test_multiple_buddies_select_correct_other_participant_and_persisted_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = (
        _row(),
        _row(
            match_id=SECOND_MATCH_ID,
            first_user_id=SECOND_BUDDY_USER_ID,
            second_user_id=CURRENT_USER_ID,
            conversation_id=SECOND_CONVERSATION_ID,
            score_breakdown=_snapshot(interest_points=20),
            score=43,
        ),
    )
    list_rows = AsyncMock(return_value=(rows, 2))
    load_profiles = AsyncMock(
        return_value={
            FIRST_BUDDY_USER_ID: _profile(FIRST_BUDDY_PROFILE_ID, "First Buddy"),
            SECOND_BUDDY_USER_ID: _profile(SECOND_BUDDY_PROFILE_ID, "Second Buddy"),
        }
    )
    monkeypatch.setattr(buddies, "_list_current_buddy_rows", list_rows)
    monkeypatch.setattr(buddies, "load_safe_participant_profiles", load_profiles)
    session = MagicMock(spec=AsyncSession)

    result = await buddies.list_current_buddies(
        cast(AsyncSession, session),
        _principal(),
        locale="de",
        page=1,
        page_size=20,
    )

    assert result.total == 2
    assert result.total_pages == 1
    assert [item.match_id for item in result.items] == [FIRST_MATCH_ID, SECOND_MATCH_ID]
    assert [item.conversation_id for item in result.items] == [
        FIRST_CONVERSATION_ID,
        SECOND_CONVERSATION_ID,
    ]
    assert [item.buddy.id for item in result.items] == [
        FIRST_BUDDY_PROFILE_ID,
        SECOND_BUDDY_PROFILE_ID,
    ]
    assert [item.score for item in result.items] == [63, 43]
    assert result.items[1].explanation.interests.points == 20
    assert result.items[1].reference_week_start == date(2026, 9, 28)
    list_rows.assert_awaited_once_with(
        session,
        owner_user_id=CURRENT_USER_ID,
        page=1,
        page_size=20,
    )
    load_profiles.assert_awaited_once_with(
        session,
        (FIRST_BUDDY_USER_ID, SECOND_BUDDY_USER_ID),
        locale="de",
    )


@pytest.mark.anyio
async def test_zero_buddies_avoids_profile_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        buddies,
        "_list_current_buddy_rows",
        AsyncMock(return_value=((), 0)),
    )
    load_profiles = AsyncMock()
    monkeypatch.setattr(buddies, "load_safe_participant_profiles", load_profiles)

    result = await buddies.list_current_buddies(
        MagicMock(spec=AsyncSession),
        _principal(),
        locale="en",
        page=1,
        page_size=20,
    )

    assert result.items == []
    assert result.total == result.total_pages == 0
    load_profiles.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("row", "profiles"),
    (
        (_row(conversation_id=None), {FIRST_BUDDY_USER_ID: _profile(FIRST_BUDDY_PROFILE_ID, "A")}),
        (_row(), {}),
        (
            _row(score_breakdown={"reference_week_start": "2026-09-28"}),
            {FIRST_BUDDY_USER_ID: _profile(FIRST_BUDDY_PROFILE_ID, "A")},
        ),
    ),
)
async def test_incomplete_or_malformed_authoritative_state_fails_closed(
    row: buddies._CurrentBuddyRow,
    profiles: dict[UUID, SafeInvitationProfile],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        buddies,
        "_list_current_buddy_rows",
        AsyncMock(return_value=((row,), 1)),
    )
    monkeypatch.setattr(
        buddies,
        "load_safe_participant_profiles",
        AsyncMock(return_value=profiles),
    )

    with pytest.raises(buddies.CurrentBuddyReadStateError):
        await buddies.list_current_buddies(
            MagicMock(spec=AsyncSession),
            _principal(),
            locale="en",
            page=1,
            page_size=20,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(("page", "page_size"), ((0, 20), (1, 0), (1, 51)))
async def test_invalid_pagination_is_rejected_before_query(page: int, page_size: int) -> None:
    session = MagicMock(spec=AsyncSession)

    with pytest.raises(ValueError):
        await buddies.list_current_buddies(
            cast(AsyncSession, session),
            _principal(),
            locale="en",
            page=page,
            page_size=page_size,
        )

    session.scalar.assert_not_called()
    session.execute.assert_not_called()


@pytest.mark.anyio
async def test_active_buddy_avatar_query_uses_exact_profile_side_of_owned_match() -> None:
    photo = ProfilePhoto(id=PHOTO_ID, profile_id=FIRST_BUDDY_PROFILE_ID)
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=photo)

    result = await buddies.get_active_buddy_avatar(
        cast(AsyncSession, mock),
        _principal(),
        PHOTO_ID,
    )

    assert result is photo
    statement = mock.scalar.await_args.args[0]
    compiled = statement.compile(dialect=make_url("postgresql+asyncpg://").get_dialect()())
    rendered = str(compiled).upper()
    assert "MATCHES.PARTICIPANT_ONE_USER_ID" in rendered
    assert "MATCHES.PARTICIPANT_TWO_USER_ID" in rendered
    assert "MATCHES.PARTICIPANT_ONE_PROFILE_ID" in rendered
    assert "MATCHES.PARTICIPANT_TWO_PROFILE_ID" in rendered
    assert "MATCHES.STATUS" in rendered
    assert CURRENT_USER_ID in compiled.params.values()
    assert PHOTO_ID in compiled.params.values()
    for forbidden in ("USERS.EMAIL", "PASSWORD_HASH", "MATCHING_INVITATIONS"):
        assert forbidden not in rendered
