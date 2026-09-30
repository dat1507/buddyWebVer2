"""INV-006 state-race and relationship-safety acceptance on isolated PostgreSQL.

Set INV006_TEST_DATABASE_URL to the disposable ``inv006_runner`` role in a
loopback-only database named ``inv006_mutations``. Never target shared data.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
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

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import (
    BuddyConversation,
    BuddyMatch,
    BuddyMessage,
    InvitationStatus,
    MatchingInvitation,
    StudentProfile,
    StudentType,
    TransactionalOutbox,
    User,
)
from app.schemas import ProfileUpdate
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.buddy_chat import persist_buddy_message
from app.services.invitation_acceptance import (
    MATCHING_INVITATION_ACCEPTED,
    InvitationAcceptanceResult,
    InvitationAcceptError,
    accept_matching_invitation,
)
from app.services.invitation_expiry import expire_invitation_batch
from app.services.invitation_mutations import (
    InvitationMutationError,
    InvitationMutationReason,
    InvitationMutationResult,
    cancel_matching_invitation,
    decline_matching_invitation,
    hide_accepted_invitation_from_sender,
)
from app.services.invitation_reads import list_incoming_invitations, list_sent_invitations
from app.services.invitation_sending import send_matching_invitation
from app.services.matching_eligibility import get_eligible_matching_principal
from app.services.matching_recommendations import current_reference_week_start
from app.services.profiles import (
    ProfileUpdateConflictError,
    ProfileUpdateConflictReason,
    update_own_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 17, 0, tzinfo=UTC)
MutationOperation = Callable[..., Awaitable[InvitationMutationResult]]


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
                    "email": f"inv006-{user_id}@example.invalid",
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
                    "full_name": f"INV-006 participant {index}",
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
                {"profile_id": profile_id, "object_key": f"inv006/{profile_id}.jpg"}
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
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, created_at, updated_at, expires_at) "
                "VALUES (:id, :sender_id, :recipient_id, 'Private mutation fixture', "
                ":created_at, :created_at, :expires_at)"
            ),
            {
                "id": invitation_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "created_at": created_at,
                "expires_at": created_at + timedelta(days=7),
            },
        )


async def _principal(session: AsyncSession, user_id: UUID) -> VerifiedBuddyPrincipal:
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
) -> tuple[str, InvitationAcceptanceResult | None]:
    async with factory() as session:
        current = await _principal(session, recipient_id)
        try:
            result = await accept_matching_invitation(
                session,
                current,
                invitation_id=invitation_id,
                clock=lambda: NOW,
            )
            await session.commit()
            return result.status.value, result
        except InvitationAcceptError as error:
            await session.rollback()
            return error.reason.value, None


async def _mutate(
    factory: async_sessionmaker[AsyncSession],
    operation: MutationOperation,
    invitation_id: UUID,
    owner_id: UUID,
    *,
    at: datetime = NOW,
) -> tuple[str, InvitationMutationResult | None]:
    async with factory() as session:
        current = await _principal(session, owner_id)
        try:
            result = await operation(
                session,
                current,
                invitation_id=invitation_id,
                clock=lambda: at,
            )
            await session.commit()
            return result.status.value, result
        except InvitationMutationError as error:
            await session.rollback()
            return error.reason.value, None


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


async def _relationship_counts(
    session: AsyncSession,
    invitation_id: UUID,
) -> tuple[int, int, int]:
    match_count = int(
        await session.scalar(
            select(func.count(BuddyMatch.id)).where(
                BuddyMatch.accepted_invitation_id == invitation_id
            )
        )
        or 0
    )
    conversation_count = int(
        await session.scalar(
            select(func.count(BuddyConversation.id))
            .join(BuddyMatch, BuddyConversation.match_id == BuddyMatch.id)
            .where(BuddyMatch.accepted_invitation_id == invitation_id)
        )
        or 0
    )
    event_count = int(
        await session.scalar(
            select(func.count(TransactionalOutbox.id)).where(
                TransactionalOutbox.event_type == MATCHING_INVITATION_ACCEPTED,
                TransactionalOutbox.aggregate_id == invitation_id,
            )
        )
        or 0
    )
    return match_count, conversation_count, event_count


async def _assert_mutation_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        user_ids, profile_ids = await _seed_eligible_participants(engine, count=24)
        invitation_ids = [uuid4() for _ in range(12)]

        # Accept wins over Decline; the waiter refreshes the locked terminal state.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[0],
            sender_id=user_ids[0],
            recipient_id=user_ids[1],
            created_at=NOW - timedelta(hours=1),
        )
        async with factory() as accept_winner:
            recipient = await _principal(accept_winner, user_ids[1])
            await accept_matching_invitation(
                accept_winner,
                recipient,
                invitation_id=invitation_ids[0],
                clock=lambda: NOW,
            )
            decline_task = asyncio.create_task(
                _mutate(
                    factory,
                    decline_matching_invitation,
                    invitation_ids[0],
                    user_ids[1],
                )
            )
            await _assert_blocked(cast(asyncio.Task[object], decline_task))
            await accept_winner.commit()
        assert (await asyncio.wait_for(decline_task, timeout=5))[0] == (
            InvitationMutationReason.INVALID_STATE.value
        )

        # Decline wins over Accept and leaves no relationship artifacts.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[1],
            sender_id=user_ids[2],
            recipient_id=user_ids[3],
            created_at=NOW - timedelta(hours=1),
        )
        async with factory() as decline_winner:
            recipient = await _principal(decline_winner, user_ids[3])
            await decline_matching_invitation(
                decline_winner,
                recipient,
                invitation_id=invitation_ids[1],
                clock=lambda: NOW,
            )
            accept_task = asyncio.create_task(_accept(factory, invitation_ids[1], user_ids[3]))
            await _assert_blocked(cast(asyncio.Task[object], accept_task))
            await decline_winner.commit()
        assert (await asyncio.wait_for(accept_task, timeout=5))[0] == (
            "INVITATION_ACCEPT_NOT_PENDING"
        )

        # Accept wins over Cancel.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[2],
            sender_id=user_ids[4],
            recipient_id=user_ids[5],
            created_at=NOW - timedelta(hours=1),
        )
        async with factory() as accept_winner:
            recipient = await _principal(accept_winner, user_ids[5])
            await accept_matching_invitation(
                accept_winner,
                recipient,
                invitation_id=invitation_ids[2],
                clock=lambda: NOW,
            )
            cancel_task = asyncio.create_task(
                _mutate(
                    factory,
                    cancel_matching_invitation,
                    invitation_ids[2],
                    user_ids[4],
                )
            )
            await _assert_blocked(cast(asyncio.Task[object], cancel_task))
            await accept_winner.commit()
        assert (await asyncio.wait_for(cancel_task, timeout=5))[0] == (
            InvitationMutationReason.INVALID_STATE.value
        )

        # Cancel wins over Accept and leaves no relationship artifacts.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[3],
            sender_id=user_ids[6],
            recipient_id=user_ids[7],
            created_at=NOW - timedelta(hours=1),
        )
        async with factory() as cancel_winner:
            sender = await _principal(cancel_winner, user_ids[6])
            await cancel_matching_invitation(
                cancel_winner,
                sender,
                invitation_id=invitation_ids[3],
                clock=lambda: NOW,
            )
            accept_task = asyncio.create_task(_accept(factory, invitation_ids[3], user_ids[7]))
            await _assert_blocked(cast(asyncio.Task[object], accept_task))
            await cancel_winner.commit()
        assert (await asyncio.wait_for(accept_task, timeout=5))[0] == (
            "INVITATION_ACCEPT_NOT_PENDING"
        )

        # Decline/Cancel can win immediately before expiry; SKIP LOCKED never overwrites them.
        for offset, operation, owner_index, expected_status in (
            (4, decline_matching_invitation, 9, InvitationStatus.DECLINED),
            (6, cancel_matching_invitation, 12, InvitationStatus.CANCELLED),
        ):
            await _insert_invitation(
                engine,
                invitation_id=invitation_ids[offset],
                sender_id=user_ids[offset * 2],
                recipient_id=user_ids[offset * 2 + 1],
                created_at=NOW - timedelta(days=7),
            )
            async with factory() as mutation_winner:
                owner = await _principal(mutation_winner, user_ids[owner_index])
                await operation(
                    mutation_winner,
                    owner,
                    invitation_id=invitation_ids[offset],
                    clock=lambda: NOW - timedelta(microseconds=1),
                )
                expired_ids = await asyncio.wait_for(_expire(factory, at=NOW), timeout=5)
                assert invitation_ids[offset] not in expired_ids
                await mutation_winner.commit()
            async with factory() as verify:
                row = await verify.get(MatchingInvitation, invitation_ids[offset])
                assert row is not None and row.status is expected_status

        # Persisted expiry wins over Decline/Cancel; waiters return the stable expiry reason.
        for offset, operation, owner_index in (
            (5, decline_matching_invitation, 11),
            (7, cancel_matching_invitation, 14),
        ):
            await _insert_invitation(
                engine,
                invitation_id=invitation_ids[offset],
                sender_id=user_ids[offset * 2],
                recipient_id=user_ids[offset * 2 + 1],
                created_at=NOW - timedelta(days=7),
            )
            async with factory() as expiry_winner:
                expired_ids = await expire_invitation_batch(
                    expiry_winner,
                    batch_size=100,
                    clock=lambda: NOW,
                )
                assert invitation_ids[offset] in expired_ids
                mutation_task = asyncio.create_task(
                    _mutate(
                        factory,
                        operation,
                        invitation_ids[offset],
                        user_ids[owner_index],
                    )
                )
                await _assert_blocked(cast(asyncio.Task[object], mutation_task))
                await expiry_winner.commit()
            assert (await asyncio.wait_for(mutation_task, timeout=5))[0] == (
                InvitationMutationReason.EXPIRED.value
            )

        # Duplicate owner retries are harmless, and terminal rows release pair/pending limits.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[8],
            sender_id=user_ids[16],
            recipient_id=user_ids[17],
            created_at=NOW - timedelta(hours=1),
        )
        decline_retries = await asyncio.gather(
            _mutate(
                factory,
                decline_matching_invitation,
                invitation_ids[8],
                user_ids[17],
            ),
            _mutate(
                factory,
                decline_matching_invitation,
                invitation_ids[8],
                user_ids[17],
            ),
        )
        assert [result[0] for result in decline_retries] == ["DECLINED", "DECLINED"]

        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[9],
            sender_id=user_ids[18],
            recipient_id=user_ids[19],
            created_at=NOW - timedelta(hours=1),
        )
        cancel_retries = await asyncio.gather(
            _mutate(
                factory,
                cancel_matching_invitation,
                invitation_ids[9],
                user_ids[18],
            ),
            _mutate(
                factory,
                cancel_matching_invitation,
                invitation_ids[9],
                user_ids[18],
            ),
        )
        assert [result[0] for result in cancel_retries] == ["CANCELLED", "CANCELLED"]

        for sender_index, recipient_index in ((16, 17), (18, 19)):
            async with factory() as resend:
                sender = await _principal(resend, user_ids[sender_index])
                eligible_sender = await get_eligible_matching_principal(resend, sender)
                invitation = await send_matching_invitation(
                    resend,
                    eligible_sender,
                    recipient_profile_id=profile_ids[recipient_index],
                    message="Immediate re-invite after terminal response",
                    clock=lambda: NOW + timedelta(minutes=1),
                )
                await resend.commit()
                assert invitation.status is InvitationStatus.PENDING
                assert (
                    await resend.scalar(
                        select(func.count(MatchingInvitation.id)).where(
                            MatchingInvitation.sender_id == user_ids[sender_index],
                            MatchingInvitation.status == InvitationStatus.PENDING,
                            MatchingInvitation.expires_at > NOW + timedelta(minutes=1),
                        )
                    )
                    == 1
                )

        async with factory() as visibility:
            declined_sender = await _principal(visibility, user_ids[2])
            declined_recipient = await _principal(visibility, user_ids[3])
            cancelled_sender = await _principal(visibility, user_ids[6])
            cancelled_recipient = await _principal(visibility, user_ids[7])
            declined_sent = await list_sent_invitations(
                visibility,
                declined_sender,
                locale="en",
                page=1,
                page_size=50,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW + timedelta(minutes=1),
            )
            declined_incoming = await list_incoming_invitations(
                visibility,
                declined_recipient,
                locale="en",
                page=1,
                page_size=50,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW + timedelta(minutes=1),
            )
            cancelled_sent = await list_sent_invitations(
                visibility,
                cancelled_sender,
                locale="en",
                page=1,
                page_size=50,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW + timedelta(minutes=1),
            )
            cancelled_incoming = await list_incoming_invitations(
                visibility,
                cancelled_recipient,
                locale="en",
                page=1,
                page_size=50,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW + timedelta(minutes=1),
            )
            assert invitation_ids[1] not in {item.id for item in declined_sent.items}
            assert invitation_ids[1] not in {item.id for item in declined_incoming.items}
            assert invitation_ids[3] not in {item.id for item in cancelled_sent.items}
            assert invitation_ids[3] not in {item.id for item in cancelled_incoming.items}

        # Concurrent Accept then Hide: hide waits, refreshes ACCEPTED, and remains view-only.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[10],
            sender_id=user_ids[20],
            recipient_id=user_ids[21],
            created_at=NOW - timedelta(hours=1),
        )
        async with factory() as accept_winner:
            recipient = await _principal(accept_winner, user_ids[21])
            await accept_matching_invitation(
                accept_winner,
                recipient,
                invitation_id=invitation_ids[10],
                clock=lambda: NOW,
            )
            hide_task = asyncio.create_task(
                _mutate(
                    factory,
                    hide_accepted_invitation_from_sender,
                    invitation_ids[10],
                    user_ids[20],
                    at=NOW + timedelta(seconds=1),
                )
            )
            await _assert_blocked(cast(asyncio.Task[object], hide_task))
            await accept_winner.commit()
        assert (await asyncio.wait_for(hide_task, timeout=5))[0] == "ACCEPTED"

        # A separately accepted row proves duplicate hide, Sent filtering, chat retention,
        # and the ACTIVE-Match profile-type lock all survive sender-only hiding.
        await _insert_invitation(
            engine,
            invitation_id=invitation_ids[11],
            sender_id=user_ids[22],
            recipient_id=user_ids[23],
            created_at=NOW - timedelta(hours=1),
        )
        accepted_status, accepted = await _accept(factory, invitation_ids[11], user_ids[23])
        assert accepted_status == "ACCEPTED" and accepted is not None
        async with factory() as message_session:
            await persist_buddy_message(
                message_session,
                conversation_id=accepted.conversation_id,
                authenticated_sender_id=user_ids[22],
                body="Message must survive sender history hide.",
                clock=lambda: NOW + timedelta(seconds=1),
            )
            await message_session.commit()

        hide_retries = await asyncio.gather(
            _mutate(
                factory,
                hide_accepted_invitation_from_sender,
                invitation_ids[11],
                user_ids[22],
                at=NOW + timedelta(seconds=2),
            ),
            _mutate(
                factory,
                hide_accepted_invitation_from_sender,
                invitation_ids[11],
                user_ids[22],
                at=NOW + timedelta(seconds=3),
            ),
        )
        assert [result[0] for result in hide_retries] == ["ACCEPTED", "ACCEPTED"]
        assert (
            await _mutate(
                factory,
                hide_accepted_invitation_from_sender,
                invitation_ids[11],
                user_ids[23],
            )
        )[0] == InvitationMutationReason.NOT_FOUND.value
        assert (
            await _mutate(
                factory,
                hide_accepted_invitation_from_sender,
                invitation_ids[11],
                user_ids[0],
            )
        )[0] == InvitationMutationReason.NOT_FOUND.value

        async with factory() as verify:
            hidden = await verify.get(MatchingInvitation, invitation_ids[11])
            assert hidden is not None
            assert hidden.status is InvitationStatus.ACCEPTED
            assert hidden.sender_hidden_at in {
                NOW + timedelta(seconds=2),
                NOW + timedelta(seconds=3),
            }
            assert await _relationship_counts(verify, invitation_ids[11]) == (1, 1, 1)
            assert (
                await verify.scalar(
                    select(func.count(BuddyMessage.id)).where(
                        BuddyMessage.conversation_id == accepted.conversation_id
                    )
                )
                == 1
            )
            sender = await _principal(verify, user_ids[22])
            sent = await list_sent_invitations(
                verify,
                sender,
                locale="en",
                page=1,
                page_size=50,
                reference_week_start=current_reference_week_start(NOW),
                clock=lambda: NOW + timedelta(minutes=1),
            )
            assert invitation_ids[11] not in {item.id for item in sent.items}

        async with factory() as profile_update:
            profile_owner_user = cast(
                User | None,
                await profile_update.scalar(select(User).where(User.id == user_ids[22])),
            )
            assert profile_owner_user is not None
            with pytest.raises(ProfileUpdateConflictError) as error:
                await update_own_profile(
                    profile_update,
                    profile_owner_user,
                    ProfileUpdate(version=1, student_type=StudentType.INTERNATIONAL),
                )
            assert (
                error.value.reason is ProfileUpdateConflictReason.STUDENT_TYPE_LOCKED_ACTIVE_MATCH
            )
            await profile_update.rollback()

        async with factory() as verify:
            assert await _relationship_counts(verify, invitation_ids[0]) == (1, 1, 1)
            assert await _relationship_counts(verify, invitation_ids[1]) == (0, 0, 0)
            assert await _relationship_counts(verify, invitation_ids[2]) == (1, 1, 1)
            assert await _relationship_counts(verify, invitation_ids[3]) == (0, 0, 0)
            for invitation_id in invitation_ids[4:10]:
                assert await _relationship_counts(verify, invitation_id) == (0, 0, 0)
    finally:
        await engine.dispose()


def test_live_inv006_mutation_races_and_relationship_safety() -> None:
    database_url = os.getenv("INV006_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV006_TEST_DATABASE_URL for disposable INV-006 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv006_mutations"
        or parsed_url.username != "inv006_runner"
    ):
        pytest.fail(
            "INV-006 requires the disposable inv006_runner role in the isolated "
            "loopback inv006_mutations database."
        )

    os.environ[MIGRATION_URL_VARIABLE] = database_url
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "head")
        asyncio.run(_assert_mutation_contract(async_database_url))
        command.check(config)
    finally:
        get_migration_database_settings.cache_clear()
        os.environ.pop(MIGRATION_URL_VARIABLE, None)
