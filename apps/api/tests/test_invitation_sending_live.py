"""Opt-in INV-003 concurrency acceptance on isolated loopback PostgreSQL.

Set INV003_TEST_DATABASE_URL to the disposable ``inv003_runner`` role in a
loopback-only database named ``inv003_acceptance``. The database is migrated to
the existing head; this test never targets shared development or production data.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
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
    InvitationStatus,
    MatchingInvitation,
    StudentType,
    TransactionalOutbox,
)
from app.services.invitation_sending import (
    MATCHING_INVITATION_CREATED,
    InvitationSendError,
    InvitationSendReason,
    send_matching_invitation,
)
from app.services.matching_eligibility import EligibleMatchingPrincipal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_eligible_participants(
    engine: AsyncEngine,
    *,
    count: int,
) -> tuple[list[UUID], list[UUID]]:
    user_ids = [uuid4() for _ in range(count)]
    profile_ids = [uuid4() for _ in range(count)]
    vietnamese_indices = {0, 2, 4, 36, 68, 70, 72}
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
                    "email": f"inv003-{user_id}@example.invalid",
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
                    "full_name": f"Eligible participant {index}",
                    "display_name": f"Participant {index}",
                    "student_type": (
                        StudentType.VIETNAMESE.value
                        if index in vietnamese_indices
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
            [
                {"profile_id": profile_id, "interest_id": interest_id}
                for profile_id in profile_ids
            ],
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
                {"profile_id": profile_id, "object_key": f"inv003/{profile_id}.jpg"}
                for profile_id in profile_ids
            ],
        )
    return user_ids, profile_ids


def _principal(user_id: UUID, profile_id: UUID, student_type: StudentType) -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=user_id,
        profile_id=profile_id,
        student_type=student_type,
    )


async def _send(
    factory: async_sessionmaker[AsyncSession],
    sender: EligibleMatchingPrincipal,
    recipient_profile_id: UUID,
    *,
    message: str,
) -> tuple[str, UUID | None]:
    async with factory() as session:
        try:
            invitation = await send_matching_invitation(
                session,
                sender,
                recipient_profile_id=recipient_profile_id,
                message=message,
                clock=lambda: NOW,
            )
            await session.commit()
            return "CREATED", invitation.id
        except InvitationSendError as error:
            await session.rollback()
            return error.reason.value, None


async def _insert_invitations(
    engine: AsyncEngine,
    rows: list[dict[str, object]],
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:sender_id, :recipient_id, :message, :status, :created_at, "
                ":updated_at, :expires_at, :responded_at)"
            ),
            rows,
        )


async def _insert_active_match(
    engine: AsyncEngine,
    *,
    sender_user_id: UUID,
    recipient_user_id: UUID,
    sender_profile_id: UUID,
    recipient_profile_id: UUID,
) -> None:
    invitation_id = uuid4()
    created_at = NOW - timedelta(hours=1)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, 'Accepted relationship marker', "
                "'ACCEPTED', :created_at, :updated_at, :expires_at, :responded_at)"
            ),
            {
                "id": invitation_id,
                "sender_id": sender_user_id,
                "recipient_id": recipient_user_id,
                "created_at": created_at,
                "updated_at": NOW,
                "expires_at": created_at + timedelta(days=7),
                "responded_at": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matches "
                "(participant_one_user_id, participant_two_user_id, "
                "participant_one_profile_id, participant_two_profile_id, status, "
                "accepted_invitation_id, score, score_breakdown, activated_at, "
                "created_at, updated_at) VALUES "
                "(:sender_user_id, :recipient_user_id, :sender_profile_id, "
                ":recipient_profile_id, 'ACTIVE', :invitation_id, 70, "
                "CAST(:score_breakdown AS jsonb), :activated_at, :activated_at, "
                ":activated_at)"
            ),
            {
                "sender_user_id": sender_user_id,
                "recipient_user_id": recipient_user_id,
                "sender_profile_id": sender_profile_id,
                "recipient_profile_id": recipient_profile_id,
                "invitation_id": invitation_id,
                "score_breakdown": json.dumps(
                    {
                        "reference_week_start": "2026-09-28",
                        "interests": {"similarity": 1, "weight": 40, "points": 40},
                    }
                ),
                "activated_at": NOW,
            },
        )


async def _assert_concurrency_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    user_ids, profile_ids = await _seed_eligible_participants(engine, count=74)
    successful_ids: set[UUID] = set()
    try:
        duplicate_sender = _principal(
            user_ids[0], profile_ids[0], StudentType.VIETNAMESE
        )
        duplicate_results = await asyncio.gather(
            _send(
                factory,
                duplicate_sender,
                profile_ids[1],
                message="  Duplicate race  ",
            ),
            _send(
                factory,
                duplicate_sender,
                profile_ids[1],
                message="Duplicate race",
            ),
        )
        assert sorted(result[0] for result in duplicate_results) == [
            "CREATED",
            InvitationSendReason.PENDING_EXISTS.value,
        ]
        successful_ids.update(result[1] for result in duplicate_results if result[1])

        reciprocal_a = _principal(user_ids[2], profile_ids[2], StudentType.VIETNAMESE)
        reciprocal_b = _principal(
            user_ids[3], profile_ids[3], StudentType.INTERNATIONAL
        )
        reciprocal_results = await asyncio.gather(
            _send(factory, reciprocal_a, profile_ids[3], message="A to B"),
            _send(factory, reciprocal_b, profile_ids[2], message="B to A"),
        )
        assert sorted(result[0] for result in reciprocal_results) == [
            "CREATED",
            InvitationSendReason.PENDING_EXISTS.value,
        ]
        successful_ids.update(result[1] for result in reciprocal_results if result[1])

        await _insert_invitations(
            engine,
            [
                {
                    "sender_id": user_ids[4],
                    "recipient_id": user_ids[index],
                    "message": f"Seed pending {index}",
                    "status": InvitationStatus.PENDING.value,
                    "created_at": NOW,
                    "updated_at": NOW,
                    "expires_at": NOW + timedelta(days=7),
                    "responded_at": None,
                }
                for index in range(5, 34)
            ],
        )
        limit_sender = _principal(user_ids[4], profile_ids[4], StudentType.VIETNAMESE)
        limit_results = await asyncio.gather(
            _send(factory, limit_sender, profile_ids[34], message="Request thirty"),
            _send(factory, limit_sender, profile_ids[35], message="Request thirty too"),
        )
        assert sorted(result[0] for result in limit_results) == [
            "CREATED",
            InvitationSendReason.PENDING_LIMIT_REACHED.value,
        ]
        successful_ids.update(result[1] for result in limit_results if result[1])
        async with factory() as session:
            effective_limit_count = await session.scalar(
                select(func.count(MatchingInvitation.id)).where(
                    MatchingInvitation.sender_id == user_ids[4],
                    MatchingInvitation.status == InvitationStatus.PENDING,
                    MatchingInvitation.expires_at > NOW,
                )
            )
            assert effective_limit_count == 30

        stale_created_at = NOW - timedelta(days=8)
        await _insert_invitations(
            engine,
            [
                {
                    "sender_id": user_ids[36],
                    "recipient_id": user_ids[index],
                    "message": f"Stale pending {index}",
                    "status": InvitationStatus.PENDING.value,
                    "created_at": stale_created_at,
                    "updated_at": stale_created_at,
                    "expires_at": stale_created_at + timedelta(days=7),
                    "responded_at": None,
                }
                for index in range(37, 68)
            ],
        )
        stale_sender = _principal(
            user_ids[36], profile_ids[36], StudentType.VIETNAMESE
        )
        stale_result = await _send(
            factory,
            stale_sender,
            profile_ids[37],
            message="  Immediate after expiry  ",
        )
        assert stale_result[0] == "CREATED"
        assert stale_result[1] is not None
        successful_ids.add(stale_result[1])
        async with factory() as session:
            pair_rows = tuple(
                (
                    await session.scalars(
                        select(MatchingInvitation)
                        .where(
                            MatchingInvitation.sender_id == user_ids[36],
                            MatchingInvitation.recipient_id == user_ids[37],
                        )
                        .order_by(MatchingInvitation.created_at)
                    )
                ).all()
            )
            assert [row.status for row in pair_rows] == [
                InvitationStatus.EXPIRED,
                InvitationStatus.PENDING,
            ]
            assert pair_rows[1].message == "Immediate after expiry"

        await _insert_active_match(
            engine,
            sender_user_id=user_ids[68],
            recipient_user_id=user_ids[69],
            sender_profile_id=profile_ids[68],
            recipient_profile_id=profile_ids[69],
        )
        accepted_sender = _principal(
            user_ids[68], profile_ids[68], StudentType.VIETNAMESE
        )
        accepted_result = await _send(
            factory,
            accepted_sender,
            profile_ids[69],
            message="Must remain blocked",
        )
        assert accepted_result == (InvitationSendReason.ACTIVE_PAIR_EXISTS.value, None)

        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE app_private.student_profiles SET matching_opt_in = false "
                    "WHERE id = :profile_id"
                ),
                {"profile_id": profile_ids[71]},
            )
            await connection.execute(
                text("UPDATE app_private.users SET is_active = false WHERE id = :user_id"),
                {"user_id": user_ids[72]},
            )
        recipient_changed = await _send(
            factory,
            _principal(user_ids[70], profile_ids[70], StudentType.VIETNAMESE),
            profile_ids[71],
            message="Stale recommendation recipient",
        )
        sender_changed = await _send(
            factory,
            _principal(user_ids[72], profile_ids[72], StudentType.VIETNAMESE),
            profile_ids[73],
            message="Stale sender state",
        )
        assert recipient_changed == (
            InvitationSendReason.RECIPIENT_INELIGIBLE.value,
            None,
        )
        assert sender_changed == (InvitationSendReason.SENDER_INELIGIBLE.value, None)

        async with factory() as session:
            outbox_rows = tuple(
                (
                    await session.scalars(
                        select(TransactionalOutbox).where(
                            TransactionalOutbox.aggregate_id.in_(successful_ids)
                        )
                    )
                ).all()
            )
            assert len(outbox_rows) == len(successful_ids) == 4
            assert all(row.event_type == MATCHING_INVITATION_CREATED for row in outbox_rows)
            assert all(set(row.payload) == {"invitation_id"} for row in outbox_rows)
            assert all("message" not in row.payload for row in outbox_rows)
    finally:
        await engine.dispose()


def test_live_duplicate_reciprocal_limit_expiry_and_outbox_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("INV003_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV003_TEST_DATABASE_URL for disposable INV-003 PostgreSQL acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv003_acceptance"
        or parsed_url.username != "inv003_runner"
    ):
        pytest.fail(
            "INV-003 requires the disposable inv003_runner role in the isolated "
            "loopback inv003_acceptance database."
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
        asyncio.run(_assert_concurrency_contract(async_database_url))
    finally:
        get_migration_database_settings.cache_clear()
