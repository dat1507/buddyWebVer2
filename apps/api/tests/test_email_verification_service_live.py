"""Opt-in concurrent EMAIL-001A acceptance on an empty disposable PostgreSQL database.

Set EMAIL001A_TEST_DATABASE_URL to the privileged postgres role in a loopback-only
database named email001a_acceptance. Never point it at development or production data.
The database must be discarded after this test because Alembic's runtime role is cluster-wide.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    MigrationDatabaseSettings,
    get_migration_database_settings,
)
from app.core.database import migration_database_url
from app.models import EmailVerificationToken, User, UserRole
from app.services.email_verification import (
    EmailVerificationTokenError,
    consume_email_verification_token,
    digest_email_verification_token,
    issue_email_verification_token,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
TEST_PASSWORD_HASH = "$2b$12$iLQsp2jeX5jeoHycNLdy5.liN8K13POvlFVK/GUSa8uml6fCZEUW6"


class _ServiceExerciseError(RuntimeError):
    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


def _migration_config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


async def _attempt_consume(
    factory: async_sessionmaker[AsyncSession],
    plaintext: str,
) -> str:
    async with factory() as session:
        try:
            await consume_email_verification_token(
                session,
                plaintext,
                clock=lambda: NOW + timedelta(minutes=1),
            )
            await session.commit()
            return "consumed"
        except EmailVerificationTokenError:
            await session.rollback()
            return "rejected"
        except Exception as exc:
            await session.rollback()
            return type(exc).__name__


async def _exercise_service(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    user_id: UUID
    stage = "seed the token owner"
    try:
        async with factory() as session:
            user = User(
                email="email001a@example.invalid",
                password_hash=TEST_PASSWORD_HASH,
                role=UserRole.USER,
                is_active=True,
                email_verified=False,
                email_verified_at=None,
            )
            session.add(user)
            await session.commit()
            user_id = user.id

        stage = "issue the first token"
        async with factory() as session:
            issued = await issue_email_verification_token(
                session,
                user_id,
                clock=lambda: NOW,
            )
            await session.commit()

        stage = "verify digest-only persistence"
        async with factory() as session:
            persisted = await session.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == user_id
                )
            )
            assert persisted is not None
            assert persisted.token_digest == digest_email_verification_token(issued.token)
            assert persisted.token_digest != issued.token.encode("ascii")

        stage = "race two token consumers"
        outcomes = await asyncio.gather(
            _attempt_consume(factory, issued.token),
            _attempt_consume(factory, issued.token),
        )
        if sorted(outcomes) != ["consumed", "rejected"]:
            stage = f"race two token consumers ({', '.join(sorted(outcomes))})"
            raise AssertionError

        stage = "verify one-use consumption"
        async with factory() as session:
            consumed = await session.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token_digest
                    == digest_email_verification_token(issued.token)
                )
            )
            assert consumed is not None
            assert consumed.consumed_at == NOW + timedelta(minutes=1)

        stage = "issue a replacement token"
        async with factory() as session:
            older = await issue_email_verification_token(
                session,
                user_id,
                clock=lambda: NOW + timedelta(minutes=2),
            )
            await session.commit()
        stage = "supersede the replacement token"
        async with factory() as session:
            newest = await issue_email_verification_token(
                session,
                user_id,
                clock=lambda: NOW + timedelta(minutes=3),
            )
            await session.commit()

        stage = "verify supersession and change email"
        async with factory() as session:
            older_row = await session.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token_digest
                    == digest_email_verification_token(older.token)
                )
            )
            newest_row = await session.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token_digest
                    == digest_email_verification_token(newest.token)
                )
            )
            assert older_row is not None and older_row.superseded_at == NOW + timedelta(minutes=3)
            assert newest_row is not None and newest_row.superseded_at is None
            current_user = await session.get(User, user_id)
            assert current_user is not None
            current_user.email = "changed-email001a@example.invalid"
            await session.commit()

        stage = "reject the old email snapshot"
        async with factory() as session:
            with pytest.raises(EmailVerificationTokenError):
                await consume_email_verification_token(
                    session,
                    newest.token,
                    clock=lambda: NOW + timedelta(minutes=4),
                )
            await session.rollback()
    except Exception:
        raise _ServiceExerciseError(stage) from None
    finally:
        await engine.dispose()


def test_live_concurrent_consume_supersession_and_email_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.getenv("EMAIL001A_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set EMAIL001A_TEST_DATABASE_URL for disposable EMAIL-001A acceptance.")
    try:
        parsed_url = make_url(database_url)
    except Exception:
        pytest.fail("EMAIL-001A disposable database URL is invalid.", pytrace=False)
    if (
        parsed_url.host != "127.0.0.1"
        or parsed_url.database != "email001a_acceptance"
        or parsed_url.username != "postgres"
    ):
        pytest.fail(
            "EMAIL-001A requires the privileged postgres role in the isolated loopback "
            "email001a_acceptance database.",
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
        stage = "exercise concurrent token operations"
        asyncio.run(_exercise_service(async_database_url))
    except _ServiceExerciseError as exc:
        failed_stage = exc.stage
    except Exception:
        failed_stage = stage
    finally:
        try:
            command.downgrade(config, "0007_event_tables")
        except Exception:
            failed_stage = failed_stage or "final EMAIL-001A cleanup"
        get_migration_database_settings.cache_clear()
    if failed_stage is not None:
        pytest.fail(
            f"EMAIL-001A disposable acceptance failed during {failed_stage}; "
            "database details were suppressed.",
            pytrace=False,
        )
