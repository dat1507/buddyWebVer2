"""Opt-in BUDDY-001 migration and concurrency acceptance on isolated PostgreSQL.

Set BUDDY001_TEST_DATABASE_URL to the disposable ``buddy001_runner`` role in a
loopback-only database named ``buddy001_acceptance``. The test returns that
database to revision 0012 and must never target development or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import BuddyMatch, MatchStatus, StudentType
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 3, 0, tzinfo=UTC)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _compatibility() -> CompatibilityScore:
    return CompatibilityScore(
        precise_score=Fraction(3, 4) * 100,
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


async def _seed_contract_rows(
    engine: AsyncEngine,
) -> tuple[list[UUID], list[UUID], list[UUID]]:
    user_ids = [uuid4() for _ in range(5)]
    profile_ids = [uuid4() for _ in range(5)]
    invitation_ids = [uuid4() for _ in range(5)]
    student_types = (
        StudentType.VIETNAMESE,
        StudentType.INTERNATIONAL,
        StudentType.VIETNAMESE,
        StudentType.INTERNATIONAL,
        StudentType.INTERNATIONAL,
    )
    invitation_pairs = (
        (user_ids[0], user_ids[1]),
        (user_ids[2], user_ids[3]),
        (user_ids[3], user_ids[2]),
        (user_ids[0], user_ids[4]),
        (user_ids[0], user_ids[2]),
    )
    created_at = NOW - timedelta(hours=1)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.users (id, email, password_hash) "
                "VALUES (:id, :email, 'test-only-hash')"
            ),
            [
                {"id": user_id, "email": f"buddy001-{user_id}@example.invalid"}
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
                    "full_name": f"Buddy participant {index}",
                    "student_type": student_types[index].value,
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
                    "sender_id": pair[0],
                    "recipient_id": pair[1],
                    "message": f"Accepted invitation {index}",
                    "created_at": created_at,
                    "updated_at": NOW,
                    "expires_at": created_at + timedelta(days=7),
                    "responded_at": NOW,
                }
                for index, pair in enumerate(invitation_pairs)
            ],
        )
    return user_ids, profile_ids, invitation_ids


async def _activate(
    factory: async_sessionmaker[AsyncSession],
    invitation_id: UUID,
) -> tuple[str, UUID | None]:
    async with factory() as session:
        try:
            buddy_match = await activate_buddy_match(
                session,
                accepted_invitation_id=invitation_id,
                compatibility=_compatibility(),
                clock=lambda: NOW,
            )
            await session.commit()
            return "CREATED", buddy_match.id
        except BuddyMatchActivationError as error:
            await session.rollback()
            return error.reason.value, None


async def _expect_integrity_error(
    engine: AsyncEngine,
    statement: str,
    parameters: dict[str, object],
) -> None:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        with pytest.raises(IntegrityError):
            await connection.execute(text(statement), parameters)
        await transaction.rollback()


async def _assert_upgrade_and_concurrency(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        user_ids, profile_ids, invitation_ids = await _seed_contract_rows(engine)

        same_direction_results = await asyncio.gather(
            _activate(factory, invitation_ids[0]),
            _activate(factory, invitation_ids[0]),
        )
        assert sorted(result[0] for result in same_direction_results) == [
            "CREATED",
            BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS.value,
        ]

        reciprocal_results = await asyncio.gather(
            _activate(factory, invitation_ids[1]),
            _activate(factory, invitation_ids[2]),
        )
        assert sorted(result[0] for result in reciprocal_results) == [
            "CREATED",
            BuddyMatchActivationReason.ACTIVE_PAIR_EXISTS.value,
        ]

        second_buddy = await _activate(factory, invitation_ids[3])
        assert second_buddy[0] == "CREATED"
        same_type = await _activate(factory, invitation_ids[4])
        assert same_type == (BuddyMatchActivationReason.OPPOSITE_TYPES_REQUIRED.value, None)

        async with factory() as session:
            matches = tuple(
                (
                    await session.scalars(
                        select(BuddyMatch).order_by(BuddyMatch.activated_at, BuddyMatch.id)
                    )
                ).all()
            )
            assert len(matches) == 3
            assert all(match.status is MatchStatus.ACTIVE for match in matches)
            assert all(match.score == 75 for match in matches)
            assert sum(
                user_ids[0]
                in {match.participant_one_user_id, match.participant_two_user_id}
                for match in matches
            ) == 2
            assert all(match.pair_low_user_id < match.pair_high_user_id for match in matches)
            for match in matches:
                serialized = repr(match.score_breakdown).lower()
                assert set(match.score_breakdown) == {
                    "reference_week_start",
                    "interests",
                    "activities",
                    "availability",
                    "languages",
                    "major",
                }
                assert all(
                    forbidden not in serialized
                    for forbidden in ("email", "user_id", "profile_id", "message")
                )

            reciprocal_pair_match = next(
                match
                for match in matches
                if {match.participant_one_user_id, match.participant_two_user_id}
                == {user_ids[2], user_ids[3]}
            )
            unused_pair_invitation_id = next(
                invitation_id
                for invitation_id in invitation_ids[1:3]
                if invitation_id != reciprocal_pair_match.accepted_invitation_id
            )

        async with engine.connect() as connection:
            permissions = (
                await connection.execute(
                    text(
                        "SELECT "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matches', 'SELECT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matches', 'INSERT'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matches', 'UPDATE'), "
                        "has_table_privilege('vgu_buddy_runtime', "
                        "'app_private.matches', 'DELETE')"
                    )
                )
            ).one()
            assert permissions == (True, True, False, False)
            assert (
                await connection.scalar(
                    text(
                        "SELECT relrowsecurity FROM pg_class "
                        "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' AND relname = 'matches'"
                    )
                )
                is True
            )
            assert (
                await connection.scalar(
                    text(
                        "SELECT array_agg(enumlabel ORDER BY enumsortorder) "
                        "FROM pg_enum JOIN pg_type ON pg_type.oid = enumtypid "
                        "JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace "
                        "WHERE pg_namespace.nspname = 'app_private' "
                        "AND pg_type.typname = 'match_status'"
                    )
                )
                == ["ACTIVE"]
            )
            index_rows = {
                row.relname: row.indisunique
                for row in (
                    await connection.execute(
                        text(
                            "SELECT index_class.relname, pg_index.indisunique "
                            "FROM pg_index "
                            "JOIN pg_class AS table_class ON table_class.oid = indrelid "
                            "JOIN pg_class AS index_class ON index_class.oid = indexrelid "
                            "JOIN pg_namespace ON pg_namespace.oid = table_class.relnamespace "
                            "WHERE pg_namespace.nspname = 'app_private' "
                            "AND table_class.relname = 'matches'"
                        )
                    )
                )
            }
            assert index_rows["uq_matches_active_pair"] is True
            assert index_rows["ix_matches_participant_one_status_activated_at"] is False
            assert index_rows["ix_matches_participant_two_status_activated_at"] is False
            semester_column = (
                await connection.execute(
                    text(
                        "SELECT data_type, is_nullable FROM information_schema.columns "
                        "WHERE table_schema = 'app_private' AND table_name = 'matches' "
                        "AND column_name = 'semester_id'"
                    )
                )
            ).one()
            assert semester_column == ("uuid", "YES")

        duplicate_statement = (
            "INSERT INTO app_private.matches "
            "(participant_one_user_id, participant_two_user_id, "
            "participant_one_profile_id, participant_two_profile_id, status, "
            "accepted_invitation_id, score, score_breakdown, activated_at) VALUES "
            "(:participant_one_user_id, :participant_two_user_id, "
            ":participant_one_profile_id, :participant_two_profile_id, 'ACTIVE', "
            ":accepted_invitation_id, 75, '{}'::jsonb, :activated_at)"
        )
        await _expect_integrity_error(
            engine,
            duplicate_statement,
            {
                "participant_one_user_id": user_ids[3],
                "participant_two_user_id": user_ids[2],
                "participant_one_profile_id": profile_ids[3],
                "participant_two_profile_id": profile_ids[2],
                "accepted_invitation_id": unused_pair_invitation_id,
                "activated_at": NOW,
            },
        )
        await _expect_integrity_error(
            engine,
            duplicate_statement,
            {
                "participant_one_user_id": user_ids[2],
                "participant_two_user_id": user_ids[2],
                "participant_one_profile_id": profile_ids[2],
                "participant_two_profile_id": profile_ids[2],
                "accepted_invitation_id": invitation_ids[4],
                "activated_at": NOW,
            },
        )
    finally:
        await engine.dispose()


async def _assert_downgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            match_table, match_type, invitation_table = (
                await connection.execute(
                    text(
                        "SELECT to_regclass('app_private.matches'), "
                        "to_regtype('app_private.match_status'), "
                        "to_regclass('app_private.matching_invitations')"
                    )
                )
            ).one()
            assert match_table is None
            assert match_type is None
            assert invitation_table == "app_private.matching_invitations"
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.matching_invitations")
                )
                == 5
            )
    finally:
        await engine.dispose()


async def _assert_reupgraded(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert (
                await connection.scalar(text("SELECT to_regclass('app_private.matches')"))
                == "app_private.matches"
            )
            assert await connection.scalar(text("SELECT count(*) FROM app_private.matches")) == 0
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.matching_invitations")
                )
                == 5
            )
            assert (
                await connection.scalar(select(func.count()).select_from(BuddyMatch))
                == 0
            )
    finally:
        await engine.dispose()


def test_live_match_upgrade_races_downgrade_and_reupgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("BUDDY001_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set BUDDY001_TEST_DATABASE_URL for disposable BUDDY-001 PostgreSQL acceptance."
        )
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "buddy001_acceptance"
        or parsed_url.username != "buddy001_runner"
    ):
        pytest.fail(
            "BUDDY-001 requires the disposable buddy001_runner role in the isolated "
            "loopback buddy001_acceptance database."
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    async_database_url = parsed_url.set(
        drivername="postgresql+asyncpg",
        query={"ssl": "disable"},
    ).render_as_string(hide_password=False)
    try:
        command.upgrade(config, "0012_invitation_persistence")
        command.upgrade(config, "head")
        asyncio.run(_assert_upgrade_and_concurrency(async_database_url))
        command.check(config)
        command.downgrade(config, "0012_invitation_persistence")
        asyncio.run(_assert_downgraded(async_database_url))
        command.upgrade(config, "head")
        asyncio.run(_assert_reupgraded(async_database_url))
    finally:
        command.downgrade(config, "0012_invitation_persistence")
        get_migration_database_settings.cache_clear()
