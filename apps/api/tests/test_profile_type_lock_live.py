"""Opt-in PROFILE-V2-001 type-change versus Match activation acceptance.

Set PROFILEV2001_TEST_DATABASE_URL to the disposable ``profilev2001_runner``
role in a loopback-only database named ``profilev2001_acceptance``. Never point
this test at development, staging, or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import select, text
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
from app.models import BuddyMatch, StudentProfile, StudentType, User
from app.schemas import ProfileUpdate
from app.services.buddy_matches import (
    BuddyMatchActivationError,
    BuddyMatchActivationReason,
    activate_buddy_match,
)
from app.services.matching_scoring import (
    CompatibilityBreakdown,
    CompatibilityScore,
    CompatibilitySignalBreakdown,
)
from app.services.profiles import (
    ProfileUpdateConflictError,
    ProfileUpdateConflictReason,
    update_own_profile,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _compatibility() -> CompatibilityScore:
    return CompatibilityScore(
        precise_score=Fraction(75),
        score=75,
        breakdown=CompatibilityBreakdown(
            interests=CompatibilitySignalBreakdown(Fraction(1), 40, Fraction(40)),
            activities=CompatibilitySignalBreakdown(Fraction(1, 2), 35, Fraction(35, 2)),
            availability=CompatibilitySignalBreakdown(Fraction(1), 15, Fraction(15)),
            languages=CompatibilitySignalBreakdown(Fraction(0), 5, Fraction(0)),
            major=CompatibilitySignalBreakdown(Fraction(1, 2), 5, Fraction(5, 2)),
        ),
        reference_week_start=date(2026, 9, 28),
    )


async def _seed_race_pairs(
    engine: AsyncEngine,
) -> tuple[list[UUID], list[UUID], list[UUID]]:
    user_ids = [uuid4() for _ in range(4)]
    profile_ids = [uuid4() for _ in range(4)]
    invitation_ids = [uuid4() for _ in range(2)]
    created_at = NOW - timedelta(hours=1)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users (id, email, password_hash) "
                "VALUES (:id, :email, 'test-only-hash')"
            ),
            [
                {"id": user_id, "email": f"profilev2001-{user_id}@example.invalid"}
                for user_id in user_ids
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, student_type) "
                "VALUES (:id, :user_id, :full_name, :student_type)"
            ),
            [
                {
                    "id": profile_ids[index],
                    "user_id": user_id,
                    "full_name": f"Profile type race {index}",
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
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                "expires_at, responded_at) VALUES "
                "(:id, :sender_id, :recipient_id, :message, 'ACCEPTED', :created_at, "
                ":updated_at, :expires_at, :responded_at)"
            ),
            [
                {
                    "id": invitation_ids[index],
                    "sender_id": user_ids[index * 2],
                    "recipient_id": user_ids[index * 2 + 1],
                    "message": f"Accepted race fixture {index}",
                    "created_at": created_at,
                    "updated_at": NOW,
                    "expires_at": created_at + timedelta(days=7),
                    "responded_at": NOW,
                }
                for index in range(2)
            ],
        )
    return user_ids, profile_ids, invitation_ids


async def _activate(
    factory: async_sessionmaker[AsyncSession],
    invitation_id: UUID,
) -> str:
    async with factory() as session:
        try:
            await activate_buddy_match(
                session,
                accepted_invitation_id=invitation_id,
                compatibility=_compatibility(),
                clock=lambda: NOW,
            )
            await session.commit()
            return "CREATED"
        except BuddyMatchActivationError as error:
            await session.rollback()
            return error.reason.value


async def _change_type(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    *,
    expected_version: int,
    student_type: StudentType,
) -> str:
    async with factory() as session:
        owner = cast(User | None, await session.scalar(select(User).where(User.id == user_id)))
        assert owner is not None
        try:
            await update_own_profile(
                session,
                owner,
                ProfileUpdate(
                    version=expected_version,
                    student_type=student_type,
                ),
            )
            await session.commit()
            return "UPDATED"
        except ProfileUpdateConflictError as error:
            await session.rollback()
            return error.reason.value


async def _assert_blocked(task: asyncio.Task[str]) -> None:
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.shield(task), timeout=0.25)


async def _assert_type_update_match_races(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        user_ids, _profile_ids, invitation_ids = await _seed_race_pairs(engine)

        async with factory() as profile_winner_session:
            owner = cast(
                User | None,
                await profile_winner_session.scalar(
                    select(User).where(User.id == user_ids[0])
                ),
            )
            assert owner is not None
            await update_own_profile(
                profile_winner_session,
                owner,
                ProfileUpdate(
                    version=1,
                    student_type=StudentType.INTERNATIONAL,
                ),
            )
            activation_task = asyncio.create_task(_activate(factory, invitation_ids[0]))
            await _assert_blocked(activation_task)
            await profile_winner_session.commit()
        assert await asyncio.wait_for(activation_task, timeout=5) == (
            BuddyMatchActivationReason.OPPOSITE_TYPES_REQUIRED.value
        )

        async with factory() as match_winner_session:
            await activate_buddy_match(
                match_winner_session,
                accepted_invitation_id=invitation_ids[1],
                compatibility=_compatibility(),
                clock=lambda: NOW,
            )
            update_task = asyncio.create_task(
                _change_type(
                    factory,
                    user_ids[2],
                    expected_version=1,
                    student_type=StudentType.INTERNATIONAL,
                )
            )
            await _assert_blocked(update_task)
            await match_winner_session.commit()
        assert await asyncio.wait_for(update_task, timeout=5) == (
            ProfileUpdateConflictReason.STUDENT_TYPE_LOCKED_ACTIVE_MATCH.value
        )

        second_match_invitation_id = uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO app_private.matching_invitations "
                    "(id, sender_id, recipient_id, message, status, created_at, updated_at, "
                    "expires_at, responded_at) VALUES "
                    "(:id, :sender_id, :recipient_id, :message, 'ACCEPTED', :created_at, "
                    ":updated_at, :expires_at, :responded_at)"
                ),
                {
                    "id": second_match_invitation_id,
                    "sender_id": user_ids[2],
                    "recipient_id": user_ids[1],
                    "message": "Accepted multiple-match fixture",
                    "created_at": NOW - timedelta(minutes=30),
                    "updated_at": NOW,
                    "expires_at": NOW - timedelta(minutes=30) + timedelta(days=7),
                    "responded_at": NOW,
                },
            )
        assert await _activate(factory, second_match_invitation_id) == "CREATED"
        assert await _change_type(
            factory,
            user_ids[2],
            expected_version=1,
            student_type=StudentType.INTERNATIONAL,
        ) == ProfileUpdateConflictReason.STUDENT_TYPE_LOCKED_ACTIVE_MATCH.value

        async with factory() as verification_session:
            profiles = tuple(
                (
                    await verification_session.scalars(
                        select(StudentProfile)
                        .where(StudentProfile.user_id.in_((user_ids[0], user_ids[2])))
                        .order_by(StudentProfile.user_id)
                    )
                ).all()
            )
            types_by_user = {profile.user_id: profile.student_type for profile in profiles}
            assert types_by_user[user_ids[0]] is StudentType.INTERNATIONAL
            assert types_by_user[user_ids[2]] is StudentType.VIETNAMESE
            matches = tuple((await verification_session.scalars(select(BuddyMatch))).all())
            assert len(matches) == 2
            assert {
                frozenset(
                    (match.participant_one_user_id, match.participant_two_user_id)
                )
                for match in matches
            } == {
                frozenset((user_ids[2], user_ids[3])),
                frozenset((user_ids[2], user_ids[1])),
            }

        async with engine.connect() as connection:
            invalid_match_count = await connection.scalar(
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
            assert invalid_match_count == 0
    finally:
        await engine.dispose()


def test_live_profile_type_update_and_match_activation_are_serialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("PROFILEV2001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set PROFILEV2001_TEST_DATABASE_URL for disposable PROFILE-V2-001 acceptance."
        )
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "profilev2001_acceptance"
        or parsed_url.username != "profilev2001_runner"
    ):
        pytest.fail(
            "PROFILE-V2-001 requires the disposable profilev2001_runner role in the "
            "isolated loopback profilev2001_acceptance database."
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
        asyncio.run(_assert_type_update_match_races(async_database_url))
        command.check(config)
    finally:
        get_migration_database_settings.cache_clear()
