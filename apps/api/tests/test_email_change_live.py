"""Opt-in EMAIL-004 atomicity acceptance on disposable PostgreSQL.

Set EMAIL004_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named email004_acceptance. Never point it at development or production data.
The database must be discarded after this test because Alembic's runtime role is cluster-wide.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID

import pytest
from alembic.config import Config
from pydantic import SecretBytes, SecretStr
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    EmailVerificationDeliverySettings,
    MigrationDatabaseSettings,
    get_migration_database_settings,
)
from app.core.database import migration_database_url
from app.models import EmailVerificationToken, StudentProfile, TransactionalOutbox, User, UserRole
from app.services.buddy_access import BuddyCapabilityError, get_verified_buddy_principal
from app.services.email_changes import EmailChangeConflictError, change_current_user_email
from app.services.email_verification import (
    confirm_email_verification_token,
    issue_email_verification_token,
)
from app.services.email_verification_requests import EmailVerificationTemplate
from app.services.passwords import hash_password

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
TEST_CREDENTIAL = "Correct horse battery staple 🔒"
SHARED_EMAIL = "email004-shared@example.invalid"
SETTINGS = EmailVerificationDeliverySettings(
    public_app_base_url="https://buddy.example",
    sealing_key=SecretBytes(bytes(range(32))),
)


class _ServiceExerciseError(RuntimeError):
    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _attempt_change(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
) -> str:
    async with factory() as session:
        try:
            await change_current_user_email(
                session,
                user_id,
                SHARED_EMAIL,
                TEST_CREDENTIAL,
                SETTINGS,
            )
            await session.commit()
            return "changed"
        except EmailChangeConflictError:
            await session.rollback()
            return "conflict"
        except Exception as exc:
            await session.rollback()
            return type(exc).__name__


async def _exercise_email_change(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    stage = "seed verified users, profiles, and old tokens"
    try:
        password_hash = hash_password(TEST_CREDENTIAL)
        user_ids: list[UUID] = []
        async with factory() as session:
            for index in range(2):
                user = User(
                    email=f"email004-{index}@example.invalid",
                    password_hash=password_hash,
                    role=UserRole.USER,
                    is_active=True,
                    email_verified=False,
                    email_verified_at=NOW,
                )
                session.add(user)
                await session.flush()
                session.add(
                    StudentProfile(
                        user_id=user.id,
                        full_name=f"Preserved profile {index}",
                    )
                )
                await issue_email_verification_token(session, user.id)
                user_ids.append(user.id)
            await session.commit()

        stage = "race the unique replacement address"
        outcomes = await asyncio.gather(
            _attempt_change(factory, user_ids[0]),
            _attempt_change(factory, user_ids[1]),
        )
        if sorted(outcomes) != ["changed", "conflict"]:
            stage = f"race the unique replacement address ({', '.join(sorted(outcomes))})"
            raise AssertionError

        stage = "verify atomic relock, new-address delivery, and data retention"
        async with factory() as session:
            winner = await session.scalar(select(User).where(User.email == SHARED_EMAIL))
            assert winner is not None
            loser = await session.scalar(select(User).where(User.id != winner.id))
            assert loser is not None
            assert winner.email_verified_at is None
            assert loser.email_verified_at == NOW
            assert (
                await session.scalar(select(func.count()).select_from(StudentProfile))
            ) == 2
            with pytest.raises(BuddyCapabilityError):
                await get_verified_buddy_principal(session, winner)

            active_token = await session.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == winner.id,
                    EmailVerificationToken.consumed_at.is_(None),
                    EmailVerificationToken.superseded_at.is_(None),
                    EmailVerificationToken.deleted_at.is_(None),
                )
            )
            token_rows = tuple(
                (
                    await session.scalars(
                        select(EmailVerificationToken).where(
                            EmailVerificationToken.user_id == winner.id
                        )
                    )
                ).all()
            )
            outbox = await session.scalar(
                select(TransactionalOutbox).where(
                    TransactionalOutbox.recipient_user_id == winner.id
                )
            )
            assert active_token is not None
            assert active_token.email_snapshot == SHARED_EMAIL
            assert len(token_rows) == 2
            assert sum(row.superseded_at is not None for row in token_rows) == 1
            assert outbox is not None
            assert outbox.recipient_email == SHARED_EMAIL
            content = EmailVerificationTemplate(SETTINGS).render(outbox.payload)
            plaintext = unquote(content.text_body.split("?token=", maxsplit=1)[1].splitlines()[0])

        stage = "confirm the replacement address and restore capability"
        async with factory() as session:
            await confirm_email_verification_token(session, plaintext, winner.id)
            await session.commit()
        async with factory() as session:
            reverified = await session.get(User, winner.id)
            assert reverified is not None and reverified.email_verified_at is not None
            principal = await get_verified_buddy_principal(session, reverified)
            assert principal.profile.user_id == winner.id
    except Exception:
        raise _ServiceExerciseError(stage) from None
    finally:
        await engine.dispose()


def test_live_unique_race_data_retention_relock_and_reunlock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("EMAIL004_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set EMAIL004_TEST_DATABASE_URL for disposable EMAIL-004 acceptance.")
    try:
        parsed_url = make_url(database_url)
    except Exception:
        pytest.fail("EMAIL-004 disposable database URL is invalid.", pytrace=False)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "email004_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "EMAIL-004 requires the privileged postgres role in the isolated loopback "
            "email004_acceptance database.",
            pytrace=False,
        )

    monkeypatch.setenv(MIGRATION_URL_VARIABLE, database_url)
    get_migration_database_settings.cache_clear()
    config = _migration_config()
    failed_stage: str | None = None
    stage = "normalize the disposable database URL"
    try:
        async_database_url = migration_database_url(
            MigrationDatabaseSettings(url=SecretStr(database_url))
        ).render_as_string(hide_password=False)
        stage = "upgrade the disposable database"
        command.upgrade(config, "head")
        stage = "exercise the email-change transaction"
        asyncio.run(_exercise_email_change(async_database_url))
    except _ServiceExerciseError as exc:
        failed_stage = exc.stage
    except Exception:
        failed_stage = stage
    finally:
        get_migration_database_settings.cache_clear()
    if failed_stage is not None:
        pytest.fail(
            f"EMAIL-004 disposable acceptance failed during {failed_stage}; "
            "database details were suppressed.",
            pytrace=False,
        )
