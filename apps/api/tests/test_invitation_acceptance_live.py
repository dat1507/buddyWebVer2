"""INV-005 atomic/concurrency acceptance on isolated loopback PostgreSQL.

Set INV005_TEST_DATABASE_URL to the disposable ``inv005_runner`` role in a
loopback-only database named ``inv005_acceptance``. Never target shared data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.services.invitation_acceptance as acceptance
from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import (
    BuddyConversation,
    BuddyMatch,
    InvitationStatus,
    MatchingInvitation,
    StudentProfile,
    StudentType,
    TransactionalOutbox,
    User,
)
from app.schemas import ProfileUpdate
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_acceptance import (
    MATCHING_INVITATION_ACCEPTED,
    InvitationAcceptanceResult,
    InvitationAcceptError,
    InvitationAcceptReason,
    accept_matching_invitation,
)
from app.services.invitation_expiry import expire_invitation_batch
from app.services.invitation_reads import list_incoming_invitations, list_sent_invitations
from app.services.matching_recommendations import current_reference_week_start
from app.services.profiles import (
    ProfileUpdateConflictError,
    ProfileUpdateConflictReason,
    update_own_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_eligible_participants(
    engine: AsyncEngine,
    *,
    count: int,
) -> tuple[list[UUID], list[UUID]]:
    user_ids = [uuid4() for _ in range(count)]
    profile_ids = [uuid4() for _ in range(count)]
    async with engine.begin() as connection:
        interest_id = await connection.scalar(
            text("SELECT id FROM app_private.interests WHERE code = 'travel'")
        )
        assert isinstance(interest_id, UUID)
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, email_verified, email_verified_at) "
                "VALUES (:id, :email, 'test-only-hash', true, :verified_at)"
            ),
            [
                {
                    "id": user_id,
                    "email": f"inv005-{user_id}@example.invalid",
                    "verified_at": NOW,
                }
                for user_id in user_ids
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, display_name, student_type, matching_opt_in) "
                "VALUES (:id, :user_id, :full_name, :display_name, :student_type, true)"
            ),
            [
                {
                    "id": profile_ids[index],
                    "user_id": user_id,
                    "full_name": f"INV-005 participant {index}",
                    "display_name": f"Participant {index}",
                    "student_type": (
                        StudentType.VIETNAMESE.value
                        if index % 2 == 0
                        else StudentType.INTERNATIONAL.value
                    ),
                }
                for index, user_id in enumerate(user_ids)
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_interests (profile_id, interest_id) "
                "VALUES (:profile_id, :interest_id)"
            ),
            [{"profile_id": profile_id, "interest_id": interest_id} for profile_id in profile_ids],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_languages "
                "(profile_id, language_code, proficiency) "
                "VALUES (:profile_id, 'en', 'fluent')"
            ),
            [{"profile_id": profile_id} for profile_id in profile_ids],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_photos "
                "(profile_id, object_key, mime_type, byte_size, width, height, is_avatar) "
                "VALUES (:profile_id, :object_key, 'image/jpeg', 128, 64, 64, true)"
            ),
            [
                {"profile_id": profile_id, "object_key": f"inv005/{profile_id}.jpg"}
                for profile_id in profile_ids
            ],
        )
    return user_ids, profile_ids


async def _insert_invitation(
    engine: AsyncEngine,
    *,
    invitation_id: UUID,
    sender_id: UUID,
    recipient_id: UUID,
    created_at: datetime,
    status: InvitationStatus = InvitationStatus.PENDING,
) -> None:
    responded_at = NOW if status is InvitationStatus.ACCEPTED else None
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, 'Private acceptance fixture', :status, "
                ":created_at, :updated_at, :expires_at, :responded_at)"
            ),
            {
                "id": invitation_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "status": status.value,
                "created_at": created_at,
                "updated_at": responded_at or created_at,
                "expires_at": created_at + timedelta(days=7),
                "responded_at": responded_at,
            },
        )


async def _insert_existing_relationship(
    engine: AsyncEngine,
    *,
    invitation_id: UUID,
    sender_id: UUID,
    recipient_id: UUID,
    sender_profile_id: UUID,
    recipient_profile_id: UUID,
) -> None:
    await _insert_invitation(
        engine,
        invitation_id=invitation_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        created_at=NOW - timedelta(hours=2),
        status=InvitationStatus.ACCEPTED,
    )
    match_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matches "
                "(id, participant_one_user_id, participant_two_user_id, "
                "participant_one_profile_id, participant_two_profile_id, status, "
                "accepted_invitation_id, score, score_breakdown, activated_at, "
                "created_at, updated_at) VALUES "
                "(:id, :sender_id, :recipient_id, :sender_profile_id, "
                ":recipient_profile_id, 'ACTIVE', :invitation_id, 50, '{}'::jsonb, "
                ":activated_at, :activated_at, :activated_at)"
            ),
            {
                "id": match_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "sender_profile_id": sender_profile_id,
                "recipient_profile_id": recipient_profile_id,
                "invitation_id": invitation_id,
                "activated_at": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_conversations "
                "(match_id, created_at) VALUES (:match_id, :created_at)"
            ),
            {"match_id": match_id, "created_at": NOW},
        )


async def _principal(
    session: AsyncSession,
    user_id: UUID,
) -> VerifiedBuddyPrincipal:
    user = cast(User | None, await session.scalar(select(User).where(User.id == user_id)))
    profile = cast(
        StudentProfile | None,
        await session.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id)),
    )
    assert user is not None and profile is not None
    return VerifiedBuddyPrincipal(user=user, profile=profile)


async def _accept(
    factory: async_sessionmaker[AsyncSession],
    invitation_id: UUID,
    recipient_id: UUID,
    *,
    at: datetime = NOW,
) -> tuple[str, InvitationAcceptanceResult | None]:
    async with factory() as session:
        current = await _principal(session, recipient_id)
        try:
            result = await accept_matching_invitation(
                session,
                current,
                invitation_id=invitation_id,
                clock=lambda: at,
            )
            await session.commit()
            return "ACCEPTED", result
        except InvitationAcceptError as error:
            await session.rollback()
            return error.reason.value, None


async def _change_type(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
) -> str:
    async with factory() as session:
        owner = cast(User | None, await session.scalar(select(User).where(User.id == user_id)))
        assert owner is not None
        try:
            await update_own_profile(
                session,
                owner,
                ProfileUpdate(version=1, student_type=StudentType.INTERNATIONAL),
            )
            await session.commit()
            return "UPDATED"
        except ProfileUpdateConflictError as error:
            await session.rollback()
            return error.reason.value


async def _expire(
    factory: async_sessionmaker[AsyncSession],
    *,
    at: datetime,
) -> tuple[UUID, ...]:
    async with factory() as session:
        ids = await expire_invitation_batch(session, batch_size=100, clock=lambda: at)
        await session.commit()
        return ids


async def _assert_blocked(task: asyncio.Task[object]) -> None:
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout=0.25)


async def _assert_acceptance_contract(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        user_ids, profile_ids = await _seed_eligible_participants(engine, count=22)
        invitation_ids = [uuid4() for _ in range(12)]
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[0],
            sender_id=user_ids[0],
            recipient_id=user_ids[1],
            created_at=NOW - timedelta(hours=1),
        )
        concurrent = await asyncio.gather(
            _accept(factory, invitation_ids[0], user_ids[1]),
            _accept(factory, invitation_ids[0], user_ids[1]),
        )
        assert [item[0] for item in concurrent] == ["ACCEPTED", "ACCEPTED"]
        receipts = [item[1] for item in concurrent]
        assert receipts[0] is not None and receipts[1] is not None
        assert receipts[0] == receipts[1]

        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(BuddyMatch)) == 1
            assert await session.scalar(select(func.count()).select_from(BuddyConversation)) == 1
            accepted_events = tuple(
                (
                    await session.scalars(
                        select(TransactionalOutbox).where(
                            TransactionalOutbox.event_type == MATCHING_INVITATION_ACCEPTED,
                            TransactionalOutbox.aggregate_id == invitation_ids[0],
                        )
                    )
                ).all()
            )
            assert len(accepted_events) == 1
            assert set(accepted_events[0].payload) == {
                "invitation_id",
                "match_id",
                "conversation_id",
            }
            assert "message" not in accepted_events[0].payload
            pending_count = await session.scalar(
                select(func.count(MatchingInvitation.id)).where(
                    MatchingInvitation.sender_id == user_ids[0],
                    MatchingInvitation.status == InvitationStatus.PENDING,
                )
            )
            assert pending_count == 0
            recipient = await _principal(session, user_ids[1])
            sender = await _principal(session, user_ids[0])
            incoming = await list_incoming_invitations(
                session,
                recipient,
                locale="en",
                page=1,
                page_size=20,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW,
            )
            sent = await list_sent_invitations(
                session,
                sender,
                locale="en",
                page=1,
                page_size=20,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW,
            )
            assert incoming.items == []
            assert [item.id for item in sent.items] == [invitation_ids[0]]
            assert sent.items[0].status is InvitationStatus.ACCEPTED

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[1],
            sender_id=user_ids[2],
            recipient_id=user_ids[3],
            created_at=NOW - timedelta(days=7),
        )
        assert await _accept(factory, invitation_ids[1], user_ids[3]) == (
            InvitationAcceptReason.EXPIRED.value,
            None,
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[2],
            sender_id=user_ids[4],
            recipient_id=user_ids[5],
            created_at=NOW - timedelta(minutes=30),
        )
        await _insert_existing_relationship(
            engine,
            invitation_id=invitation_ids[3],
            sender_id=user_ids[4],
            recipient_id=user_ids[5],
            sender_profile_id=profile_ids[4],
            recipient_profile_id=profile_ids[5],
        )
        assert await _accept(factory, invitation_ids[2], user_ids[5]) == (
            InvitationAcceptReason.ACTIVE_PAIR_EXISTS.value,
            None,
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[4],
            sender_id=user_ids[6],
            recipient_id=user_ids[7],
            created_at=NOW - timedelta(minutes=20),
        )
        async with factory() as profile_winner:
            owner = cast(
                User | None,
                await profile_winner.scalar(select(User).where(User.id == user_ids[6])),
            )
            assert owner is not None
            await update_own_profile(
                profile_winner,
                owner,
                ProfileUpdate(version=1, student_type=StudentType.INTERNATIONAL),
            )
            accept_task = asyncio.create_task(_accept(factory, invitation_ids[4], user_ids[7]))
            await _assert_blocked(cast(asyncio.Task[object], accept_task))
            await profile_winner.commit()
        assert await asyncio.wait_for(accept_task, timeout=5) == (
            InvitationAcceptReason.OPPOSITE_TYPES_REQUIRED.value,
            None,
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[5],
            sender_id=user_ids[8],
            recipient_id=user_ids[9],
            created_at=NOW - timedelta(minutes=15),
        )
        async with factory() as accept_winner:
            current = await _principal(accept_winner, user_ids[9])
            await accept_matching_invitation(
                accept_winner,
                current,
                invitation_id=invitation_ids[5],
                clock=lambda: NOW,
            )
            update_task = asyncio.create_task(_change_type(factory, user_ids[8]))
            await _assert_blocked(cast(asyncio.Task[object], update_task))
            await accept_winner.commit()
        assert await asyncio.wait_for(update_task, timeout=5) == (
            ProfileUpdateConflictReason.STUDENT_TYPE_LOCKED_ACTIVE_MATCH.value
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[6],
            sender_id=user_ids[10],
            recipient_id=user_ids[11],
            created_at=NOW - timedelta(minutes=10),
        )
        with monkeypatch.context() as patcher:
            patcher.setattr(
                acceptance,
                "get_or_create_buddy_conversation",
                AsyncMock(side_effect=RuntimeError("injected conversation failure")),
            )
            async with factory() as session:
                current = await _principal(session, user_ids[11])
                with pytest.raises(RuntimeError, match="injected conversation failure"):
                    await accept_matching_invitation(
                        session,
                        current,
                        invitation_id=invitation_ids[6],
                        clock=lambda: NOW,
                    )
                await session.rollback()

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[7],
            sender_id=user_ids[12],
            recipient_id=user_ids[13],
            created_at=NOW - timedelta(minutes=8),
        )
        with monkeypatch.context() as patcher:
            patcher.setattr(
                acceptance,
                "enqueue_transactional_email",
                AsyncMock(side_effect=RuntimeError("injected outbox failure")),
            )
            async with factory() as session:
                current = await _principal(session, user_ids[13])
                with pytest.raises(RuntimeError, match="injected outbox failure"):
                    await accept_matching_invitation(
                        session,
                        current,
                        invitation_id=invitation_ids[7],
                        clock=lambda: NOW,
                    )
                await session.rollback()

        async with factory() as session:
            rolled_back = tuple(
                (
                    await session.scalars(
                        select(MatchingInvitation)
                        .where(MatchingInvitation.id.in_(invitation_ids[6:8]))
                        .order_by(MatchingInvitation.id)
                    )
                ).all()
            )
            assert all(row.status is InvitationStatus.PENDING for row in rolled_back)
            rolled_back_matches = await session.scalar(
                select(func.count(BuddyMatch.id)).where(
                    BuddyMatch.accepted_invitation_id.in_(invitation_ids[6:8])
                )
            )
            assert rolled_back_matches == 0

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[8],
            sender_id=user_ids[14],
            recipient_id=user_ids[15],
            created_at=NOW - timedelta(days=7) + timedelta(minutes=1),
        )
        async with factory() as accept_before_expiry:
            current = await _principal(accept_before_expiry, user_ids[15])
            await accept_matching_invitation(
                accept_before_expiry,
                current,
                invitation_id=invitation_ids[8],
                clock=lambda: NOW,
            )
            expiry_task = asyncio.create_task(_expire(factory, at=NOW + timedelta(minutes=2)))
            expired_while_locked = await asyncio.wait_for(expiry_task, timeout=5)
            assert invitation_ids[8] not in expired_while_locked
            await accept_before_expiry.commit()

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[9],
            sender_id=user_ids[16],
            recipient_id=user_ids[17],
            created_at=NOW - timedelta(days=7),
        )
        async with factory() as expiry_winner:
            selected = await expire_invitation_batch(
                expiry_winner,
                batch_size=100,
                clock=lambda: NOW,
            )
            assert invitation_ids[9] in selected
            losing_accept = asyncio.create_task(
                _accept(
                    factory,
                    invitation_ids[9],
                    user_ids[17],
                    at=NOW - timedelta(seconds=1),
                )
            )
            await _assert_blocked(cast(asyncio.Task[object], losing_accept))
            await expiry_winner.commit()
        assert (await asyncio.wait_for(losing_accept, timeout=5))[0] == (
            InvitationAcceptReason.NOT_PENDING.value
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[10],
            sender_id=user_ids[18],
            recipient_id=user_ids[19],
            created_at=NOW - timedelta(minutes=5),
        )
        assert await _accept(factory, invitation_ids[10], user_ids[18]) == (
            InvitationAcceptReason.NOT_FOUND.value,
            None,
        )
        assert await _accept(factory, invitation_ids[10], user_ids[20]) == (
            InvitationAcceptReason.NOT_FOUND.value,
            None,
        )

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[11],
            sender_id=user_ids[18],
            recipient_id=user_ids[21],
            created_at=NOW - timedelta(minutes=4),
        )
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE app_private.users SET email_verified = false, "
                    "email_verified_at = NULL WHERE id = :user_id"
                ),
                {"user_id": user_ids[21]},
            )
        assert await _accept(factory, invitation_ids[11], user_ids[21]) == (
            InvitationAcceptReason.RECIPIENT_INELIGIBLE.value,
            None,
        )

        async with engine.connect() as connection:
            invalid_matches = await connection.scalar(
                text(
                    "SELECT count(*) FROM app_private.matches AS buddy_match "
                    "JOIN app_private.student_profiles AS first_profile "
                    "ON first_profile.id = buddy_match.participant_one_profile_id "
                    "JOIN app_private.student_profiles AS second_profile "
                    "ON second_profile.id = buddy_match.participant_two_profile_id "
                    "WHERE buddy_match.status = 'ACTIVE' "
                    "AND first_profile.student_type = second_profile.student_type"
                )
            )
            assert invalid_matches == 0
    finally:
        await engine.dispose()


def test_live_atomic_accept_replay_rollbacks_and_lock_races(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("INV005_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV005_TEST_DATABASE_URL for disposable INV-005 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv005_acceptance"
        or parsed_url.username != "inv005_runner"
    ):
        pytest.fail(
            "INV-005 requires the disposable inv005_runner role in the isolated "
            "loopback inv005_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "head")
        asyncio.run(_assert_acceptance_contract(async_database_url, monkeypatch))
        command.check(config)
    finally:
        get_migration_database_settings.cache_clear()
