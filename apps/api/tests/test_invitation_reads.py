"""INV-004 visibility, projection, pagination, and privacy service tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.invitation_reads as reads
from app.models import (
    InvitationStatus,
    LanguageProficiency,
    MatchingInvitation,
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

NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
REFERENCE_WEEK = date(2026, 9, 28)
CURRENT_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
CURRENT_PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
PARTICIPANT_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
PARTICIPANT_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")
INTEREST_ID = UUID("40000000-0000-4000-8000-000000000001")
PHOTO_ID = UUID("50000000-0000-4000-8000-000000000001")


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
    user = User(
        id=CURRENT_USER_ID,
        email="private@example.com",
        password_hash="private-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )
    profile = StudentProfile(
        id=CURRENT_PROFILE_ID,
        user_id=CURRENT_USER_ID,
        full_name="Current User",
        display_name="Current",
        student_type=StudentType.VIETNAMESE,
        matching_opt_in=False,
    )
    return VerifiedBuddyPrincipal(user=user, profile=profile)


def _safe_profile(
    profile_id: UUID,
    *,
    student_type: StudentType,
    complete: bool = True,
) -> SafeInvitationProfile:
    return SafeInvitationProfile(
        id=profile_id,
        display_name="Alex",
        student_type=student_type,
        major="Computer Science",
        avatar=(SafeMatchingAvatar(id=PHOTO_ID, width=640, height=480) if complete else None),
        interests=(
            [
                SafeMatchingPreference(
                    id=INTEREST_ID,
                    code="music",
                    label="Music",
                    is_custom=False,
                )
            ]
            if complete
            else []
        ),
        languages=(
            [
                SafeMatchingLanguage(
                    code="en",
                    label="English",
                    proficiency=LanguageProficiency.FLUENT,
                    is_custom=False,
                )
            ]
            if complete
            else []
        ),
        activities=[],
        availability=None,
    )


def _row(
    *,
    status: InvitationStatus = InvitationStatus.PENDING,
    message: str | None = "Grüße 😀 <script>alert(1)</script>",
) -> reads._InvitationRow:
    return reads._InvitationRow(
        id=INVITATION_ID,
        status=status,
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
        participant_user_id=PARTICIPANT_USER_ID,
        message=message,
    )


def test_visibility_predicates_are_owner_scoped_and_effective_expiry_aware() -> None:
    dialect = make_url("postgresql+asyncpg://").get_dialect()()
    incoming = select(MatchingInvitation.id).where(
        *reads._visibility_conditions(
            "incoming",
            owner_user_id=CURRENT_USER_ID,
            at=NOW,
        )
    )
    sent = select(MatchingInvitation.id).where(
        *reads._visibility_conditions(
            "sent",
            owner_user_id=CURRENT_USER_ID,
            at=NOW,
        )
    )
    incoming_sql = str(incoming.compile(dialect=dialect)).upper()
    sent_compiled = sent.compile(dialect=dialect)
    sent_sql = str(sent_compiled).upper()

    assert "RECIPIENT_ID" in incoming_sql
    assert "STATUS" in incoming_sql
    assert "EXPIRES_AT >" in incoming_sql
    assert "SENDER_ID" in sent_sql
    assert "EXPIRES_AT >" in sent_sql
    assert InvitationStatus.ACCEPTED in sent_compiled.params.values()
    assert "SENDER_HIDDEN_AT IS NULL" in sent_sql
    for hidden_status in ("DECLINED", "EXPIRED", "CANCELLED"):
        assert hidden_status not in sent_sql


@pytest.mark.anyio
async def test_sent_page_query_is_bounded_deterministic_and_never_selects_message() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=1)
    mock.execute = AsyncMock(
        return_value=_TupleResult(
            [
                (
                    INVITATION_ID,
                    InvitationStatus.ACCEPTED,
                    NOW,
                    NOW + timedelta(days=7),
                    PARTICIPANT_USER_ID,
                )
            ]
        )
    )

    rows, total = await reads._list_invitation_rows(
        cast(AsyncSession, mock),
        view="sent",
        owner_user_id=CURRENT_USER_ID,
        page=2,
        page_size=20,
        at=NOW,
    )

    assert total == 1
    assert rows == (_row(status=InvitationStatus.ACCEPTED, message=None),)
    statement = mock.execute.await_args.args[0]
    sql = str(statement).upper()
    assert "ORDER BY" in sql
    assert "CREATED_AT DESC" in sql
    assert "ID DESC" in sql
    assert "LIMIT" in sql and "OFFSET" in sql
    assert "MESSAGE" not in sql


@pytest.mark.anyio
async def test_profile_projection_uses_fixed_batch_queries_and_safe_columns() -> None:
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock(
        side_effect=[
            _TupleResult(
                [
                    (
                        PARTICIPANT_USER_ID,
                        PARTICIPANT_PROFILE_ID,
                        "Alex",
                        StudentType.INTERNATIONAL,
                        "Computer Science",
                        None,
                        PHOTO_ID,
                        640,
                        480,
                    )
                ]
            ),
            _TupleResult(
                [
                    (
                        PARTICIPANT_PROFILE_ID,
                        INTEREST_ID,
                        "music",
                        "Music",
                        "Musik",
                    )
                ]
            ),
            _TupleResult(
                [
                    (
                        PARTICIPANT_PROFILE_ID,
                        "en",
                        "English",
                        "Englisch",
                        LanguageProficiency.FLUENT,
                    )
                ]
            ),
            _TupleResult([]),
            _TupleResult([]),
        ]
    )

    profiles = await reads.load_safe_participant_profiles(
        cast(AsyncSession, mock),
        (PARTICIPANT_USER_ID,),
        locale="de",
    )

    assert mock.execute.await_count == 5
    profile = profiles[PARTICIPANT_USER_ID]
    assert profile.id == PARTICIPANT_PROFILE_ID
    assert profile.interests[0].label == "Musik"
    assert profile.languages[0].label == "Englisch"
    statements = "\n".join(str(call.args[0]).lower() for call in mock.execute.await_args_list)
    for forbidden_column in (
        "users.email",
        "password_hash",
        "student_profiles.full_name",
        "normalized_key",
        "object_key",
        "bucket",
    ):
        assert forbidden_column not in statements


@pytest.mark.anyio
async def test_incoming_page_preserves_message_and_projects_current_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = _principal()
    current_profile = _safe_profile(
        CURRENT_PROFILE_ID,
        student_type=StudentType.VIETNAMESE,
    )
    sender_profile = _safe_profile(
        PARTICIPANT_PROFILE_ID,
        student_type=StudentType.INTERNATIONAL,
    )
    monkeypatch.setattr(
        reads,
        "_list_invitation_rows",
        AsyncMock(return_value=((_row(),), 21)),
    )
    load_profiles = AsyncMock(
        return_value={
            CURRENT_USER_ID: current_profile,
            PARTICIPANT_USER_ID: sender_profile,
        }
    )
    monkeypatch.setattr(reads, "load_safe_participant_profiles", load_profiles)
    session = MagicMock(spec=AsyncSession)

    result = await reads.list_incoming_invitations(
        cast(AsyncSession, session),
        principal,
        locale="en",
        page=2,
        page_size=20,
        reference_week_start=REFERENCE_WEEK,
        clock=lambda: NOW,
    )

    assert result.total == 21
    assert result.total_pages == 2
    assert len(result.items) == 1
    item = result.items[0]
    assert item.sender.id == PARTICIPANT_PROFILE_ID
    assert item.message == "Grüße 😀 <script>alert(1)</script>"
    assert item.score is not None
    assert item.explanation is not None
    load_profiles.assert_awaited_once_with(
        session,
        (CURRENT_USER_ID, PARTICIPANT_USER_ID),
        locale="en",
    )


@pytest.mark.anyio
async def test_sent_page_omits_message_and_keeps_incomplete_participant_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = _principal()
    current_profile = _safe_profile(
        CURRENT_PROFILE_ID,
        student_type=StudentType.VIETNAMESE,
    )
    recipient_profile = _safe_profile(
        PARTICIPANT_PROFILE_ID,
        student_type=StudentType.INTERNATIONAL,
        complete=False,
    )
    monkeypatch.setattr(
        reads,
        "_list_invitation_rows",
        AsyncMock(return_value=((_row(status=InvitationStatus.ACCEPTED, message=None),), 1)),
    )
    monkeypatch.setattr(
        reads,
        "load_safe_participant_profiles",
        AsyncMock(
            return_value={
                CURRENT_USER_ID: current_profile,
                PARTICIPANT_USER_ID: recipient_profile,
            }
        ),
    )

    result = await reads.list_sent_invitations(
        MagicMock(spec=AsyncSession),
        principal,
        locale="en",
        page=1,
        page_size=20,
        reference_week_start=REFERENCE_WEEK,
        clock=lambda: NOW,
    )

    assert result.items[0].status is InvitationStatus.ACCEPTED
    assert result.items[0].recipient.id == PARTICIPANT_PROFILE_ID
    assert result.items[0].score is None
    assert result.items[0].explanation is None
    assert "message" not in result.items[0].model_dump()


@pytest.mark.anyio
@pytest.mark.parametrize("view", ("incoming", "sent"))
async def test_empty_pages_do_not_issue_profile_queries(
    view: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reads,
        "_list_invitation_rows",
        AsyncMock(return_value=((), 0)),
    )
    load_profiles = AsyncMock()
    monkeypatch.setattr(reads, "load_safe_participant_profiles", load_profiles)
    function = (
        reads.list_incoming_invitations if view == "incoming" else reads.list_sent_invitations
    )

    result = await function(
        MagicMock(spec=AsyncSession),
        _principal(),
        locale="en",
        page=1,
        page_size=20,
        reference_week_start=REFERENCE_WEEK,
        clock=lambda: NOW,
    )

    assert result.items == []
    assert result.total == result.total_pages == 0
    load_profiles.assert_not_awaited()


@pytest.mark.parametrize(
    ("page", "page_size", "reference_week"),
    (
        (0, 20, REFERENCE_WEEK),
        (1, 0, REFERENCE_WEEK),
        (1, 51, REFERENCE_WEEK),
        (1, 20, date(2026, 9, 29)),
    ),
)
@pytest.mark.anyio
async def test_invalid_pagination_or_reference_week_is_rejected_before_query(
    page: int,
    page_size: int,
    reference_week: date,
) -> None:
    mock = MagicMock(spec=AsyncSession)

    with pytest.raises(ValueError):
        await reads.list_incoming_invitations(
            cast(AsyncSession, mock),
            _principal(),
            locale="en",
            page=page,
            page_size=page_size,
            reference_week_start=reference_week,
            clock=lambda: NOW,
        )

    mock.scalar.assert_not_called()
    mock.execute.assert_not_called()
