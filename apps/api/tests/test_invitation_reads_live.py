"""Opt-in INV-004 acceptance on an isolated loopback PostgreSQL database.

Set INV004_TEST_DATABASE_URL to the disposable ``inv004_runner`` role in a
loopback-only database named ``inv004_acceptance``. The database is migrated to
the existing head; this test never targets shared development or production data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import MIGRATION_URL_VARIABLE, get_migration_database_settings
from app.models import InvitationStatus, StudentProfile, StudentType, User
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_reads import (
    list_incoming_invitations,
    list_sent_invitations,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
REFERENCE_WEEK = date(2026, 9, 28)


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _seed_participants(
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
                "VALUES (:id, :email, 'test-only-private-hash', true, :verified_at)"
            ),
            [
                {
                    "id": user_id,
                    "email": f"inv004-{user_id}@example.invalid",
                    "verified_at": NOW,
                }
                for user_id in user_ids
            ],
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, display_name, student_type, major, "
                "matching_opt_in) VALUES "
                "(:id, :user_id, :full_name, :display_name, :student_type, "
                ":major, true)"
            ),
            [
                {
                    "id": profile_ids[index],
                    "user_id": user_id,
                    "full_name": f"Private Legal Name {index}",
                    "display_name": f"Buddy {index}",
                    "student_type": (
                        StudentType.VIETNAMESE.value
                        if index == 0
                        else StudentType.INTERNATIONAL.value
                    ),
                    "major": "Computer Science",
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
                "(profile_id, object_key, mime_type, byte_size, width, height, "
                "is_avatar) VALUES "
                "(:profile_id, :object_key, 'image/jpeg', 128, 64, 64, true)"
            ),
            [
                {"profile_id": profile_id, "object_key": f"inv004/{profile_id}.jpg"}
                for profile_id in profile_ids
            ],
        )
    return user_ids, profile_ids


def _invitation_row(
    sender_id: UUID,
    recipient_id: UUID,
    *,
    status: InvitationStatus,
    created_at: datetime,
    hidden: bool = False,
    deleted: bool = False,
) -> dict[str, object]:
    invitation_id = uuid4()
    expires_at = created_at + timedelta(days=7)
    terminal_at = min(NOW, expires_at - timedelta(microseconds=1))
    return {
        "id": invitation_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "message": f"Plain text invitation {invitation_id} <b>not HTML</b>",
        "status": status.value,
        "created_at": created_at,
        "updated_at": NOW,
        "expires_at": expires_at,
        "responded_at": (
            terminal_at
            if status in {InvitationStatus.ACCEPTED, InvitationStatus.DECLINED}
            else None
        ),
        "cancelled_at": terminal_at if status is InvitationStatus.CANCELLED else None,
        "expired_at": NOW if status is InvitationStatus.EXPIRED else None,
        "sender_hidden_at": NOW if hidden else None,
        "deleted_at": NOW if deleted else None,
    }


async def _seed_invitations(
    engine: AsyncEngine,
    user_ids: list[UUID],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tied_at = NOW - timedelta(hours=1)
    incoming = [
        _invitation_row(
            user_ids[1], user_ids[0], status=InvitationStatus.PENDING, created_at=tied_at
        ),
        _invitation_row(
            user_ids[2], user_ids[0], status=InvitationStatus.PENDING, created_at=tied_at
        ),
        _invitation_row(
            user_ids[3],
            user_ids[0],
            status=InvitationStatus.PENDING,
            created_at=NOW - timedelta(days=8),
        ),
        _invitation_row(
            user_ids[4],
            user_ids[0],
            status=InvitationStatus.ACCEPTED,
            created_at=NOW - timedelta(days=2),
        ),
        _invitation_row(
            user_ids[5],
            user_ids[0],
            status=InvitationStatus.DECLINED,
            created_at=NOW - timedelta(days=2),
        ),
        _invitation_row(
            user_ids[6],
            user_ids[7],
            status=InvitationStatus.PENDING,
            created_at=NOW - timedelta(hours=1),
        ),
    ]
    sent = [
        _invitation_row(
            user_ids[0],
            user_ids[8],
            status=InvitationStatus.PENDING,
            created_at=NOW - timedelta(minutes=30),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[9],
            status=InvitationStatus.ACCEPTED,
            created_at=NOW - timedelta(hours=2),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[10],
            status=InvitationStatus.ACCEPTED,
            created_at=NOW - timedelta(hours=3),
            hidden=True,
        ),
        _invitation_row(
            user_ids[0],
            user_ids[11],
            status=InvitationStatus.DECLINED,
            created_at=NOW - timedelta(hours=4),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[12],
            status=InvitationStatus.CANCELLED,
            created_at=NOW - timedelta(hours=5),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[13],
            status=InvitationStatus.EXPIRED,
            created_at=NOW - timedelta(days=8),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[14],
            status=InvitationStatus.PENDING,
            created_at=NOW - timedelta(days=8),
        ),
        _invitation_row(
            user_ids[0],
            user_ids[15],
            status=InvitationStatus.PENDING,
            created_at=NOW - timedelta(hours=1),
            deleted=True,
        ),
    ]
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, created_at, "
                "updated_at, expires_at, responded_at, cancelled_at, expired_at, "
                "sender_hidden_at, deleted_at) VALUES "
                "(:id, :sender_id, :recipient_id, :message, :status, :created_at, "
                ":updated_at, :expires_at, :responded_at, :cancelled_at, :expired_at, "
                ":sender_hidden_at, :deleted_at)"
            ),
            [*incoming, *sent],
        )
    return incoming, sent


async def _assert_read_contract(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    user_ids, profile_ids = await _seed_participants(engine, count=16)
    incoming_rows, sent_rows = await _seed_invitations(engine, user_ids)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = await session.scalar(select(User).where(User.id == user_ids[0]))
            profile = await session.scalar(
                select(StudentProfile).where(StudentProfile.id == profile_ids[0])
            )
            assert user is not None and profile is not None
            principal = VerifiedBuddyPrincipal(user=user, profile=profile)

            incoming_page_1 = await list_incoming_invitations(
                session,
                principal,
                locale="de",
                page=1,
                page_size=1,
                reference_week_start=REFERENCE_WEEK,
                clock=lambda: NOW,
            )
            incoming_page_2 = await list_incoming_invitations(
                session,
                principal,
                locale="de",
                page=2,
                page_size=1,
                reference_week_start=REFERENCE_WEEK,
                clock=lambda: NOW,
            )
            expected_incoming = sorted(
                (
                    cast(UUID, incoming_rows[0]["id"]),
                    cast(UUID, incoming_rows[1]["id"]),
                ),
                reverse=True,
            )
            actual_incoming = (
                incoming_page_1.items[0].id,
                incoming_page_2.items[0].id,
            )
            assert actual_incoming == tuple(expected_incoming)
            assert incoming_page_1.total == 2
            assert incoming_page_1.total_pages == 2
            assert incoming_page_1.items[0].status is InvitationStatus.PENDING
            assert incoming_page_1.items[0].message.startswith("Plain text invitation")
            assert incoming_page_1.items[0].score is not None
            assert incoming_page_1.items[0].explanation is not None
            assert incoming_page_1.items[0].sender.interests[0].label == "Reisen"

            sent = await list_sent_invitations(
                session,
                principal,
                locale="en",
                page=1,
                page_size=20,
                reference_week_start=REFERENCE_WEEK,
                clock=lambda: NOW,
            )
            assert [item.id for item in sent.items] == [
                sent_rows[0]["id"],
                sent_rows[1]["id"],
            ]
            assert [item.status for item in sent.items] == [
                InvitationStatus.PENDING,
                InvitationStatus.ACCEPTED,
            ]
            assert sent.total == 2
            assert all(item.score is not None for item in sent.items)
            assert all(item.explanation is not None for item in sent.items)

            serialized = f"{incoming_page_1.model_dump()} {sent.model_dump()}"
            for private_value in (
                "@example.invalid",
                "test-only-private-hash",
                "Private Legal Name",
                "user_id",
                "sender_id",
                "recipient_id",
                "normalized_key",
                "object_key",
                "bucket",
            ):
                assert private_value not in serialized
            assert "message" not in sent.model_dump()["items"][0]

            indexes = set(
                (
                    await session.scalars(
                        text(
                            "SELECT indexname FROM pg_indexes "
                            "WHERE schemaname = 'app_private' "
                            "AND tablename = 'matching_invitations'"
                        )
                    )
                ).all()
            )
            assert {
                "ix_matching_invitations_sender_status_created_at",
                "ix_matching_invitations_recipient_status_created_at",
                "ix_matching_invitations_pending_expires_at",
            }.issubset(indexes)
    finally:
        await engine.dispose()


def test_live_visibility_privacy_pagination_and_current_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("INV004_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set INV004_TEST_DATABASE_URL for disposable INV-004 acceptance.")
    parsed_url = make_url(database_url)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "inv004_acceptance"
        or parsed_url.username != "inv004_runner"
    ):
        pytest.fail(
            "INV-004 requires the disposable inv004_runner role in the isolated "
            "loopback inv004_acceptance database."
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
        asyncio.run(_assert_read_contract(async_database_url))
    finally:
        get_migration_database_settings.cache_clear()
